from rest_framework.permissions import BasePermission
from .models import Group, Member, Expense

class IsGroupMember(BasePermission):
    def has_permission(self, request, view):
        group = getattr(view, 'group', None) # getattrs Python function that safely reads an attribute from an object.
        if group is None:            # getattr is used to avoid AttributeError when the attribute might not be present.
            return True
        return Member.objects.filter(group=group, user=request.user).exists()
               

class IsGroupCreator(BasePermission):
    def has_permission(self, request, view):
        group = getattr(view, 'group', None)
        if group is None:
            return False
        return group.created_by_id == request.user.id


class IsGroupCreatorOrExpenseCreator(BasePermission):
    def has_object_permission(self, request, view, obj):
        # obj is Expense
        if obj.group.created_by_id == request.user.id:
            return True
        return obj.created_by_id == request.user.id
    