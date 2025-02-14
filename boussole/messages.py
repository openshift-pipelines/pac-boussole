import os

LGTM_THRESHOLD = int(os.getenv("PAC_LGTM_THRESHOLD", "1"))

HELP_TEXT = f"""
### 🤖 Available Commands
| Command                     | Description                                                                     |
| --------------------------- | ------------------------------------------------------------------------------- |
| `/assign user1 user2`       | Assigns users for review to the PR                                              |
| `/unassign user1 user2`     | Removes assigned users                                                          |
| `/label bug feature`        | Adds labels to the PR                                                           |
| `/unlabel bug feature`      | Removes labels from the PR                                                      |
| `/lgtm`                     | Approves the PR if at least {LGTM_THRESHOLD} org members have commented `/lgtm` |
| `/merge`                    | Merges the PR if it has enough `/lgtm` approvals                                |
| `/cherry-pick target-branch`| Cherry-picks the PR changes to the target branch                                |
| `/rebase`                   | Rebases the PR branch on the base branch                                        |
| `/help`                     | Shows this help message                                                         |
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

LGTM_BREAKDOWN_TEMPLATE = """
### LGTM Vote Breakdown

* **Current valid votes:** {valid_votes}/{threshold}
* **Voting required for approval:** {threshold}

**Votes Summary:**
| Reviewer | Permission | Valid Vote |
|----------|------------|------------|
{users_table}

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

# Error and status message templates
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

# Add new error message template for cherry-pick
CHERRY_PICK_ERROR = """
### ❌ Cherry Pick Failed

Failed to cherry-pick changes from PR #{source_pr} to branch `{target_branch}`:
* Status Code: `{status_code}`
* Error: `{error_text}`

**Possible causes:**
* Merge conflicts
* Branch protection rules
* Invalid branch name
* Missing permissions

Please resolve any issues and try again.
"""

CHERRY_PICK_SUCCESS = """
### ✅ Cherry Pick Successful

Successfully cherry-picked changes from PR #{source_pr} to branch `{target_branch}`.

**Details:**
* Source PR: #{source_pr}
* Target Branch: `{target_branch}`
* Cherry-picked by: @{user}
* New commit SHA: `{commit_sha}`
"""

CHERRY_PICK_CONFLICT = """
🚨 Merge conflict detected while cherry-picking PR #{self.pr_num} to {target_branch}
• Progress: {current_commit}/{total_commits} commits
• Conflicting commit: {commit_sha}

To resolve this conflict:
1. Create a new branch from {target_branch}

```shell
git checkout -b resolve-cherry-pick-{self.pr_num} origin/{target_branch}
```

2. Cherry-pick the commits manually using:

```shell
git cherry-pick {commit_sha}
```

3. Resolve the conflicts with your favorite editor
4. Create a new PR with your changes

```shell
git push YOURFORKREMOTE resolve-cherry-pick-{self.pr_num} --force-with-lease
gh pr create --base {target_branch} --head YOURFORK:resolve-cherry-pick-{self.pr_num}
```

Need assistance? Please contact the repository maintainers.
"""

REVIEW_REQUESTED = """{greeting}

🔍 @{submitter} has kindly requested your review on this PR. 

• Please review the changes and provide your feedback
• Look for code quality, potential bugs, and overall design
• Feel free to suggest improvements or alternatives
• Consider testing the changes if possible

⏰ Take your time - there's no immediate rush, but a timely review would be
appreciated.

Thank you for your help! 🙌"""
