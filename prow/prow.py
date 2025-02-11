#!/usr/bin/env python3
# Copyright 2025 Red Hat, Inc.
# Author: Chmouel Boudjnah <chmouel@redhat.com>
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "requests",
# ]
# ///
import argparse
import os
import re
import sys
from dataclasses import dataclass
from enum import Enum, auto
from functools import cache, lru_cache
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.exceptions import RequestException


# Message templates moved to a dedicated class
@dataclass(frozen=True)
class Templates:
    PERMISSION_CHECK_ERROR = """
### ⚠️ Permission Check Failed

Unable to verify permissions for user **@{user}**
* API Response Status: `{status_code}`
* This might be due to:
  * User not being a repository collaborator
  * Invalid authentication
  * Rate limiting

Please check user permissions and try again.
"""

    PERMISSION_DATA_MISSING = """
### ❌ Permission Data Missing

Failed to retrieve permission level for user **@{user}**
* Received empty permission data from GitHub API
* This might indicate an API response format change
* Please contact repository administrators for assistance
"""

    COMMENTS_FETCH_ERROR = """
### 🚫 Failed to Retrieve PR Comments

Unable to process LGTM votes due to API error:
* Status Code: `{status_code}`
* Response: `{response_text}`

**Troubleshooting Steps:**
1. Check your authentication token
2. Verify PR number: `{pr_num}`
3. Ensure the PR hasn't been closed or deleted
"""

    SELF_APPROVAL_ERROR = """
### ⚠️ Invalid LGTM Vote

* User **@{user}** attempted to approve their own PR
* Self-approval is not permitted for security reasons
* Please [delete the comment]({comment_url}) before continuing.

Please wait for reviews from other team members.
"""

    INSUFFICIENT_PERMISSIONS = """
### 🔒 Insufficient Permissions

* User **@{user}** does not have permission to merge
* Current permission level: `{permission}`
* Required permissions: `{required_permissions}`

Please request assistance from a repository maintainer.
"""

    NOT_ENOUGH_LGTM = """
### ❌ Insufficient Approvals

* Current valid LGTM votes: **{valid_votes}**
* Required votes: **{threshold}**

Please obtain additional approvals before merging.
"""

    MERGE_FAILED = """
### ❌ Merge Failed

Unable to merge PR #{pr_num}:
* Status Code: `{status_code}`
* Error: `{error_text}`

**Possible causes:**
* Branch protection rules not satisfied
* Merge conflicts present
* Required checks failing

Please resolve any issues and try again.
"""

    SUCCESS_MERGED = """
### ✅ PR Successfully Merged

* Merge method: `{merge_method}`
* Merged by: **@{comment_sender}**
* Total approvals: **{valid_votes}/{lgtm_threshold}**

**Approvals Summary:**
| Reviewer | Permission | Status |
|----------|------------|--------|
{users_table}
"""

    APPROVED_TEMPLATE = """
### ✅ Pull Request Approved

**Approval Status:**
* Required Approvals: {threshold}
* Current Approvals: {valid_votes}

### 👥 Approved By:
| Reviewer | Permission | Status |
|----------|------------|--------|
{users_table}

### 📝 Next Steps
* All required checks must pass
* Branch protection rules apply
* Get a maintainer to use the `/merge` command to merge the PR

Thank you for your contributions! 🎉
"""

    LGTM_BREAKDOWN = """
### LGTM Vote Breakdown

* **Current valid votes:** {valid_votes}/{threshold}
* **Voting required for approval:** {threshold}

**Votes Summary:**
| Reviewer | Permission | Valid Vote |
|----------|------------|------------|
{users_table}
"""

    HELP = """
### 🤖 Available Commands
| Command                     | Description                                                                     |
| --------------------------- | ------------------------------------------------------------------------------- |
| `/assign user1 user2`       | Assigns users for review to the PR                                              |
| `/unassign user1 user2`     | Removes assigned users                                                          |
| `/label bug feature`        | Adds labels to the PR                                                           |
| `/unlabel bug feature`      | Removes labels from the PR                                                      |
| `/lgtm`                     | Approves the PR if at least {threshold} org members have commented `/lgtm`      |
| `/merge`                    | Merges the PR if it has enough `/lgtm` approvals                               |
| `/rebase`                   | Rebases the PR branch on the base branch                                        |
| `/help`                     | Shows this help message                                                         |
"""


class Config:
    """
    Configuration settings with environment variable fallbacks.
    """

    LGTM_THRESHOLD = int(os.getenv("PAC_LGTM_THRESHOLD", "1"))
    DEFAULT_TIMEOUT = 10
    API_VERSION = "application/vnd.github.v3+json"


class CommandType(Enum):
    """
    Enumeration of supported PR commands.
    """

    ASSIGN = auto()
    UNASSIGN = auto()
    LABEL = auto()
    UNLABEL = auto()
    LGTM = auto()
    MERGE = auto()
    REBASE = auto()
    HELP = auto()

    @classmethod
    def from_str(cls, value: str) -> Optional["CommandType"]:
        try:
            return cls[value.upper()]
        except KeyError:
            return None


@dataclass(frozen=True)
class PRCommand:
    """
    Represents a parsed PR command with its arguments.
    """

    type: CommandType
    values: List[str]

    @classmethod
    def parse(cls, comment: str) -> Optional["PRCommand"]:
        match = re.match(r"^/(\w+)\s*(.*)", comment)
        if not match:
            return None

        command, values = match.groups()
        command_type = CommandType.from_str(command)
        if not command_type:
            return None

        return cls(command_type, values.split())


class GitHubAPI:
    """
    Enhanced GitHub API client with error handling and caching.
    """

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {token}", "Accept": Config.API_VERSION}
        )

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.request(
                method, url, timeout=Config.DEFAULT_TIMEOUT, **kwargs
            )
            response.raise_for_status()
            return response
        except RequestException as e:
            print(f"API request failed: {e}", file=sys.stderr)
            sys.exit(1)

    @lru_cache(maxsize=100)
    def get(self, endpoint: str) -> requests.Response:
        return self._make_request("GET", endpoint)

    def post(self, endpoint: str, data: Dict) -> requests.Response:
        return self._make_request("POST", endpoint, json=data)

    def put(self, endpoint: str, data: Dict) -> requests.Response:
        return self._make_request("PUT", endpoint, json=data)

    def delete(self, endpoint: str, data: Optional[Dict] = None) -> requests.Response:
        return self._make_request("DELETE", endpoint, json=data if data else {})


@dataclass(frozen=True)
class PRContext:
    """
    Immutable context object containing PR-related data.
    """

    pr_num: int
    pr_sender: str
    comment_sender: str
    lgtm_threshold: int
    lgtm_permissions: set[str]
    lgtm_review_event: str
    merge_method: str

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "PRContext":
        return cls(
            pr_num=int(args.pr_num),
            pr_sender=args.pr_sender,
            comment_sender=args.comment_sender,
            lgtm_threshold=args.lgtm_threshold,
            lgtm_permissions=set(args.lgtm_permissions.split(",")),
            lgtm_review_event=args.lgtm_review_event,
            merge_method=args.merge_method,
        )


class UserPermissions:
    """
    Handles user permission checking and caching.
    """

    def __init__(self, api: GitHubAPI, required_permissions: set[str]):
        self.api = api
        self.required_permissions = required_permissions
        self._cache: Dict[str, Optional[str]] = {}

    @lru_cache(maxsize=100)
    def check_membership(self, user: str) -> Tuple[Optional[str], bool]:
        """
        Check if a user has required permissions.
        """
        if user in self._cache:
            permission = self._cache[user]
            return permission, permission in self.required_permissions

        response = self.api.get(f"collaborators/{user}/permission")
        permission = response.json().get("permission")
        self._cache[user] = permission

        return permission, permission in self.required_permissions


class PRHandler:
    """
    Handles PR operations with improved organization and error handling.
    """

    def __init__(self, api: GitHubAPI, context: PRContext):
        self.api = api
        self.context = context
        self.permissions = UserPermissions(api, context.lgtm_permissions)
        self._command_handlers = {
            CommandType.ASSIGN: self._handle_assign,
            CommandType.UNASSIGN: self._handle_unassign,
            CommandType.LABEL: self._handle_label,
            CommandType.UNLABEL: self._handle_unlabel,
            CommandType.LGTM: self._handle_lgtm,
            CommandType.MERGE: self._handle_merge,
            CommandType.REBASE: self._handle_rebase,
            CommandType.HELP: self._handle_help,
        }

    def handle_command(self, command: PRCommand) -> None:
        """
        Entry point for handling all commands.
        """
        self._validate_pr_state()
        handler = self._command_handlers.get(command.type)
        if handler:
            handler(command.values)
        else:
            print(f"Unknown command: {command.type}", file=sys.stderr)
            sys.exit(1)

    @cache
    def get_pr_status(self) -> Dict[str, Any]:
        """
        Cached PR status retrieval.
        """
        response = self.api.get(f"pulls/{self.context.pr_num}")
        return response.json()

    def _validate_pr_state(self) -> None:
        """
        Ensures PR is in valid state for operations.
        """
        status = self.get_pr_status()
        if status.get("state") != "open":
            print(f"⚠️ PR #{self.context.pr_num} is not open.", file=sys.stderr)
            sys.exit(1)

    def _post_comment(self, message: str) -> None:
        """
        Posts a comment to the PR.
        """
        self.api.post(f"issues/{self.context.pr_num}/comments", {"body": message})

    def _handle_assign(self, users: List[str]) -> None:
        """
        Handles the assign command.
        """
        users = [user.lstrip("@") for user in users]
        self.api.post(
            f"pulls/{self.context.pr_num}/requested_reviewers", {"reviewers": users}
        )
        self._post_comment(f"✅ Assigned {', '.join(users)} for review.")

    def _handle_unassign(self, users: List[str]) -> None:
        """
        Handles the unassign command.
        """
        users = [user.lstrip("@") for user in users]
        self.api.delete(
            f"pulls/{self.context.pr_num}/requested_reviewers", {"reviewers": users}
        )
        self._post_comment(f"✅ Unassigned {', '.join(users)} from review.")

    def _handle_label(self, labels: List[str]) -> None:
        """
        Handles the label command.
        """
        self.api.post(f"issues/{self.context.pr_num}/labels", {"labels": labels})
        self._post_comment(f"✅ Added labels: {', '.join(labels)}")

    def _handle_unlabel(self, labels: List[str]) -> None:
        """
        Handles the unlabel command.
        """
        for label in labels:
            self.api.delete(f"issues/{self.context.pr_num}/labels/{label}")
        self._post_comment(f"✅ Removed labels: {', '.join(labels)}")

    def _handle_rebase(self, _: List[str]) -> None:
        """
        Handles the rebase command.
        """
        self.api.put(f"pulls/{self.context.pr_num}/update-branch", {})
        self._post_comment("✅ Rebased the PR branch on the base branch.")

    def _handle_help(self, _: List[str]) -> None:
        """
        Handles the help command.
        """
        self._post_comment(Templates.HELP.format(threshold=self.context.lgtm_threshold))

    def _handle_lgtm(self, _: List[str]) -> None:
        """
        Handles the LGTM command.
        """
        votes = self._collect_lgtm_votes()
        if len(votes) >= self.context.lgtm_threshold:
            self._approve_pr(votes)
        else:
            self._post_lgtm_breakdown(votes)

    def _handle_merge(self, _: List[str]) -> None:
        """
        Handles the merge command.
        """
        self._validate_merger_permissions()
        votes = self._collect_lgtm_votes()

        if len(votes) >= self.context.lgtm_threshold:
            self._merge_pr(votes)
        else:
            self._post_comment(
                Templates.NOT_ENOUGH_LGTM.format(
                    valid_votes=len(votes), threshold=self.context.lgtm_threshold
                )
            )

    def _collect_lgtm_votes(self) -> Dict[str, str]:
        """
        Collects and validates LGTM votes.
        """
        response = self.api.get(f"issues/{self.context.pr_num}/comments")
        votes: Dict[str, str] = {}

        for comment in response.json():
            if not re.search(r"^/lgtm\b", comment.get("body", ""), re.IGNORECASE):
                continue

            user = comment["user"]["login"]
            if user == self.context.pr_sender:
                self._handle_self_approval(user, comment["html_url"])

            permission, is_valid = self.permissions.check_membership(user)
            if is_valid and permission:
                votes[user] = permission

        return votes

    def _handle_self_approval(self, user: str, comment_url: str) -> None:
        """
        Handles self-approval attempts.
        """
        msg = Templates.SELF_APPROVAL_ERROR.format(user=user, comment_url=comment_url)
        self._post_comment(msg)
        print(msg, file=sys.stderr)
        sys.exit(1)

    def _validate_merger_permissions(self) -> None:
        """
        Validates if the comment sender has permission to merge.
        """
        permission, is_valid = self.permissions.check_membership(
            self.context.comment_sender
        )
        if not is_valid:
            msg = Templates.INSUFFICIENT_PERMISSIONS.format(
                user=self.context.comment_sender,
                permission=permission,
                required_permissions=", ".join(self.context.lgtm_permissions),
            )
            self._post_comment(msg)
            print(msg, file=sys.stderr)
            sys.exit(1)

    def _approve_pr(self, votes: Dict[str, str]) -> None:
        """
        Approves the PR with the collected LGTM votes.
        """
        users_table = "\n".join(
            f"| @{user} | `{permission}` | ✅ |" for user, permission in votes.items()
        )
        message = Templates.APPROVED_TEMPLATE.format(
            threshold=self.context.lgtm_threshold,
            valid_votes=len(votes),
            users_table=users_table,
        )
        self._post_comment(message)
        self.api.post(
            f"pulls/{self.context.pr_num}/reviews",
            {"event": self.context.lgtm_review_event, "body": message},
        )

    def _post_lgtm_breakdown(self, votes: Dict[str, str]) -> None:
        """
        Posts a detailed breakdown of LGTM votes.
        """
        users_table = "\n".join(
            f"| @{user} | `{permission}` | ✅ |"
            if permission in self.context.lgtm_permissions
            else f"| @{user} | `{permission}` | ❌ |"
            for user, permission in votes.items()
        )
        message = Templates.LGTM_BREAKDOWN.format(
            valid_votes=len(votes),
            threshold=self.context.lgtm_threshold,
            users_table=users_table,
        )
        self._post_comment(message)

    def _merge_pr(self, votes: Dict[str, str]) -> None:
        """
        Merges the PR if it has enough LGTM approvals.
        """
        data = {
            "merge_method": self.context.merge_method,
            "commit_title": f"Merged PR #{self.context.pr_num}",
            "commit_message": f"PR #{self.context.pr_num} merged by {self.context.comment_sender} with {len(votes)} LGTM votes.",
        }
        response = self.api.put(f"pulls/{self.context.pr_num}/merge", data)

        if response.status_code == 200:
            users_table = "\n".join(
                f"| @{user} | `{permission}` | ✅ |"
                for user, permission in votes.items()
            )
            success_message = Templates.SUCCESS_MERGED.format(
                merge_method=self.context.merge_method,
                comment_sender=self.context.comment_sender,
                valid_votes=len(votes),
                lgtm_threshold=self.context.lgtm_threshold,
                users_table=users_table,
            )
            self._post_comment(success_message)
        else:
            self._post_comment(
                Templates.MERGE_FAILED.format(
                    pr_num=self.context.pr_num,
                    status_code=response.status_code,
                    error_text=response.text,
                )
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage prow-like commands on a GitHub PullRequest.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--lgtm-threshold",
        type=int,
        default=Config.LGTM_THRESHOLD,
        help="Minimum number of LGTM approvals required to merge a PR.",
    )
    parser.add_argument(
        "--lgtm-permissions",
        default=os.getenv("PAC_LGTM_PERMISSIONS", "admin,write"),
        help="Comma-separated list of GitHub permissions required to give a valid LGTM.",
    )
    parser.add_argument(
        "--lgtm-review-event",
        default=os.getenv("PAC_LGTM_REVIEW_EVENT", "APPROVE"),
        help="The type of review event to trigger when an LGTM is given.",
    )
    parser.add_argument(
        "--merge-method",
        default=os.getenv("GH_MERGE_METHOD", "rebase"),
        help="The method to use when merging the pull request. Options: 'merge', 'rebase', or 'squash'.",
    )
    parser.add_argument(
        "--github-token",
        default=os.getenv("GITHUB_TOKEN"),
        help="GitHub API token for authentication.",
    )
    parser.add_argument(
        "--pr-num",
        default=os.getenv("GH_PR_NUM"),
        help="The number of the pull request to operate on.",
    )
    parser.add_argument(
        "--pr-sender",
        default=os.getenv("GH_PR_SENDER"),
        help="The GitHub username of the user who opened the pull request.",
    )
    parser.add_argument(
        "--comment-sender",
        default=os.getenv("GH_COMMENT_SENDER"),
        help="The GitHub username of the user who triggered the command.",
    )
    parser.add_argument(
        "--repo-owner",
        default=os.getenv("GH_REPO_OWNER"),
        help="The owner (organization or user) of the GitHub repository.",
    )
    parser.add_argument(
        "--repo-name",
        default=os.getenv("GH_REPO_NAME"),
        help="The name of the GitHub repository.",
    )
    parser.add_argument(
        "--trigger-comment",
        default=os.getenv("PAC_TRIGGER_COMMENT"),
        help="The comment that triggered this command.",
    )
    args = parser.parse_args()

    if not args.github_token:
        parser.error(
            "GitHub API token is required. Use --github-token or GITHUB_TOKEN env variable."
        )
    if not args.pr_num:
        parser.error("PR number is required. Use --pr-num or GH_PR_NUM env variable.")
    if not args.pr_sender:
        parser.error(
            "PR sender is required. Use --pr-sender or GH_PR_SENDER env variable."
        )
    if not args.comment_sender:
        parser.error(
            "Comment sender is required. Use --comment-sender or GH_COMMENT_SENDER env variable."
        )
    if not args.repo_owner:
        parser.error(
            "Repository owner is required. Use --repo-owner or GH_REPO_OWNER env variable."
        )
    if not args.repo_name:
        parser.error(
            "Repository name is required. Use --repo-name or GH_REPO_NAME env variable."
        )
    if not args.trigger_comment:
        parser.error(
            "Trigger comment is required. Use --trigger-comment or PAC_TRIGGER_COMMENT env variable."
        )

    return args


def main():
    args = parse_args()
    api_base = f"https://api.github.com/repos/{args.repo_owner}/{args.repo_name}"
    api = GitHubAPI(api_base, args.github_token)
    context = PRContext.from_args(args)
    pr_handler = PRHandler(api, context)

    command = PRCommand.parse(args.trigger_comment)
    if not command:
        print(
            f"⚠️ No valid command found in comment: {args.trigger_comment}",
            file=sys.stderr,
        )
        sys.exit(1)

    pr_handler.handle_command(command)


if __name__ == "__main__":
    main()
