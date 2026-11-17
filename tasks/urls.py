from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter(trailing_slash=False)
router.register("tasks", views.TaskViewSet, basename="task")

urlpatterns = router.urls
