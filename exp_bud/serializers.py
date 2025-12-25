from django.contrib.auth import get_user_model
from .models import Group, GroupMember
from rest_framework import serializers

User = get_user_model

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name', 'created_by', 'created_at']
        read_only_fields = ['id', 'created_by', 'created_at']
        

class AddMemberSerializer(serializers.Serializer):
    username = serializers.CharField()
    
    def validate_username(self, value):
        try:
            user = User.objects.get(username=value)
        except User.DoesNotExist:
            raise serializers.ValidationError('User not found')
        return value
    