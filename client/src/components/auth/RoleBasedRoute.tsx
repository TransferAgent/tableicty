import { Navigate } from 'react-router-dom';
import { useTenant } from '../../contexts/TenantContext';

type Role = 'PLATFORM_ADMIN' | 'TENANT_ADMIN' | 'TENANT_STAFF' | 'SHAREHOLDER';

interface RoleBasedRouteProps {
  children: React.ReactNode;
  allowedRoles: Role[];
  fallback?: string;
}

export function RoleBasedRoute({ children, allowedRoles, fallback = '/dashboard' }: RoleBasedRouteProps) {
  const { currentRole, loading } = useTenant();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!currentRole) {
    return <Navigate to={fallback} replace />;
  }

  const hasAccess = allowedRoles.includes(currentRole as Role);

  if (!hasAccess) {
    return <Navigate to={fallback} replace />;
  }

  return <>{children}</>;
}

export function AdminRoute({ children }: { children: React.ReactNode }) {
  return (
    <RoleBasedRoute allowedRoles={['PLATFORM_ADMIN', 'TENANT_ADMIN']}>
      {children}
    </RoleBasedRoute>
  );
}

export function StaffRoute({ children }: { children: React.ReactNode }) {
  return (
    <RoleBasedRoute allowedRoles={['PLATFORM_ADMIN', 'TENANT_ADMIN', 'TENANT_STAFF']}>
      {children}
    </RoleBasedRoute>
  );
}
