from django.contrib.auth import get_user_model
from .models import Group, Member
from rest_framework import serializers

User = get_user_model() # returns the actual User model class

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'password']
        read_only_fields = ['id']
        
    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
        )
        


class MemberInfoSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Member
        fields = ['id', 'username', 'join_at']
        read_only_fields = fields


class GroupSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    members_info = MemberInfoSerializer(source='members_link', many=True, read_only=True)
    
    class Meta:
        model = Group
        fields = ['id', 'name', 'created_by', 'created_at', 'created_by_username', 'members_info']
        read_only_fields = ['id', 'created_by', 'created_at']
        

class AddMemberSerializer(serializers.Serializer):
    username = serializers.CharField()
    
    def validate_username(self, value):
        try:
            user = User.objects.get(username=value)
        except User.DoesNotExist:
            raise serializers.ValidationError('User not found')
        return user

