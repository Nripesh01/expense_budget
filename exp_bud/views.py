from decimal import Decimal
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework import generics, status,serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.utils import timezone # timezone module contains multiple utilities, including:
                                    # now(), datetime, timedelta, get_current_timezone()
from rest_framework.exceptions import PermissionDenied


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
    
    def get(self, request, group_id):
        # make sure the group exists and the user is a member
        group = get_object_or_404(Group, id=group_id, members=request.user)
        categories = Category.objects.filter(group=group)
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id, members=request.user)

        # include the group in the serializer
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(group=group)  # automatically assign the group
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class ExpenseListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsGroupMember]
    serializer_class = ExpenseSerializer
    
    def dispatch(self, request, *args, **kwargs):
        self.group = get_object_or_404(Group, id=kwargs['group_id'], members=self.request.user)
        return super().dispatch(request, *args, **kwargs)
     
     # select_related = fetch related single objects in the same query(OneToOne, Foreignkey)
     # prefetch_related = fetch related lists of objects in separate query, cached in Python (ManyToMany, reverse Foreignkey)
     
    def get_queryset(self):
        return ( Expense.objects.filter(group=self.group).select_related('category', 'paid_by', 'created_by')
                .prefetch_related('splits__user').order_by('name'))
    
    def get_serializer_context(self):
        ctx = super().get_serializer_context() # we call the parent class via super() to keep DRF’s
        # returns a default dict of {'request', 'view', 'format'} by default; can be overridden to add custom context.
        ctx['group'] = self.group # default group
        return ctx
    
    def perform_create(self, serializer):
        serializer.save(group=self.group, created_by=self.request.user)
        


class ExpenseDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsGroupCreatorOrExpenseCreator]
    serializer_class = ExpenseSerializer
    
    def dispatch(self, request, *args, **kwargs):
        self.group = get_object_or_404(Group, id=kwargs['group_id'], members=self.request.user)
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        return Expense.objects.filter(group=self.group).select_related('category', 'paid_by', 'created_by')
    



class BudgetUpsertView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsGroupCreator, IsGroupMember]
    serializer_class = BudgetPeriodSerializer
    
    def dispatch(self, request, *args, **kwargs):
        self.group = get_object_or_404(Group, id=kwargs['group_id'], members=self.request.user)
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request, group_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        year = serializer.validated_data['year']
        month = serializer.validated_data['month']
        limit = serializer.validated_data['limit']
        
        budget, _ = BudgetPeriod.objects.update_or_create( # update_or_create is UPSERT logic. In db terms, it mean,
                                                          # Update if the record exists, otherwise Insert a new record.
            group=self.group, year=year, month=month,
            defaults={'limit': limit, 'created_by': request.user},
        )
        
        return Response(BudgetPeriodSerializer(budget).data, status=status.HTTP_200_OK)




class SettlementListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsGroupMember]
    serializer_class = SettlementSerializer
    
    def dispatch(self, request, *args, **kwargs):
        self.group = get_object_or_404(Group, id=kwargs['group_id'], members=self.request.user)
        return super().dispatch(request,*args, **kwargs)
    
    def get_queryset(self):
        return Settlement.objects.filter(group=self.group).select_related('from_user', 'to_user').order_by('-settled_at')
    
    def perform_create(self, serializer):
        from_user = serializer.validated_data['from_user']
        to_user = serializer.validated_data['to_user']
        
        if not Member.objects.filter(group=self.group, user=from_user).exists():
            raise serializers.ValidationError({'from_user': 'Not a group member'})
        
        if not Member.objects.filter(group=self.group, user=to_user).exists():
            raise serializers.ValidationError({'to_user': 'Not a group member'})
        
        serializer.save(group=self.group)


class GroupSummaryView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id, members=self.request.user)
        
        now = timezone.now() # Current date, time, with timezone
        year = int(request.query_params.get('year', now.year)) # year comes from the url
        month = int(request.query_params.get('month', now.month))
        day = int(request.query_params.get('day', now.day))
        
        start = timezone.datetime(year, month, day, tzinfo=timezone.get_current_timezone()) # tzinf assigns timezone to a datetime
        end = (start + timezone.timedelta(days=32).replace(day=1)) # timedelta a time difference.To say how much time to move
        
        expenses = Expense.objects.filter(group=group, spent_at__gte=start, spent_at__lt=end).select_related('paid_by')
        # gte,gt,lte,lt,_exact is field lookups  gte- greater than or equal to, lt - less than.
        #__ is used in ORM queries.like: field looksup, Traversing relationships, Ordering/annotations. ( __ --> the separator tells Django “apply a lookups field” 
        
        splits = ExpenseSplit.objects.filter(expense__in=expenses).select_related('user', 'expense')
        # expense is foreignKey, __in mean ORM lookup meaning “the value must be in this queryset, expenses is queryset 
        settlements = Settlement.objects.filter(group=group, settled_at__gte=start, settled_at__lt=end)
        
        
        total_spent = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        # aggregate is db-level calculation across all rows in QuerySet. common funcs: Sum, Avg, Count, Min, Max
        # if total has value use that. if not provided safe fallback to Deciaml('0.00')
        # ['total'] is dict key access and access the value from dictionary returned by aggregate
        budget = BudgetPeriod.objects.filter(group=group, year=year, month=month).first()
        budget_limit = budget.limit if budget else None
        remaining = (budget_limit - total_spent) if budget_limit is not None else None # this is null-safe conditional assignment
        
        # balances: + means user should receive, - means user owes
        member_ids = list(Member.objects.filter(group=group).values_list('user_id', flat=True))
        balances = {uid: Decimal('0.00') for uid in member_ids} # this is a dictionary comprehension
        # uid : Decimal('0.00), use uid as the key in dict and Decimal('0.00) as the value. eg: { 1: Decimal('2000.00'),}
        
        
        for e in expenses:
            balances[e.paid_by_id] += e.amount
            
        for s in splits:
            balances[s.user_id] -= s.share
        
        for st in settlements:
            balances[st.from_user_id] += st.amount
            balances[st.to_user_id] -= st.amount
        
        
        users = User.objects.filter(id__in=member_ids).only('id', 'username')
        id_to_name = {u.id: u.username for u in users}
        balance_list = [                          # .get(key, default),if found return value. If not return default-> str(uid) it is a null-safe / error-safe      
            {'user_id': uid, 'username': id_to_name.get(uid, str(uid)), 'net': str(balances[uid])} # balances[uid] → fetches that user’s net amount from the dictionary
            for uid in member_ids
        ]
        
        # [] is the dictionary lookup operator in Python used to access or update the value of a specific key in a dictionary
        
        
        
        return Response({
            'group_id': group.id,
            'group_name': group.name,
            'currency': group.currency,
            'period': {'year': year, 'month': month},
            'total_spent': str(total_spent),
            'budget_limit': str(budget_limit) if budget_limit is not None else None,
            'remaining': str(remaining) if remaining is not None else None,
            'balances': balance_list,
        })
        