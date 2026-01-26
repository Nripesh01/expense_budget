from decimal import Decimal
from django.db import transaction # transaction : a group of database operations that must succeed together as one unit.
                                  # It follows the rule: all succeed (commit) or none succeed (rollback).
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Group, Member, Category, Expense, ExpenseSplit, BudgetPeriod, Settlement

User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'password', 'email']


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
            email=validated_data.get('email'),
        )


class MemberInfoSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    # source mean go through a related object to get a field. (. → traverse the relation, in serializer 
                                                     # (.) only working with Python objects, not the database.)
    class Meta:
        model = Member
        fields = ['id', 'user_id', 'username', 'role', 'joined_at']
        read_only_fields = fields
        

class CategorySerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True)
    class Meta:
        model = Category
        fields = ['id','group','group_name' ,'name', 'created_at']
        read_only_fields = ['id', 'created_at']


class GroupSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    members_info = MemberInfoSerializer(source='member_links', many=True, read_only=True)
    categories = CategorySerializer(source='categories', many=True, read_only=True)
    
    class Meta:
        model = Group
        fields = ['id', 'name', 'created_by', 'currency', 'created_by_username', 'members_info', 'created_at']
        read_only_fields = ['id', 'name', 'created_by', 'created_at', 'created_by_username', 'members_info']
        

class AddMemberSerializer(serializers.Serializer):
    username = serializers.CharField()
    
    def validate_username(self, value): # field level validation (validate_<fieldname>(self, value)
                                        # use when Validation depends on one field only
        try:
            return User.objects.get(username=value)
        except User.DoesNotExist:
            raise serializers.ValidationError('User not found')
        

class ExpenseSplitInputSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    share = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.00'))
    

class ExpenseSplitOutputSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    
    class Meta:
        model = ExpenseSplit
        fields = ['id', 'user_id', 'username','expense', 'share']
        

class ExpenseSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    paid_by_username = serializers.CharField(source='paid_by.username', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    splits = ExpenseSplitOutputSerializer(many=True, read_only=True)
    
    # input-only fields for create
    category_id = serializers.IntegerField(required=False, allow_null=True)
    paid_by_id = serializers.IntegerField()
    split_items = ExpenseSplitInputSerializer(many=True, required=False)    
    
    class Meta:
        model = Expense
        fields = ['id', 'group', 'description', 'amount', 'spent_at', 'category_id', 'category_name', 'created_by', 
                  'created_by_username', 'paid_by_id','paid_by_username', 'splits', 'split_items']
        
        read_only_fields = ['id', 'group', 'created_by', 'created_by_username', 'category_name', 'paid_by_username', 
                'created_at','splits']
        
        
    def validate(self, attrs):  # object-level validation, use when Validation depends on multiple fields together, 
                                # attrs is a dictionary of the validated fields for the serializer
        group = self.context['group'] # context is a dictionary used for runtime data passed from View to Serializer
                                      # Used for authorization, validation, and controlled object creation
                                      # uses of context : security and validation, object creation, access request user
        request = self.context['request']
        
        # paid_by user must be a member of the group
        try:
            paid_by = User.objects.get(id=attrs['paid_by_id'])
        except User.DoesNotExist:
            raise serializers.ValidationError({'paid_by_id': 'Invalid User'})
        
        if not Member.objects.filter(group=group, user=paid_by).exists():  # exists() → checks if any row exists (True or False)
            raise serializers.ValidationError({'paid_by_id': 'paid_by user must be a member of the group'})
        
        # category must belongs to the same group (if provided)
        cat_id = attrs.get('category_id', None)
        if cat_id is not None:
            if not Category.objects.filter(id=cat_id, group=group).exists():
                raise serializers.ValidationError({'category_id': 'category id does not belongs to the group'})
        
        # validate split 
        split_items = attrs.get('split_items')
        if split_items:
            member_ids = set(Member.objects.filter(group=group).values_list('user_id', flat=True))
            # values_list("user_id") is a Django ORM method used to fetch only one column from the database
            # flat=True give just the user IDs as a plain list
            total = Decimal('0.00')
            for item in split_items:
                if item['user_id'] not in member_ids:
                    raise serializers.ValidationError({'split_items': 'split user must be the member of the group'})
                total += item['share']
            
            if total != attrs['amount']:
                raise serializers.ValidationError({'split_items": "split total must equal the expense amount'})
        
        return attrs
    
    
    @transaction.atomic
    def create(self, validated_data): # validated_data is a dictionary(key --> value)
        group = self.context['group']
        request = self.context['request']
        
        cat_id = validated_data.pop('category_id', None) 
        # pop removes key from the dictionary and returns its value  (data = {"paid_by_id": 10, "amount": 250})
                                                                     # x = data.pop("paid_by_id")
                                                                     # x == 10
                                                                     # data == {"amount": 250}
        paid_by_id = validated_data.pop('paid_by_id')
        split_items = validated_data.pop('split_items', None)
        
        category = None
        if cat_id is not None:
            category = Category.objects.get(id=cat_id, group=group)
        
        paid_by = User.objects.get(id=paid_by_id, group=group)
        
        expense = Expense.objects.create(
            group=group,
            category=category,
            paid_by=paid_by,
            created_by=request.user,
            **validated_data,
        )
        
        # If client did not send split_items, do equal split across current members
        if not split_items:
            member_ids = list(Member.objects.filter(group=group).values_list('user_id', flat=True))
            count = len(member_ids)
            if count == 0:
                raise serializers.ValidationError('Group has no member')
        
            amount = expense.amount
            base = (amount/count).quantize(Decimal('0.01')) # quantize is used to round a Decimal to a fixed number of decimal places.
            shares = [base] * count
        
            # fix rounding remainder
            remainder = amount - sum(shares) # remainder ensures the total of all shares equals the original amount 
            shares[-1] = shares[-1] + remainder
        
            for uid, share in zip(member_ids, shares):
                # zip() is a Python built-in function that combines multiple lists into pairs (tuples) element by element.
                # each member ID gets its corresponding share.
                ExpenseSplit.objects.create(expense=expense, user_id=uid, share=share)
        
        else:
            for item in split_items:
                ExpenseSplit.objects.create(expense=expense, user_id=item['user_id'], share=item['share'])
        


class BudgetPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetPeriod
        fields = ['id', 'year', 'month', 'limit', 'created_at']
        read_only_fields = ['id', 'created_at']
        


class SettlementSerializer(serializers.ModelSerializer):
    from_username = serializers.CharField(source='from_user.username', read_only=True)
    to_username = serializers.CharField(source='to_user.username', read_only=True)
    
    class Meta:
        model = Settlement
        fields = ['id', 'from_user', 'from_username', 'to_user', 'to_username', 'amount', 'note', 'settled_at']
        read_only_fields = ['id', 'from_username', 'to_username']