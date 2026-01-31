from django.urls import path
from .views import ( UserProfileView, UserUpdateView, RegisterView, GroupListCreateView, GroupDetailView,
                    AddMemberView, RemoveMemberView, CategoryListCreateView, ExpenseListCreateView,
                    ExpenseDetailView, BudgetUpsertView, SettlementListCreateView, GroupSummaryView,
)



urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    # as_view() converts a class-based view into a callable function that Django can execute when a request comes in.
    
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/update/', UserUpdateView.as_view(), name='profile-update'),
    
    path('groups/', GroupListCreateView.as_view(), name='group-list-create'),
    path('groups/<int:pk>/', GroupDetailView.as_view(), name='group-detail'),
    
    path('groups/<int:group_id>/add-member/', AddMemberView.as_view(), name='add-member'),
    path('groups/<int:group_id>/remove-member/<int:user_id>/', RemoveMemberView.as_view(), name='remove-member'),
    
    path('groups/<int:group_id>/categories/', CategoryListCreateView.as_view(), name='category-list-create'),
    
    path('groups/<int:group_id>/expenses/', ExpenseListCreateView.as_view(), name='expense-list-create'),
    path('groups/<int:group_id>/expense/<int:pk>/', ExpenseDetailView.as_view(), name='expense-detail'),
    
    path('groups/<int:group_id>/budget/', BudgetUpsertView.as_view(), name='budget-upsert'),
    
    path('groups/<int:group_id>/settlements/', SettlementListCreateView.as_view(), name='settlement-list-create'),
    
    path('groups/<int:group_id>/summary/', GroupSummaryView.as_view(), name='group-summary'),
]
