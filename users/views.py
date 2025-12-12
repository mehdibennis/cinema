from django.contrib.auth import get_user_model
from rest_framework import permissions, viewsets

from .serializers import UserSerializer

User = get_user_model()


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet to list users (Admin only).
    ReadOnly because user creation is done via spectator registration.
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]
