"""Tests for the board endpoints."""

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from kanban_app.models import Board, Task


def create_user(email):
    """Create a user whose name is derived from the email prefix."""
    return User.objects.create_user(
        username=email, email=email, password="secret123",
        first_name=email.split("@")[0].capitalize(), last_name="Test",
    )


class BoardTestBase(APITestCase):
    """Common fixtures: owner, member, outsider and one board."""

    def setUp(self):
        self.owner = create_user("owner@example.com")
        self.member = create_user("member@example.com")
        self.outsider = create_user("outsider@example.com")
        self.board = Board.objects.create(title="Board", owner=self.owner)
        self.board.members.add(self.owner, self.member)
        Task.objects.create(
            board=self.board, title="T1", created_by=self.owner,
            status="to-do", priority="high",
        )
        self.detail_url = reverse("board-detail", args=[self.board.id])
        self.client.force_authenticate(self.owner)


class BoardListCreateTests(BoardTestBase):
    """Tests for GET and POST /api/boards/."""

    url = reverse("board-list")

    def test_list_returns_counters(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0], {
            "id": self.board.id, "title": "Board", "member_count": 2,
            "ticket_count": 1, "tasks_to_do_count": 1,
            "tasks_high_prio_count": 1, "owner_id": self.owner.id,
        })

    def test_list_hides_foreign_boards(self):
        self.client.force_authenticate(self.outsider)
        response = self.client.get(self.url)
        self.assertEqual(response.data, [])

    def test_create_board(self):
        data = {"title": "New", "members": [self.member.id]}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["owner_id"], self.owner.id)
        self.assertEqual(response.data["member_count"], 1)

    def test_create_with_invalid_member_returns_400(self):
        data = {"title": "New", "members": [9999]}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_returns_401(self):
        self.client.force_authenticate(None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class BoardDetailTests(BoardTestBase):
    """Tests for GET, PATCH and DELETE /api/boards/{id}/."""

    def test_member_can_retrieve_board(self):
        self.client.force_authenticate(self.member)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["members"]), 2)
        self.assertNotIn("board", response.data["tasks"][0])

    def test_outsider_gets_403(self):
        self.client.force_authenticate(self.outsider)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_missing_board_returns_404(self):
        response = self.client.get(reverse("board-detail", args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_updates_title_and_members(self):
        data = {"title": "Changed", "members": [self.outsider.id]}
        response = self.client.patch(self.detail_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["owner_data"]["id"], self.owner.id)
        self.assertEqual(
            [m["id"] for m in response.data["members_data"]],
            [self.outsider.id],
        )

    def test_member_cannot_delete_board(self):
        self.client.force_authenticate(self.member)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_deletes_board_with_tasks(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Task.objects.exists())

    def test_put_is_not_allowed(self):
        response = self.client.put(self.detail_url, {}, format="json")
        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_str_representation(self):
        self.assertEqual(str(self.board), "Board")
