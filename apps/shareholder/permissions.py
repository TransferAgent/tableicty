from rest_framework import permissions


class IsShareholderOwner(permissions.BasePermission):
    """
    Custom permission to only allow shareholders to access their own data.
    """
    
    def has_permission(self, request, view):
        # User must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user has an associated shareholder record
        return hasattr(request.user, 'shareholder')
    
    def has_object_permission(self, request, view, obj):
        # Check if the object belongs to the current user's shareholder
        if hasattr(obj, 'shareholder'):
            return obj.shareholder == request.user.shareholder
        
        # If object is a Shareholder model instance
        from apps.core.models import Shareholder
        if isinstance(obj, Shareholder):
            return obj == request.user.shareholder
        
        return False
