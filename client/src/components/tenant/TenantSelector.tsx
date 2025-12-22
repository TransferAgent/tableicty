import { useState, useRef, useEffect } from 'react';
import { useTenant } from '../../contexts/TenantContext';

export function TenantSelector() {
  const { currentTenant, currentRole, availableTenants, switchTenant } = useTenant();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (!currentTenant) {
    return null;
  }

  const roleLabel = {
    'PLATFORM_ADMIN': 'Platform Admin',
    'TENANT_ADMIN': 'Admin',
    'TENANT_STAFF': 'Staff',
    'SHAREHOLDER': 'Shareholder',
  }[currentRole || ''] || currentRole;

  const hasMultipleTenants = availableTenants.length > 1;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => hasMultipleTenants && setIsOpen(!isOpen)}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border ${
          hasMultipleTenants 
            ? 'hover:bg-gray-50 cursor-pointer' 
            : 'cursor-default'
        } ${isOpen ? 'bg-gray-50' : 'bg-white'}`}
      >
        <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center">
          <span className="text-sm font-semibold text-indigo-600">
            {currentTenant.name.charAt(0).toUpperCase()}
          </span>
        </div>
        <div className="text-left">
          <div className="text-sm font-medium text-gray-900 truncate max-w-[120px]">
            {currentTenant.name}
          </div>
          <div className="text-xs text-gray-500">{roleLabel}</div>
        </div>
        {hasMultipleTenants && (
          <svg
            className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        )}
      </button>

      {isOpen && hasMultipleTenants && (
        <div className="absolute left-0 mt-2 w-64 bg-white rounded-lg shadow-lg border py-1 z-50">
          <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
            Switch Organization
          </div>
          {availableTenants.map((membership) => (
            <button
              key={membership.tenant.id}
              onClick={() => {
                switchTenant(membership.tenant.id);
                setIsOpen(false);
              }}
              className={`w-full px-3 py-2 text-left hover:bg-gray-50 flex items-center gap-3 ${
                membership.tenant.id === currentTenant.id ? 'bg-indigo-50' : ''
              }`}
            >
              <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0">
                <span className="text-sm font-semibold text-indigo-600">
                  {membership.tenant.name.charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-900 truncate">
                  {membership.tenant.name}
                </div>
                <div className="text-xs text-gray-500">
                  {membership.role.replace('_', ' ')}
                </div>
              </div>
              {membership.tenant.id === currentTenant.id && (
                <svg className="w-5 h-5 text-indigo-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
