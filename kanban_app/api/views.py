"""API views for boards, tasks and comments."""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated

from kanban_app.models import Board, Comment, Task

from .permissions import (
    IsBoardOwner,
    IsBoardOwnerOrMember,
    IsCommentAuthor,
    IsTaskBoardMember,
    IsTaskCreatorOrBoardOwner,
    is_board_member,
)
from .serializers import (
    BoardDetailSerializer,
    BoardListSerializer,
    BoardUpdateSerializer,
    CommentSerializer,
    TaskSerializer,
    TaskUpdateSerializer,
)


class BoardViewSet(viewsets.ModelViewSet):
    """List, create, retrieve, update and delete boards."""

    queryset = Board.objects.all()
    serializer_class = BoardListSerializer
    permission_classes = [IsAuthenticated, IsBoardOwnerOrMember]
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        """List only accessible boards; detail lookups see all boards."""
        if self.action != "list":
            return self.queryset
        user = self.request.user
        return self.queryset.filter(Q(owner=user) | Q(members=user)).distinct()

    def get_serializer_class(self):
        """Pick the serializer matching the current action."""
        if self.action == "retrieve":
            return BoardDetailSerializer
        if self.action == "partial_update":
            return BoardUpdateSerializer
        return self.serializer_class

    def get_permissions(self):
        """Only the board owner may delete a board."""
        if self.action == "destroy":
            return [IsAuthenticated(), IsBoardOwner()]
        return super().get_permissions()

    def perform_create(self, serializer):
        """Set the requesting user as board owner."""
        serializer.save(owner=self.request.user)


class TaskViewSet(viewsets.ModelViewSet):
    """Create, update and delete tasks."""

    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsTaskBoardMember]
    http_method_names = ["post", "patch", "delete"]

    def get_serializer_class(self):
        """Use the restricted serializer for updates."""
        if self.action == "partial_update":
            return TaskUpdateSerializer
        return self.serializer_class

    def get_permissions(self):
        """Only the task creator or the board owner may delete a task."""
        if self.action == "destroy":
            return [IsAuthenticated(), IsTaskCreatorOrBoardOwner()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        """Check board existence (404) and membership (403) first."""
        board = self.get_board_from_request()
        if not is_board_member(request.user, board):
            raise PermissionDenied("You must be a member of this board.")
        return super().create(request, *args, **kwargs)

    def get_board_from_request(self):
        """Return the board referenced in the request body or raise 404."""
        board_id = self.request.data.get("board")
        if not str(board_id).isdigit():
            raise ValidationError({"board": "A valid board id is required."})
        return get_object_or_404(Board, pk=board_id)

    def perform_create(self, serializer):
        """Set the requesting user as creator of the task."""
        serializer.save(created_by=self.request.user)


class AssignedTasksView(generics.ListAPIView):
    """List all tasks assigned to the requesting user."""

    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return tasks where the user is the assignee."""
        return self.queryset.filter(assignee=self.request.user)


class ReviewingTasksView(generics.ListAPIView):
    """List all tasks the requesting user has to review."""

    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return tasks where the user is the reviewer."""
        return self.queryset.filter(reviewer=self.request.user)


class CommentListCreateView(generics.ListCreateAPIView):
    """List and create comments of a task."""

    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, IsTaskBoardMember]

    def get_task(self):
        """Return the task from the URL and check board membership."""
        task = get_object_or_404(Task, pk=self.kwargs["task_id"])
        self.check_object_permissions(self.request, task)
        return task

    def get_queryset(self):
        """Return the task's comments in chronological order."""
        return self.queryset.filter(task=self.get_task())

    def perform_create(self, serializer):
        """Attach the comment to the task and the requesting user."""
        serializer.save(task=self.get_task(), author=self.request.user)


class CommentDeleteView(generics.DestroyAPIView):
    """Delete a comment; only its author is allowed to."""

    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, IsCommentAuthor]

    def get_object(self):
        """Return the comment of the given task or raise 404."""
        task = get_object_or_404(Task, pk=self.kwargs["task_id"])
        comment = get_object_or_404(
            self.queryset, pk=self.kwargs["pk"], task=task
        )
        self.check_object_permissions(self.request, comment)
        return comment
