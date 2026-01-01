from django.urls import path
from .views import GroupListCreateView, AddMemberView, RegisterView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('group/', GroupListCreateView.as_view(), name='group'),
    path('group/<int:group_id>/add-member/', AddMemberView.as_view(), name='add_member'),
]
