"""URL routes of the kanban app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AssignedTasksView,
    BoardViewSet,
    CommentDeleteView,
    CommentListCreateView,
    ReviewingTasksView,
    TaskViewSet,
)

router = DefaultRouter()
router.register("boards", BoardViewSet, basename="board")
router.register("tasks", TaskViewSet, basename="task")

urlpatterns = [
    path(
        "tasks/assigned-to-me/",
        AssignedTasksView.as_view(),
        name="tasks-assigned-to-me",
    ),
    path(
        "tasks/reviewing/",
        ReviewingTasksView.as_view(),
        name="tasks-reviewing",
    ),
    path(
        "tasks/<int:task_id>/comments/",
        CommentListCreateView.as_view(),
        name="task-comments",
    ),
    path(
        "tasks/<int:task_id>/comments/<int:pk>/",
        CommentDeleteView.as_view(),
        name="task-comment-detail",
    ),
    path("", include(router.urls)),
]
