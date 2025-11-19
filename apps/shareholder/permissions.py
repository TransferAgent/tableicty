from rest_framework import permissions


class IsShareholderOwner(permissions.BasePermission):
    """
    Permission: User must have a linked Shareholder record.
    Returns 403 if user has no shareholder (not 500 error).
    """
    
    def has_permission(self, request, view):
        """Check if user is authenticated and has shareholder"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check for shareholder linkage (handle missing gracefully)
        try:
            shareholder = request.user.shareholder
            if shareholder is None:
                return False
            return True
        except AttributeError:
            # user.shareholder doesn't exist
            return False
    
    def has_object_permission(self, request, view, obj):
        """Check if user owns this specific object"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            shareholder = request.user.shareholder
            if shareholder is None:
                return False
        except AttributeError:
            return False
        
        # For objects with shareholder FK
        if hasattr(obj, 'shareholder'):
            return obj.shareholder == shareholder
        
        # For Shareholder objects themselves
        return obj == shareholder
