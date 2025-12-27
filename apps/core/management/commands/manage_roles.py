"""
Management command to manage user roles in tenants.

Usage:
    # Promote a user to TENANT_ADMIN
    python manage.py manage_roles promote user@example.com --tenant "Tenant Name"
    
    # Create a new admin user for a tenant
    python manage.py manage_roles create-admin newadmin@example.com --tenant "Tenant Name" --password "SecurePass123!"
    
    # List all users and their roles
    python manage.py manage_roles list
    
    # List users in a specific tenant
    python manage.py manage_roles list --tenant "Tenant Name"
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from apps.core.models import Tenant, TenantMembership

User = get_user_model()


class Command(BaseCommand):
    help = 'Manage user roles in tenants'

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='action', help='Action to perform')
        
        # Promote command
        promote_parser = subparsers.add_parser('promote', help='Promote user to TENANT_ADMIN')
        promote_parser.add_argument('email', type=str, help='Email of user to promote')
        promote_parser.add_argument('--tenant', type=str, help='Tenant name (optional if user has only one tenant)')
        promote_parser.add_argument('--role', type=str, default='TENANT_ADMIN', 
                                   choices=['TENANT_ADMIN', 'TENANT_STAFF', 'SHAREHOLDER', 'PLATFORM_ADMIN'],
                                   help='Role to assign (default: TENANT_ADMIN)')
        
        # Create admin command
        create_parser = subparsers.add_parser('create-admin', help='Create new admin user for a tenant')
        create_parser.add_argument('email', type=str, help='Email for new admin user')
        create_parser.add_argument('--tenant', type=str, required=True, help='Tenant name')
        create_parser.add_argument('--password', type=str, required=True, help='Password for new user')
        create_parser.add_argument('--first-name', type=str, default='', help='First name')
        create_parser.add_argument('--last-name', type=str, default='', help='Last name')
        
        # List command
        list_parser = subparsers.add_parser('list', help='List users and their roles')
        list_parser.add_argument('--tenant', type=str, help='Filter by tenant name')

    def handle(self, *args, **options):
        action = options.get('action')
        
        if action == 'promote':
            self.handle_promote(options)
        elif action == 'create-admin':
            self.handle_create_admin(options)
        elif action == 'list':
            self.handle_list(options)
        else:
            self.stdout.write(self.style.ERROR('Please specify an action: promote, create-admin, or list'))

    def handle_promote(self, options):
        email = options['email']
        role = options['role']
        tenant_name = options.get('tenant')
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise CommandError(f'User with email "{email}" not found')
        
        memberships = TenantMembership.objects.filter(user=user)
        
        if not memberships.exists():
            raise CommandError(f'User "{email}" has no tenant memberships')
        
        if tenant_name:
            try:
                tenant = Tenant.objects.get(name__icontains=tenant_name)
                membership = memberships.filter(tenant=tenant).first()
                if not membership:
                    raise CommandError(f'User "{email}" is not a member of tenant "{tenant_name}"')
            except Tenant.DoesNotExist:
                raise CommandError(f'Tenant "{tenant_name}" not found')
        elif memberships.count() == 1:
            membership = memberships.first()
            tenant = membership.tenant
        else:
            tenants = [m.tenant.name for m in memberships]
            raise CommandError(f'User has multiple tenants. Please specify --tenant. Options: {tenants}')
        
        old_role = membership.role
        membership.role = role
        membership.save()
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully changed role for "{email}" in "{tenant.name}": {old_role} -> {role}'
        ))

    def handle_create_admin(self, options):
        email = options['email']
        password = options['password']
        tenant_name = options['tenant']
        first_name = options.get('first_name', '')
        last_name = options.get('last_name', '')
        
        if User.objects.filter(email=email).exists():
            raise CommandError(f'User with email "{email}" already exists')
        
        try:
            tenant = Tenant.objects.get(name__icontains=tenant_name)
        except Tenant.DoesNotExist:
            available = list(Tenant.objects.values_list('name', flat=True))
            raise CommandError(f'Tenant "{tenant_name}" not found. Available: {available}')
        except Tenant.MultipleObjectsReturned:
            matches = list(Tenant.objects.filter(name__icontains=tenant_name).values_list('name', flat=True))
            raise CommandError(f'Multiple tenants match "{tenant_name}". Please be more specific: {matches}')
        
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        TenantMembership.objects.create(
            tenant=tenant,
            user=user,
            role='TENANT_ADMIN',
            is_primary_contact=False
        )
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully created admin user "{email}" for tenant "{tenant.name}"'
        ))

    def handle_list(self, options):
        tenant_name = options.get('tenant')
        
        if tenant_name:
            try:
                tenant = Tenant.objects.get(name__icontains=tenant_name)
                memberships = TenantMembership.objects.filter(tenant=tenant).select_related('user', 'tenant')
            except Tenant.DoesNotExist:
                raise CommandError(f'Tenant "{tenant_name}" not found')
        else:
            memberships = TenantMembership.objects.all().select_related('user', 'tenant')
        
        if not memberships.exists():
            self.stdout.write('No memberships found.')
            return
        
        self.stdout.write(self.style.SUCCESS('\n=== User Roles ===\n'))
        
        current_tenant = None
        for m in memberships.order_by('tenant__name', '-role', 'user__email'):
            if current_tenant != m.tenant.name:
                current_tenant = m.tenant.name
                self.stdout.write(self.style.MIGRATE_HEADING(f'\n{current_tenant}'))
            
            role_style = self.style.SUCCESS if 'ADMIN' in m.role else self.style.WARNING
            self.stdout.write(f'  {m.user.email or "(no email)"}: {role_style(m.role)}')
        
        self.stdout.write('')
