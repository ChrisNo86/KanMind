"""Object level permissions for boards, tasks and comments."""

from rest_framework.permissions import BasePermission


def is_board_member(user, board):
    """Return True if the user owns the board or is one of its members."""
    if board.owner_id == user.id:
        return True
    return board.members.filter(pk=user.pk).exists()


class IsBoardOwnerOrMember(BasePermission):
    """Allow access to a board for its owner and its members."""

    message = "You must be the owner or a member of this board."

    def has_object_permission(self, request, view, obj):
        """Return True if the user owns or is a member of the board."""
        return is_board_member(request.user, obj)


class IsBoardOwner(BasePermission):
    """Allow access to a board only for its owner."""

    message = "Only the owner of this board can do this."

    def has_object_permission(self, request, view, obj):
        """Return True if the user owns the board."""
        return obj.owner_id == request.user.id


class IsTaskBoardMember(BasePermission):
    """Allow access to a task for members of the task's board."""

    message = "You must be a member of the board this task belongs to."

    def has_object_permission(self, request, view, obj):
        """Return True if the user is a member of the task's board."""
        return is_board_member(request.user, obj.board)


class IsTaskCreatorOrBoardOwner(BasePermission):
    """Allow access to a task for its creator and the board owner."""

    message = "Only the task creator or the board owner can do this."

    def has_object_permission(self, request, view, obj):
        """Return True if the user created the task or owns its board."""
        user_id = request.user.id
        return user_id in (obj.created_by_id, obj.board.owner_id)


class IsCommentAuthor(BasePermission):
    """Allow access to a comment only for its author."""

    message = "Only the author of this comment can do this."

    def has_object_permission(self, request, view, obj):
        """Return True if the user wrote the comment."""
        return obj.author_id == request.user.id
