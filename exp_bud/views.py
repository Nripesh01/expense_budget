from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Group, GroupMember
from .serializers import GroupSerializer, AddMemberSerializer
from django.contrib.auth import get_user_model

User = get_user_model

class GroupListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GroupSerializer
    
    def get_queryset(self):
        return Group.objects.filter(member__user=self.request.user).distinct()
        # show only groups where current user is a member
    
    def perform_create(self, serializer):
        group = serializer.save(created_by=self.request.user)
         # creator automatically becomes a member
        GroupMember.objects.create(group=group, user=self.request.user)
        

class AddMemberView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddMemberSerializer
    
    def post(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id, member__user=request.user)
        except Group.DoesNotExist:
            return Response({'detail': 'Group not found'}, status=404)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_to_add = User.objects.get(username=serializer.validated_data['username'])
        GroupMember.objects.get_or_create(group=group, user=user_to_add)
        
        return Response({'detail': 'Member is added'}, status=status.HTTP_201_CREATED)
    