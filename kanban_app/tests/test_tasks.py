"""Tests for the task and comment endpoints."""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from kanban_app.models import Board, Comment, Task

from .test_boards import create_user


class TaskTestBase(APITestCase):
    """Common fixtures: board with owner, member, outsider and a task."""

    def setUp(self):
        self.owner = create_user("owner@example.com")
        self.member = create_user("member@example.com")
        self.outsider = create_user("outsider@example.com")
        self.board = Board.objects.create(title="Board", owner=self.owner)
        self.board.members.add(self.member)
        self.task = Task.objects.create(
            board=self.board, title="Task", created_by=self.member,
            assignee=self.member, reviewer=self.owner,
        )
        self.task_url = reverse("task-detail", args=[self.task.id])
        self.client.force_authenticate(self.member)


class TaskCreateTests(TaskTestBase):
    """Tests for POST /api/tasks/."""

    url = reverse("task-list")

    def payload(self, **overrides):
        """Return a valid task payload with optional overrides."""
        data = {
            "board": self.board.id, "title": "New", "description": "",
            "status": "review", "priority": "medium",
            "assignee_id": self.member.id, "reviewer_id": self.owner.id,
            "due_date": "2025-02-27",
        }
        return {**data, **overrides}

    def test_create_task(self):
        response = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["assignee"]["id"], self.member.id)
        self.assertEqual(response.data["comments_count"], 0)
        self.assertEqual(response.data["board"], self.board.id)

    def test_outsider_gets_403(self):
        self.client.force_authenticate(self.outsider)
        response = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_missing_board_returns_404(self):
        data = self.payload(board=9999)
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_board_id_returns_400(self):
        data = self.payload(board="abc")
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_assignee_outside_board_returns_400(self):
        data = self.payload(assignee_id=self.outsider.id)
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_status_returns_400(self):
        data = self.payload(status="unknown")
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TaskUpdateDeleteTests(TaskTestBase):
    """Tests for PATCH and DELETE /api/tasks/{id}/."""

    def test_patch_task(self):
        data = {"title": "Changed", "status": "done", "assignee_id": None}
        response = self.client.patch(self.task_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["assignee"])
        self.assertNotIn("board", response.data)

    def test_patch_board_change_returns_400(self):
        other = Board.objects.create(title="Other", owner=self.member)
        data = {"board": other.id}
        response = self.client.patch(self.task_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_reviewer_outside_board_returns_400(self):
        data = {"reviewer_id": self.outsider.id}
        response = self.client.patch(self.task_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_outsider_cannot_patch(self):
        self.client.force_authenticate(self.outsider)
        response = self.client.patch(self.task_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_missing_task_returns_404(self):
        url = reverse("task-detail", args=[9999])
        response = self.client.patch(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_board_owner_can_delete(self):
        self.client.force_authenticate(self.owner)
        response = self.client.delete(self.task_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_other_member_cannot_delete(self):
        other = create_user("other@example.com")
        self.board.members.add(other)
        self.client.force_authenticate(other)
        response = self.client.delete(self.task_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_str_representation(self):
        self.assertEqual(str(self.task), "Task")


class TaskListTests(TaskTestBase):
    """Tests for the assigned-to-me and reviewing lists."""

    def test_assigned_to_me(self):
        response = self.client.get(reverse("tasks-assigned-to-me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], self.task.id)

    def test_reviewing(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(reverse("tasks-reviewing"))
        self.assertEqual(response.data[0]["board"], self.board.id)

    def test_reviewing_empty_for_member(self):
        response = self.client.get(reverse("tasks-reviewing"))
        self.assertEqual(response.data, [])


class CommentTests(TaskTestBase):
    """Tests for the comment endpoints of a task."""

    def setUp(self):
        super().setUp()
        self.comment = Comment.objects.create(
            task=self.task, author=self.member, content="First"
        )
        self.list_url = reverse("task-comments", args=[self.task.id])
        self.detail_url = reverse(
            "task-comment-detail", args=[self.task.id, self.comment.id]
        )

    def test_list_comments(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["author"], "Member Test")

    def test_create_comment(self):
        data = {"content": "Hello"}
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            set(response.data), {"id", "created_at", "author", "content"}
        )

    def test_empty_content_returns_400(self):
        response = self.client.post(self.list_url, {"content": ""})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_outsider_gets_403(self):
        self.client.force_authenticate(self.outsider)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_missing_task_returns_404(self):
        url = reverse("task-comments", args=[9999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_author_cannot_delete(self):
        self.client.force_authenticate(self.owner)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_deletes_comment(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_comment_of_other_task_returns_404(self):
        url = reverse("task-comment-detail", args=[9999, self.comment.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_comments_count_in_board_detail(self):
        url = reverse("board-detail", args=[self.board.id])
        response = self.client.get(url)
        self.assertEqual(response.data["tasks"][0]["comments_count"], 1)
        self.assertTrue(str(self.comment).startswith("member@example.com"))
