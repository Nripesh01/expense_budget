from django.db import models
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
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name}"
    

class GroupMember(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    join_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['group', 'user']  # same user can't join same group twice
        
    def __str__(self):
        return f"{self.user.username}"
    