from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Group, Member
from .serializers import GroupSerializer, AddMemberSerializer, RegisterSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


class GroupListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GroupSerializer
    
    def get_queryset(self):
        return Group.objects.filter(members=self.request.user).distinct()
        # show only groups where current user is a member
    
    def perform_create(self, serializer):
        group = serializer.save(created_by=self.request.user) # Any authenticated user can create a group.
         # creator automatically becomes a member
        Member.objects.create(group=group, user=self.request.user)
        


class AddMemberView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddMemberSerializer
    
    def post(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id, members=request.user) # Must be a member of the group to add members
        except Group.DoesNotExist:
            return Response({'detail': 'Group not found'}, status=400)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data['username']
        
        user_to_add = User.objects.filter(username=username).first()
        
        if not user_to_add:
            return Response({'detail': 'User not found'}, status=400)
        
        member, created = Member.objects.get_or_create(group=group, user=user_to_add)
        
        if not created:
            return Response({'detail': 'User is already a member'}, status=200)
        
        return Response({'detail': 'Member is added'}, status=status.HTTP_201_CREATED)
       
    