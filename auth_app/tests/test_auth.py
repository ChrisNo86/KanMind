"""Tests for registration, login, email check and the guest command."""

from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


def create_user(email="max@example.com", password="secret123"):
    """Create a user with a first and last name."""
    return User.objects.create_user(
        username=email, email=email, password=password,
        first_name="Max", last_name="Mustermann",
    )


class RegistrationTests(APITestCase):
    """Tests for POST /api/registration/."""

    url = reverse("registration")
    payload = {
        "fullname": "Example Username",
        "email": "example@mail.de",
        "password": "examplePassword",
        "repeated_password": "examplePassword",
    }

    def test_registration_returns_token_and_user(self):
        response = self.client.post(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            set(response.data), {"token", "fullname", "email", "user_id"}
        )
        self.assertEqual(response.data["fullname"], "Example Username")

    def test_password_mismatch_returns_400(self):
        data = {**self.payload, "repeated_password": "other"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_email_returns_400(self):
        create_user(email="example@mail.de")
        response = self.client.post(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_single_word_fullname_returns_400(self):
        data = {**self.payload, "fullname": "Example"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTests(APITestCase):
    """Tests for POST /api/login/."""

    url = reverse("login")

    def setUp(self):
        self.user = create_user()

    def test_login_returns_token(self):
        data = {"email": "max@example.com", "password": "secret123"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user_id"], self.user.id)
        self.assertEqual(response.data["fullname"], "Max Mustermann")

    def test_wrong_password_returns_400(self):
        data = {"email": "max@example.com", "password": "wrong"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_email_returns_400(self):
        data = {"email": "nobody@example.com", "password": "secret123"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class EmailCheckTests(APITestCase):
    """Tests for GET /api/email-check/."""

    url = reverse("email-check")

    def setUp(self):
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_existing_email_returns_user(self):
        response = self.client.get(self.url, {"email": "max@example.com"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"id": self.user.id, "email": "max@example.com",
             "fullname": "Max Mustermann"},
        )

    def test_unknown_email_returns_404(self):
        response = self.client.get(self.url, {"email": "no@example.com"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_email_returns_400(self):
        response = self.client.get(self.url, {"email": "invalid"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_returns_401(self):
        self.client.force_authenticate(None)
        response = self.client.get(self.url, {"email": "max@example.com"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class GuestUserCommandTests(APITestCase):
    """Tests for the create_guest_user management command."""

    def test_command_creates_guest_once(self):
        out = StringIO()
        call_command("create_guest_user", stdout=out)
        call_command("create_guest_user", stdout=out)
        guests = User.objects.filter(email="kevin@kovacsi.de")
        self.assertEqual(guests.count(), 1)
        self.assertIn("already exists", out.getvalue())
