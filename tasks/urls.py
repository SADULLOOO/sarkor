from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter(trailing_slash=False)
router.register("tasks", views.TaskViewSet, basename="task")

urlpatterns = [
    path("executors/<int:user_id>/reviews", views.ExecutorReviewListView.as_view(), name="executor-reviews"),
    *router.urls,
]
