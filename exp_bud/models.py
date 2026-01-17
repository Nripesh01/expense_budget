from django.db import models
from decimal import Decimal  # exact decimal numbers, best for money.
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.conf import settings
# setting is used instead of User model so Django can work with either default User model or custom User model 
#  without breaking your code.
    #      - "auth.User" (default)
    #      - "accounts.User" (custom)

class Group(models.Model):
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='groups_created')
    # AUTH_USER_MODEL tells Django which User model your project uses for authentication.
    # This ensures:
        # - Works today with default User
        # - Works tomorrow with custom User
        # - No database breaks
    # By default, Django uses:
         # -'auth.User' --> Django’s built-in User model
    
    currency = models.CharField(max_length=10, default='NPR')
    created_at = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through='Member', related_name='expense_groups')
    # through='Member':
    # Instead of Django auto-creating a hidden join table, you explicitly created your own join table model: Member.
    
    def __str__(self):
        return f"{self.name}"
    

class Member(models.Model):
    class Role(models.TextChoices):
        CREATOR = 'creator', 'Creator'
        MEMBER = 'member', 'Member'
        
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='member_links')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        constraints = [models.UniqueConstraint(fields=['group', 'user'], name='uniq_member_group_user')] # same user can't join same group twice
        
    def __str__(self):
        return f"{self.user.username} ({self.group.name})"
    
    

class Category(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=60)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        constraints = [models.UniqueConstraint(fields=['group', 'name'], name='uniq_category_group_name')]
    
    def __str__(self):
        return f"{self.name} ({self.group.name})"


class Expense(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='expenses')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='expenses')
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    # DecimalField --> Best for currency
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='expenses_paid')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='expenses_created')
    
    # Real-world: when the expense happened vs when it was created
    spent_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'{self.group.name}: {self.amount} by  {self.paid_by.username}'


class ExpenseSplit(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='splits')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='expense_splits')
    share = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    
    class Meta:
        constraints = [models.UniqueConstraint(fields=['expense', 'user'], name='uniq_split_expense_user')]
    
    def __str__(self):
        return f'{self.user.username} owes {self.share} for expense {self.expense_id}'
    

class BudgetPeriod(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='budgets')
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()
    limit = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='budget_created')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        constraints = [models.UniqueConstraint(fields=['group', 'year', 'month'], name='uniq_budget_group_period')]
        
    def __str__(self):
        return f'{self.group.name} budget {self.year}-{self.month} : {self.limit}'


class Settlement(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='settlements')
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='settlements_sent')
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='settlements_received')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    note = models.TextField(blank=True)
    settled_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f'{self.from_user.username} to {self.to_user.username}: {self.amount}'
    
    