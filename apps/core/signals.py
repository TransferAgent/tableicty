"""
AuditLog Immutability Security System

This module implements a threadlocal flag system to prevent unauthorized
manipulation of audit trails. AuditLog entries can only be created when
this flag is set, preventing direct AuditLog.objects.create() calls.

Usage Pattern (REQUIRED for all AuditLog creation):
    from apps.core.signals import set_audit_signal_flag, clear_audit_signal_flag
    
    set_audit_signal_flag()
    try:
        AuditLog.objects.create(
            user=request.user,
            action_type='CREATE',
            model_name='Transfer',
            # ... other fields
        )
    finally:
        clear_audit_signal_flag()

Security:
- Blocks both updates to existing AuditLog entries AND direct creates
- All AuditLog.objects.create() calls must be wrapped with flag guards
- Prevents audit trail forgery and unauthorized modifications
- Ensures compliance with immutable audit trail requirements

Locations using this pattern:
- apps/core/admin.py (admin actions)
- apps/api/views.py (transfer execution)
- apps/shareholder/views.py (certificate conversion requests)
- apps/shareholder/serializers.py (profile updates)
"""
import threading

# Thread-local storage for signal marker
_audit_signal_context = threading.local()


def set_audit_signal_flag():
    """Mark that we're creating AuditLog from a signal"""
    _audit_signal_context.from_signal = True


def clear_audit_signal_flag():
    """Clear the signal marker"""
    _audit_signal_context.from_signal = False


def is_from_signal():
    """Check if AuditLog creation is from a signal"""
    return getattr(_audit_signal_context, 'from_signal', False)
