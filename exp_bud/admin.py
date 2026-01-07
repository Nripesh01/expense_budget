from django.contrib import admin
from .models import Group, Member, Category, Expense, ExpenseSplit, BudgetPeriod, Settlement

admin.site.register(Group)
admin.site.register(Member)
admin.site.register(Category)
admin.site.register(Expense)
admin.site.register(ExpenseSplit)
admin.site.register(BudgetPeriod)
admin.site.register(Settlement)
