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
