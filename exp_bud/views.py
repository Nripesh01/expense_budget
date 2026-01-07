from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Group, Member
from .serializers import GroupSerializer, AddMemberSerializer, RegisterSerializer, UserProfileSerializer, UserUpdateSerializer
from django.contrib.auth import get_user_model
from rest_framework.views import APIView

User = get_user_model()

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        serializer = UserProfileSerializer(user)
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
        group = Group.objects.filter(id=group_id, members=request.user).first() 
        # user can only access groups they are already a member of
        if not group:
            return Response({'detail': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if group.created_by_id != request.user.id:
            return Response({'detail': 'Only the group creator can add members'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        
        user_to_add = serializer.validated_data['username']
        
        if not user_to_add:
            return Response({'detail': 'User not found'}, status=400)
        
        member, created = Member.objects.get_or_create(group=group, user=user_to_add)
        
        if not created:
            return Response({'detail': 'User is already a member'}, status=status.HTTP_200_OK)
        
        return Response({'detail': 'Member is added'}, status=status.HTTP_201_CREATED)
       
    
    
class RemoveMemberView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
        
    def delete(self, request, group_id, user_id):
        group = Group.objects.filter(id=group_id, members=request.user).first()
            
        if not group:
                return Response({'detail': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)
            
        if group.created_by.id != request.user.id:
                return Response({'detail': 'Only the group creator delete the members'}, status=status.HTTP_403_FORBIDDEN)
            
        if user_id == group.created_by.id:
                return Response({'detail': 'Creator cannot be removed'}, status=status.HTTP_400_BAD_REQUEST)
            
        delete_count, _ = Member.objects.filter(group=group, user_id=user_id).delete()
            # _ mean I don’t care about this value.”
            # It only deletes the membership link between that specific group and that specific user.
            # deleted_count == 1 → the membership was removed successfully
            
        if delete_count == 0: # there was no such member row (user wasn’t a member)
                return Response({'detail': 'Member not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)