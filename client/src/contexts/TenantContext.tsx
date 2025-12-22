import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { apiClient } from '../api/client';
import type { Tenant, TenantMembership, CurrentTenantResponse } from '../types';
import { useAuth } from './AuthContext';

interface TenantContextType {
  currentTenant: Tenant | null;
  currentRole: string | null;
  availableTenants: TenantMembership[];
  loading: boolean;
  error: string | null;
  refreshTenantContext: () => Promise<void>;
  switchTenant: (tenantId: string) => Promise<void>;
  isAdmin: boolean;
  isStaff: boolean;
  isPlatformAdmin: boolean;
}

const TenantContext = createContext<TenantContextType | undefined>(undefined);

export function TenantProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [currentTenant, setCurrentTenant] = useState<Tenant | null>(null);
  const [currentRole, setCurrentRole] = useState<string | null>(null);
  const [availableTenants, setAvailableTenants] = useState<TenantMembership[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      loadTenantContext();
    } else {
      setCurrentTenant(null);
      setCurrentRole(null);
      setAvailableTenants([]);
      setLoading(false);
    }
  }, [isAuthenticated]);

  const loadTenantContext = async () => {
    try {
      setLoading(true);
      setError(null);
      const response: CurrentTenantResponse = await apiClient.getCurrentTenant();
      setCurrentTenant(response.current_tenant);
      setCurrentRole(response.current_role);
      setAvailableTenants(response.available_tenants || []);
    } catch (err: any) {
      console.error('Failed to load tenant context:', err);
      setError(err.response?.data?.error || 'Failed to load tenant context');
      setCurrentTenant(null);
      setCurrentRole(null);
      setAvailableTenants([]);
    } finally {
      setLoading(false);
    }
  };

  const refreshTenantContext = async () => {
    if (isAuthenticated) {
      await loadTenantContext();
    }
  };

  const switchTenant = async (tenantId: string) => {
    const targetMembership = availableTenants.find(m => m.tenant.id === tenantId);
    if (!targetMembership) {
      console.error('Cannot switch to tenant - not a member');
      return;
    }
    setCurrentTenant(targetMembership.tenant);
    setCurrentRole(targetMembership.role);
  };

  const isAdmin = currentRole === 'PLATFORM_ADMIN' || currentRole === 'TENANT_ADMIN';
  const isStaff = isAdmin || currentRole === 'TENANT_STAFF';
  const isPlatformAdmin = currentRole === 'PLATFORM_ADMIN';

  return (
    <TenantContext.Provider
      value={{
        currentTenant,
        currentRole,
        availableTenants,
        loading,
        error,
        refreshTenantContext,
        switchTenant,
        isAdmin,
        isStaff,
        isPlatformAdmin,
      }}
    >
      {children}
    </TenantContext.Provider>
  );
}

export function useTenant() {
  const context = useContext(TenantContext);
  if (context === undefined) {
    throw new Error('useTenant must be used within a TenantProvider');
  }
  return context;
}
