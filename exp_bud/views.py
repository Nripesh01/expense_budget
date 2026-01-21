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
            raise PermissionError('Only creator can update group')
        serializer.save()
        
    def perform_destroy(self, instance):
        if instance.created_by_id != self.request.user.id:
            raise PermissionError('Only creator can delete group')
        instance.delete()



class AddMemberView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddMemberSerializer
    
    def post(self, request, group_id):
        group = Group.objects.filter(id=group_id, members=self.request.user).first()
        if not group:
            return Response({'detail': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if group.created_by.id != self.request.user.id:
            return Response({'detail': 'Only the creator can add members'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(data=request.data) # create the serializer instance with data
        serializer.is_valid(raise_exception=True) # runs all validations:(Field types (CharField, EmailField, etc.), Required fields)
        user_to_add = serializer.validated_data['username']
        
        member, created = Member.objects.get_or_create(group=group, user=user_to_add)
        
        if not created: # handles the “already exists” case
            return Response({'detail': 'User is already a member'}, status=status.HTTP_200_OK)
        
        return Response({'detail': 'Member is added'}, status=status.HTTP_201_CREATED)
    


class RemoveMemberView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, group_id, user_id):
        group = Group.objects.filter(id=group_id, members=self.request.user).first()
        if not group:
            return Response({'detail': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if group.created_by.id != self.request.user.id:
            return Response({'detail': 'Only the group creator can remove members'}, status=status.HTTP_403_FORBIDDEN)
        
        if user_id == group.created_by.id:
            return Response({'detail': 'Creator cannot be deleted'}, status=status.HTTP_400_BAD_REQUEST)
        
        delete_count, _ = Member.objects.filter(group=group, user_id=user_id).delete() 
        # .delete() methods returns a tuple with two things : (number_of_objects_deleted, { "model_name": number_deleted, ... })
        # _ is a convention in Python meaning “we don’t care about (the dictionary with per-model deletion counts)

        if delete_count == 0:
            return Response({'detail': 'Member not found'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(status=status.HTTP_204_NO_CONTENT)
        # mean member was successfully deleted, but there’s nothing else to return to the client.
        
        


class CategoryListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CategorySerializer
    
    def dispatch(self, request, *args, **kwargs): # dispatch is a DRF/Django method that receives every HTTP request 
        # first and then routes that request to the correct handler method (get(), post(), put(), patch(), delete(), etc.).
        # Overriding dispatch() lets you do pre-processing before any HTTP method runs, like fetching a group and 
        # storing it in self.group for later use in get(), post(), or serializers. 
        self.group = get_object_or_404(Group, id=kwargs['group_id'], members=self.request.user)
                                              # kwargs['group_id'], get the group ID from the URL
        return super().dispatch(request, *args, **kwargs)
        # call the parent in dispatch() for routing, authentication, permissions,etc., 
        # while still doing custom pre-processing before the request reaches the handler method
    
    def get_queryset(self):
        return Category.objects.filter(group=self.group).order_by('name')
    
    def perform_create(self, serializer):
        serializer.save(group=self.group)




class ExpenseListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsGroupMember]
    serializer_class = ExpenseSerializer
    
    def dispatch(self, request, *args, **kwargs):
        self.group = get_object_or_404(Group, id=kwargs['group_id'], members=self.request.user)
        return super().dispatch(request, *args, **kwargs)
     
    def get_queryset(self):
        return ( Expense.objects.filter(group=self.group).select_related('category', 'paid_by', 'created_by')
                .prefetch_related('splits__user').order_by('name'))
    
    def get_serializer_context(self):
        ctx = super().get_serializer_context() # we call the parent class via super() to keep DRF’s
                             #  default context (request, view, format) and then add our custom data (group) safely.
        ctx['group'] = self.group # default group
        return ctx
    
    def perform_create(self, serializer):
        serializer.save(self.request.user)
        
    