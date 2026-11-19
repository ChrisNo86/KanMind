"""Serializers for boards, tasks and comments."""

from django.contrib.auth.models import User
from rest_framework import serializers

from auth_app.api.serializers import UserSummarySerializer, get_fullname
from kanban_app.models import Board, Comment, Task

from .permissions import is_board_member


class TaskSerializer(serializers.ModelSerializer):
    """Full task representation used for creation and task lists."""

    assignee = UserSummarySerializer(read_only=True)
    reviewer = UserSummarySerializer(read_only=True)
    assignee_id = serializers.PrimaryKeyRelatedField(
        source="assignee", queryset=User.objects.all(),
        write_only=True, required=False, allow_null=True,
    )
    reviewer_id = serializers.PrimaryKeyRelatedField(
        source="reviewer", queryset=User.objects.all(),
        write_only=True, required=False, allow_null=True,
    )
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id", "board", "title", "description", "status", "priority",
            "assignee", "reviewer", "assignee_id", "reviewer_id",
            "due_date", "comments_count",
        ]

    def get_comments_count(self, obj):
        """Return the number of comments on the task."""
        return obj.comments.count()

    def validate(self, attrs):
        """Ensure assignee and reviewer are members of the task's board."""
        board = attrs.get("board") or self.instance.board
        for field in ("assignee", "reviewer"):
            user = attrs.get(field)
            if user is not None and not is_board_member(user, board):
                raise serializers.ValidationError(
                    {f"{field}_id": "User must be a member of the board."}
                )
        return attrs


class TaskUpdateSerializer(TaskSerializer):
    """Task representation for PATCH; the board cannot be changed."""

    class Meta(TaskSerializer.Meta):
        fields = [
            "id", "title", "description", "status", "priority",
            "assignee", "reviewer", "assignee_id", "reviewer_id",
            "due_date",
        ]

    def validate(self, attrs):
        """Reject attempts to move the task to another board."""
        board_id = self.initial_data.get("board")
        if board_id is not None and str(board_id) != str(
            self.instance.board_id
        ):
            raise serializers.ValidationError(
                {"board": "Changing the board of a task is not allowed."}
            )
        return super().validate(attrs)


class BoardTaskSerializer(TaskSerializer):
    """Task representation nested in the board detail (without board)."""

    class Meta(TaskSerializer.Meta):
        fields = [
            "id", "title", "description", "status", "priority",
            "assignee", "reviewer", "due_date", "comments_count",
        ]


class BoardListSerializer(serializers.ModelSerializer):
    """Board overview with counters; also used to create boards."""

    members = serializers.PrimaryKeyRelatedField(
        many=True, queryset=User.objects.all(), write_only=True,
        required=False,
    )
    member_count = serializers.SerializerMethodField()
    ticket_count = serializers.SerializerMethodField()
    tasks_to_do_count = serializers.SerializerMethodField()
    tasks_high_prio_count = serializers.SerializerMethodField()
    owner_id = serializers.ReadOnlyField(source="owner.id")

    class Meta:
        model = Board
        fields = [
            "id", "title", "members", "member_count", "ticket_count",
            "tasks_to_do_count", "tasks_high_prio_count", "owner_id",
        ]

    def get_member_count(self, obj):
        """Return the number of board members."""
        return obj.members.count()

    def get_ticket_count(self, obj):
        """Return the number of tasks on the board."""
        return obj.tasks.count()

    def get_tasks_to_do_count(self, obj):
        """Return the number of tasks with status 'to-do'."""
        return obj.tasks.filter(status=Task.Status.TO_DO).count()

    def get_tasks_high_prio_count(self, obj):
        """Return the number of tasks with priority 'high'."""
        return obj.tasks.filter(priority=Task.Priority.HIGH).count()


class BoardDetailSerializer(serializers.ModelSerializer):
    """Board with its members and tasks."""

    owner_id = serializers.ReadOnlyField(source="owner.id")
    members = UserSummarySerializer(many=True, read_only=True)
    tasks = BoardTaskSerializer(many=True, read_only=True)

    class Meta:
        model = Board
        fields = ["id", "title", "owner_id", "members", "tasks"]


class BoardUpdateSerializer(serializers.ModelSerializer):
    """Update title and members of a board (PATCH)."""

    members = serializers.PrimaryKeyRelatedField(
        many=True, queryset=User.objects.all(), write_only=True,
        required=False,
    )
    owner_data = UserSummarySerializer(source="owner", read_only=True)
    members_data = UserSummarySerializer(
        source="members", many=True, read_only=True
    )

    class Meta:
        model = Board
        fields = ["id", "title", "members", "owner_data", "members_data"]


class CommentSerializer(serializers.ModelSerializer):
    """Comment with the author's full name."""

    author = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "created_at", "author", "content"]
        read_only_fields = ["id", "created_at"]

    def get_author(self, obj):
        """Return the full name of the comment author."""
        return get_fullname(obj.author)
