from django.urls import path
from .views import GroupListCreateView, AddMemberView, RegisterView, UserProfileView, UserUpdateView, RemoveMemberView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('group/', GroupListCreateView.as_view(), name='group'),
    path('group/<int:group_id>/add-member/', AddMemberView.as_view(), name='add_member'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/<int:pk>/', UserUpdateView.as_view(), name='profile-update'),
     path("group/<int:group_id>/remove-member/<int:user_id>/", RemoveMemberView.as_view(), name="remove_member"),
]
