"""API views for authentication and user lookup."""

from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    EmailCheckSerializer,
    LoginSerializer,
    RegistrationSerializer,
    UserSummarySerializer,
    get_fullname,
)


def build_auth_response(user):
    """Return the token payload expected by the frontend."""
    token, _ = Token.objects.get_or_create(user=user)
    return {
        "token": token.key,
        "fullname": get_fullname(user),
        "email": user.email,
        "user_id": user.id,
    }


class RegistrationView(APIView):
    """Register a new user and return an auth token (open endpoint)."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Create the user and respond with token and user data."""
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            build_auth_response(user), status=status.HTTP_201_CREATED
        )


class LoginView(APIView):
    """Log a user in with email and password (open endpoint)."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Validate the credentials and respond with token and user data."""
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        return Response(build_auth_response(user), status=status.HTTP_200_OK)


class EmailCheckView(APIView):
    """Look up a registered user by email address."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return the user for the given email or 404 if unknown."""
        serializer = EmailCheckSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        user = get_object_or_404(
            User, email__iexact=serializer.validated_data["email"]
        )
        return Response(UserSummarySerializer(user).data)
