from decimal import Decimal
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView


from django.contrib.auth import get_user_model
from .models import Group, Member, Expense, ExpenseSplit, BudgetPeriod, Settlement, Category
from .serializers import ( GroupSerializer, AddMemberSerializer,
    RegisterSerializer, UserProfileSerializer, UserUpdateSerializer,
    CategorySerializer, ExpenseSerializer, BudgetPeriodSerializer, SettlementSerializer )
from .permissions import IsGroupCreator, IsGroupMember, IsGroupCreatorOrExpenseCreator

User = get_user_model()



class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    

class UserUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserUpdateSerializer
    
    def get_object(self):
        return self.request.user
    

class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    

class GroupListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GroupSerializer
    
    def get_queryset(self):
        return (Group.objects.filter(members=self.request.user).distinct().prefetch_related('member_links__user'))
    
    def perform_create(self, serializer):
        group = serializer.save(created_by=self.request.user)
        # creator becomes a member with CREATOR role
        Member.objects.create(group=group, user=self.request.user, role=Member.Role.CREATOR)


class GroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GroupSerializer
    
    def get_queryset(self):
        return Group.objects.filter(members=self.request.user).distinct()
    
    def perform_update(self, serializer):
        group = self.get_object()
        if group.created_by_id != self.request.user.id:
            raise PermissionError('Only creator can update the group')
        serializer.save()
        
    def perform_destroy(self, instance):
        if instance.created_by_id != self.request.user.id:
            raise PermissionError('Only creator can delete the group')
        instance.delete()
        