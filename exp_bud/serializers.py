from decimal import Decimal
from django.db import transaction # transaction : Django groups multiple database operations into one atomic unit.
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Group, Member, Category, Expense, ExpenseSplit, BudgetPeriod ,Settlement

User = get_user_model()

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
        fields = ['id', 'email', 'username', 'password']
        read_only_fields = ['id']
    
    def create(self, validated_data):  # create() Called when you do serializer.save()
        return User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data.get['email'],
        )


class MemberInfoSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    
    class Meta:
        model = Member
        fields = ['id', 'user_id', 'username', 'role', 'joined_at']
        read_only_fields = fields
        


class GroupSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    members_info = MemberInfoSerializer(source='member_links', many=True, read_only=True)
    
    class Meta:
        model = Group
        fields = ['id', 'name', 'created_by', 'created_at', 'currency', 'created_by_username', 'members_info']
        read_only_fields = ['id', 'name', 'created_by', 'created_at', 'created_by_username', 'members_info']
        
        
class AddMemberSerializer(serializers.Serializer):
    username = serializers.CharField()

   # def validate_username(self, value): # field level validation (validate_<fieldname>(self, value))