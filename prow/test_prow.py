from unittest.mock import MagicMock

import pytest

from prow.prow import GitHubAPI, PRHandler


@pytest.fixture
def mock_api():
    api = GitHubAPI(
        "https://api.github.com/repos/test/repo", {"Authorization": "Bearer test_token"}
    )
    api.get = MagicMock()
    api.post = MagicMock()
    api.put = MagicMock()
    api.delete = MagicMock()
    return api


@pytest.fixture
def pr_handler(mock_api):
    return PRHandler(
        api=mock_api,
        pr_num="123",
        pr_sender="test_user",
        comment_sender="reviewer",
        lgtm_threshold=2,
        lgtm_permissions="admin,write",
        lgtm_review_event="APPROVE",
        merge_method="squash",
    )


def test_post_comment(pr_handler, mock_api):
    pr_handler.post_comment("Test comment")
    mock_api.post.assert_called_once_with(
        "issues/123/comments", {"body": "Test comment"}
    )


def test_assign_unassign(pr_handler, mock_api):
    pr_handler.assign_unassign("assign", ["user1", "user2"])
    mock_api.post.assert_called_once_with(
        "pulls/123/requested_reviewers", {"reviewers": ["user1", "user2"]}
    )


def test_label(pr_handler, mock_api):
    pr_handler.label(["bug", "enhancement"])

    # Ensure both calls happened
    assert mock_api.post.call_count == 2
    mock_api.post.assert_any_call(
        "issues/123/labels", {"labels": ["bug", "enhancement"]}
    )
    mock_api.post.assert_any_call(
        "issues/123/comments", {"body": "✅ Added labels: <b>bug, enhancement</b>."}
    )


def test_unlabel(pr_handler, mock_api):
    pr_handler.unlabel(["bug"])
    mock_api.delete.assert_called_once_with("issues/123/labels/bug")


def test_check_membership(pr_handler, mock_api):
    mock_api.get.return_value.status_code = 200
    mock_api.get.return_value.json.return_value = {"permission": "write"}
    permission, is_valid = pr_handler.check_membership("reviewer")
    assert permission == "write"
    assert is_valid is True


def test_lgtm(pr_handler, mock_api):
    mock_api.get.return_value.status_code = 200

    # Mock response for PR comments
    def mock_json_comments():
        return [
            {"body": "/lgtm", "user": {"login": "reviewer1"}},
            {"body": "/lgtm", "user": {"login": "reviewer2"}},
        ]

    # Mock response for permissions
    def mock_json_permissions():
        return {"permission": "write"}

    # Assign the side_effect to return different results on multiple calls
    mock_api.get.return_value.json.side_effect = [
        mock_json_comments(),  # First call to json() -> PR comments
        mock_json_permissions(),  # Second call to json() -> reviewer1 permission
        mock_json_permissions(),  # Third call to json() -> reviewer2 permission
    ]

    assert pr_handler.lgtm() == 2
    mock_api.get.return_value.status_code = 200
