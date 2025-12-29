import type { ReactNode } from 'react';
import { Lock, ArrowUpCircle } from 'lucide-react';
import { useTenant } from '../contexts/TenantContext';
import { useNavigate } from 'react-router-dom';

export type FeatureKey =
  | 'email_invitations'
  | 'certificate_management'
  | 'transfer_processing'
  | 'compliance_reports'
  | 'dtcc_integration'
  | 'api_access'
  | 'priority_support';

interface FeatureGateProps {
  feature: FeatureKey;
  children: ReactNode;
  fallback?: ReactNode;
  showUpgradePrompt?: boolean;
  inline?: boolean;
}

const FEATURE_INFO: Record<FeatureKey, { name: string; requiredTier: string }> = {
  email_invitations: { name: 'Email Invitations', requiredTier: 'Professional' },
  certificate_management: { name: 'Certificate Management', requiredTier: 'Enterprise' },
  transfer_processing: { name: 'Transfer Processing', requiredTier: 'Professional' },
  compliance_reports: { name: 'Compliance Reports', requiredTier: 'Professional' },
  dtcc_integration: { name: 'DTCC Integration', requiredTier: 'Enterprise' },
  api_access: { name: 'API Access', requiredTier: 'Enterprise' },
  priority_support: { name: 'Priority Support', requiredTier: 'Enterprise' },
};

export function FeatureGate({
  feature,
  children,
  fallback,
  showUpgradePrompt = true,
  inline = false,
}: FeatureGateProps) {
  const { billingStatus } = useTenant();
  const navigate = useNavigate();

  const hasFeature = billingStatus?.usage?.features?.[feature] ?? false;

  if (hasFeature) {
    return <>{children}</>;
  }

  if (fallback) {
    return <>{fallback}</>;
  }

  if (!showUpgradePrompt) {
    return null;
  }

  const info = FEATURE_INFO[feature];

  if (inline) {
    return (
      <button
        onClick={() => navigate('/billing')}
        className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-purple-700 bg-purple-100 rounded-full hover:bg-purple-200 transition-colors"
        title={`Upgrade to ${info.requiredTier} to unlock ${info.name}`}
      >
        <Lock className="h-3 w-3" />
        <span>{info.requiredTier}</span>
      </button>
    );
  }

  return (
    <div className="p-4 bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-200 rounded-lg text-center">
      <Lock className="h-8 w-8 text-purple-500 mx-auto mb-2" />
      <h3 className="font-semibold text-purple-900">{info.name}</h3>
      <p className="text-sm text-purple-700 mt-1">
        This feature requires the {info.requiredTier} plan
      </p>
      <button
        onClick={() => navigate('/billing')}
        className="mt-3 inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors text-sm font-medium"
      >
        <ArrowUpCircle className="h-4 w-4" />
        Upgrade Now
      </button>
    </div>
  );
}

export function useFeature(feature: FeatureKey): boolean {
  const { billingStatus } = useTenant();
  return billingStatus?.usage?.features?.[feature] ?? false;
}

export function useUsage() {
  const { billingStatus } = useTenant();
  return billingStatus?.usage ?? null;
}
