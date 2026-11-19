"""Serializers for registration, login and user representation."""

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers


def get_fullname(user):
    """Return the display name of a user built from first and last name."""
    return f"{user.first_name} {user.last_name}".strip()


class UserSummarySerializer(serializers.ModelSerializer):
    """Compact user representation used across the whole API."""

    fullname = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "fullname"]

    def get_fullname(self, obj):
        """Return the full name of the user."""
        return get_fullname(obj)


class RegistrationSerializer(serializers.ModelSerializer):
    """Validate registration data and create a new user."""

    fullname = serializers.CharField(max_length=150)
    repeated_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["fullname", "email", "password", "repeated_password"]
        extra_kwargs = {
            "email": {"required": True, "allow_blank": False},
            "password": {"write_only": True},
        }

    def validate_email(self, value):
        """Ensure the email address is not registered yet."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email is already registered.")
        return value.lower()

    def validate_fullname(self, value):
        """Ensure the full name contains at least first and last name."""
        if len(value.split()) < 2:
            raise serializers.ValidationError(
                "Please enter first and last name."
            )
        return value.strip()

    def validate(self, attrs):
        """Ensure both password fields match."""
        if attrs["password"] != attrs["repeated_password"]:
            raise serializers.ValidationError(
                {"repeated_password": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        """Create the user; the email doubles as unique Django username."""
        first_name, last_name = validated_data["fullname"].split(" ", 1)
        return User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=first_name,
            last_name=last_name,
        )


class LoginSerializer(serializers.Serializer):
    """Authenticate a user by email and password."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Resolve the user by email and check the password."""
        user = User.objects.filter(email__iexact=attrs["email"]).first()
        if user is not None:
            user = authenticate(
                username=user.username, password=attrs["password"]
            )
        if user is None:
            raise serializers.ValidationError("Invalid email or password.")
        attrs["user"] = user
        return attrs


class EmailCheckSerializer(serializers.Serializer):
    """Validate the email query parameter of the email check."""

    email = serializers.EmailField()
