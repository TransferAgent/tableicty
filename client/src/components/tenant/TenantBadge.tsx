import { useTenant } from '../../contexts/TenantContext';

interface TenantBadgeProps {
  showRole?: boolean;
  className?: string;
}

export function TenantBadge({ showRole = false, className = '' }: TenantBadgeProps) {
  const { currentTenant, currentRole, loading } = useTenant();

  if (loading) {
    return (
      <div className={`animate-pulse flex items-center gap-2 ${className}`}>
        <div className="w-6 h-6 rounded-full bg-gray-200"></div>
        <div className="h-4 w-20 bg-gray-200 rounded"></div>
      </div>
    );
  }

  if (!currentTenant) {
    return null;
  }

  const roleColors = {
    'PLATFORM_ADMIN': 'bg-purple-100 text-purple-800',
    'TENANT_ADMIN': 'bg-indigo-100 text-indigo-800',
    'TENANT_STAFF': 'bg-blue-100 text-blue-800',
    'SHAREHOLDER': 'bg-gray-100 text-gray-800',
  };

  const roleLabels = {
    'PLATFORM_ADMIN': 'Platform Admin',
    'TENANT_ADMIN': 'Admin',
    'TENANT_STAFF': 'Staff',
    'SHAREHOLDER': 'Shareholder',
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="w-6 h-6 rounded-full bg-indigo-100 flex items-center justify-center">
        <span className="text-xs font-semibold text-indigo-600">
          {currentTenant.name.charAt(0).toUpperCase()}
        </span>
      </div>
      <span className="text-sm font-medium text-gray-700 truncate max-w-[100px]">
        {currentTenant.name}
      </span>
      {showRole && currentRole && (
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${roleColors[currentRole as keyof typeof roleColors] || 'bg-gray-100 text-gray-800'}`}>
          {roleLabels[currentRole as keyof typeof roleLabels] || currentRole}
        </span>
      )}
    </div>
  );
}
