#!/usr/bin/env python3
# Copyright 2025 Red Hat, Inc.
# Author: Chmouel Boudjnah <chmouel@redhat.com>
import os
import re
import sys

import requests

LGTM_THRESHOLD = int(os.getenv("PAC_LGTM_TRESHOLD", 1))
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GH_PR_NUM = os.getenv("GH_PR_NUM")
GH_PR_SENDER = os.getenv("GH_PR_SENDER")
GH_REPO_OWNER = os.getenv("GH_REPO_OWNER")
GH_REPO_NAME = os.getenv("GH_REPO_NAME")
PAC_TRIGGER_COMMENT = os.getenv("PAC_TRIGGER_COMMENT", "")
API_BASE = f"https://api.github.com/repos/{GH_REPO_OWNER}/{GH_REPO_NAME}"
API_ISSUE = f"{API_BASE}/issues/{GH_PR_NUM}"
API_PULLS = f"{API_BASE}/pulls/{GH_PR_NUM}"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

HELP_TEXT = f"""
### 🤖 Available Commands
| Command                   | Description                                                          |
|---------------------------|----------------------------------------------------------------------|
| `/assign user1 user2`     | Assigns users for review to the PR                                   |
| `/unassign user1 user2`   | Removes assigned users                                               |
| `/label bug feature`      | Adds labels to the PR                                                |
| `/unlabel bug feature`    | Removes labels from the PR                                           |
| `/lgtm`                   | Approves the PR if at least {LGTM_THRESHOLD} org members have commented `/lgtm`     |
| `/merge`                  | Merges the PR if it has enough `/lgtm` approvals                    |
| `/help`                   | Shows this help message                                              |
"""


def post_comment(message, error=False):
    """Posts a comment to the pull request with the given message.

    Args:
        message (str): The message to post
        error (bool): If True, formats the message as an error

    Returns:
        requests.Response: The response from the GitHub API
    """
    API_URL = f"{API_ISSUE}/comments"

    if error:
        formatted_message = f"""### ❌ Error
```
{message}
```"""
    else:
        formatted_message = message

    return make_request("POST", API_URL, {"body": formatted_message})


def make_request(method, url, data=None):
    if method == "POST":
        return requests.post(url, json=data, headers=HEADERS)
    elif method == "DELETE":
        return requests.delete(url, json=data, headers=HEADERS)
    return None


def assign_unassign(command, values):
    method = "POST" if command == "assign" else "DELETE"
    API_URL = f"{API_PULLS}/requested_reviewers"
    values = [value.lstrip("@") for value in values]
    data = {"reviewers": values}
    response = make_request(method, API_URL, data)
    if response and response.status_code in [200, 201, 204]:
        post_comment(
            f"✅ {command.capitalize()}ed <b>{', '.join(values)}</b> for reviews."
        )
    return response


def label(values):
    API_URL = f"{API_ISSUE}/labels"
    data = {"labels": values}
    post_comment(f"✅ Added labels: <b>{', '.join(values)}</b>.")
    return make_request("POST", API_URL, data)


def unlabel(values):
    for label in values:
        response = make_request("DELETE", f"{API_ISSUE}/labels/{label}")
    post_comment(f"✅ Removed labels: <b>{', '.join(values)}</b>.")
    return response


def post_lgtm_breakdown(valid_votes, lgtm_users):
    """Posts a breakdown of LGTM votes as a comment.

    Args:
        valid_votes (int): Number of valid LGTM votes
        lgtm_users (dict): Dictionary of users and their permissions who voted LGTM
    """
    message = "### LGTM Vote Breakdown\n\n"
    message += f"Current valid votes: {valid_votes}/{LGTM_THRESHOLD}\n\n"
    message += "| User | Permission | Valid Vote |\n"
    message += "|------|------------|------------|\n"

    for user, permission in lgtm_users.items():
        is_valid = permission in ["admin", "write"]
        valid_mark = "✅" if is_valid else "❌"
        message += f"| @{user} | {permission} | {valid_mark} |\n"

    return post_comment(message)


def lgtm():
    comments_resp = requests.get(API_ISSUE + "/comments", headers=HEADERS)
    if comments_resp.status_code != 200:
        error_message = f"Failed to fetch comments: {comments_resp.status_code} - {comments_resp.text}"
        print(error_message, file=sys.stderr)
        sys.exit(1)

    comments = comments_resp.json()
    lgtm_users = {}
    for comment_item in comments:
        body = comment_item.get("body", "")
        if re.search(r"^/lgtm\b", body, re.IGNORECASE):
            user_login = comment_item["user"]["login"]
            if user_login == GH_PR_SENDER:
                msg = f"User {user_login} is the PR sender and cannot /lgtm their own PR. This needs to be deleted or this won't pass"
                post_comment(msg, error=True)
                print(msg, file=sys.stderr)
                sys.exit(1)
            lgtm_users[user_login] = None

    valid_votes = 0
    for user in list(lgtm_users.keys()):
        membership_url = f"{API_BASE}/collaborators/{user}/permission"
        membership_resp = requests.get(membership_url, headers=HEADERS)

        if membership_resp.status_code != 200:
            print(
                f"User {user} does not have admin access (status: {membership_resp.status_code})",
                file=sys.stderr,
            )
            lgtm_users[user] = "none"
            continue

        response_data = membership_resp.json()
        permission = response_data.get("permission")
        if not permission:
            print("No permission found in response", file=sys.stderr)
            lgtm_users[user] = "none"
            continue

        lgtm_users[user] = permission
        if permission in ["admin", "write"]:
            valid_votes += 1
        else:
            print(
                f"User {user} does not have write access: {response_data}",
                file=sys.stderr,
            )

    # Post the LGTM breakdown
    post_lgtm_breakdown(valid_votes, lgtm_users)

    if valid_votes >= LGTM_THRESHOLD:
        API_URL = API_PULLS + "/reviews"
        data = {"event": "APPROVE", "body": "LGTM :+1:"}
        print("✅ PR approved with LGTM votes.")
        make_request("POST", API_URL, data)
    else:
        message = (
            f"Not enough valid /lgtm votes (found {valid_votes}, need {LGTM_THRESHOLD})"
        )
        print(message)
        sys.exit(0)

    return valid_votes  # Return the number of valid votes


def merge_pr():
    """Merges the pull request if the number of valid LGTM votes meets the threshold."""
    valid_votes = lgtm()  # Get the number of valid LGTM votes
    if valid_votes >= LGTM_THRESHOLD:
        API_URL = f"{API_PULLS}/merge"
        data = {
            "merge_method": "merge",  # You can change this to "squash" or "rebase" if needed
            "commit_title": f"Merged PR #{GH_PR_NUM}",
            "commit_message": f"PR #{GH_PR_NUM} merged by {GH_PR_SENDER} with {valid_votes} LGTM votes.",
        }
        response = make_request("PUT", API_URL, data)
        if response and response.status_code == 200:
            post_comment("✅ PR successfully merged.")
            return True
        else:
            post_comment(
                f"❌ Failed to merge PR: {response.status_code} - {response.text}",
                error=True,
            )
            return False
    else:
        post_comment(
            f"❌ Not enough valid /lgtm votes to merge (found {valid_votes}, need {LGTM_THRESHOLD})",
            error=True,
        )
        return False


def help_command():
    return post_comment(HELP_TEXT.strip())


def check_response(command, values, response):
    rtext = ""
    if isinstance(response, int):
        rstatus_code = response
    else:
        rstatus_code = response.status_code
        rtext = response.text
    if response and rstatus_code in [200, 201, 204]:
        print(
            f"✅ Successfully processed {command}: {', '.join(values) if values else ''}"
        )
        return True
    print(
        f"❌ Failed to process {command}: {rstatus_code} - {rtext}",
        file=sys.stderr,
    )
    return False


def main():
    match = re.match(
        r"^/(assign|unassign|label|unlabel|lgtm|help)\s*(.*)", PAC_TRIGGER_COMMENT
    )

    if not match:
        print(
            f"⚠️ No valid command found in comment: {PAC_TRIGGER_COMMENT}",
            file=sys.stderr,
        )
        sys.exit(1)

    command, values = match.groups()
    values = values.split()

    if command == "assign" or command == "unassign":
        response = assign_unassign(command, values)
    elif command == "label":
        response = label(values)
    elif command == "unlabel":
        response = unlabel(values)
    elif command == "help":
        response = help_command()
    elif command == "lgtm":
        lgtm()
        return
    elif command == "merge":
        merge_pr()
        return

    if not check_response(command, values, response):
        sys.exit(1)


if __name__ == "__main__":
    main()
