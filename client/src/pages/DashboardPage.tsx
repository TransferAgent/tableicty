import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { apiClient } from '../api/client';
import { useTenant } from '../contexts/TenantContext';
import type { Holding, PortfolioSummary } from '../types';
import { formatNumber, formatDate } from '../lib/utils';
import { TrendingUp, Building2, Briefcase, Users, CreditCard, Settings, Shield, Crown, CheckCircle, XCircle } from 'lucide-react';
import { PortfolioCharts } from '../components/charts/PortfolioCharts';

function UsageProgressBar({ current, limit, label }: { current: number; limit: number; label: string }) {
  const unlimited = limit === -1;
  const percentage = unlimited ? 0 : Math.min((current / limit) * 100, 100);
  const isNearLimit = !unlimited && percentage >= 80;
  const isAtLimit = !unlimited && current >= limit;
  
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">{label}</span>
        <span className={`font-medium ${isAtLimit ? 'text-red-600' : isNearLimit ? 'text-yellow-600' : 'text-gray-900'}`}>
          {current.toLocaleString()} / {unlimited ? 'Unlimited' : limit.toLocaleString()}
        </span>
      </div>
      {!unlimited && (
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              isAtLimit ? 'bg-red-500' : isNearLimit ? 'bg-yellow-500' : 'bg-indigo-500'
            }`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      )}
    </div>
  );
}

export function DashboardPage() {
  const { isAdmin, currentTenant, currentRole, billingStatus } = useTenant();
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    // Only load portfolio data for shareholders, not admins
    if (!isAdmin) {
      loadData();
    } else {
      setLoading(false);
    }
  }, [isAdmin]);

  const loadData = async () => {
    try {
      const [holdingsData, summaryData] = await Promise.all([
        apiClient.getHoldings(),
        apiClient.getPortfolioSummary(),
      ]);
      setHoldings(holdingsData.holdings);
      setSummary(summaryData);
    } catch (err: any) {
      const message = err.response?.data?.error || 'Failed to load portfolio data';
      setError(message);
      toast.error(message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading portfolio...</p>
        </div>
      </div>
    );
  }

  if (error && !isAdmin) {
    return (
      <div className="rounded-md bg-red-50 p-4">
        <p className="text-sm text-red-800">{error}</p>
      </div>
    );
  }

  // Admin Dashboard View
  if (isAdmin) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Welcome to {currentTenant?.name || 'Your Organization'}
          </h1>
          <p className="mt-1 text-sm text-gray-600">
            Manage your transfer agent platform from here
          </p>
        </div>

        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Link
              to="/dashboard/admin"
              className="flex items-center p-4 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
            >
              <Settings className="h-8 w-8 text-indigo-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-900">Organization Settings</p>
                <p className="text-xs text-gray-500">Manage your company</p>
              </div>
            </Link>

            <Link
              to="/dashboard/billing"
              className="flex items-center p-4 bg-green-50 rounded-lg hover:bg-green-100 transition-colors"
            >
              <CreditCard className="h-8 w-8 text-green-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-900">Billing & Subscription</p>
                <p className="text-xs text-gray-500">Manage your plan</p>
              </div>
            </Link>

            <Link
              to="/dashboard/security"
              className="flex items-center p-4 bg-purple-50 rounded-lg hover:bg-purple-100 transition-colors"
            >
              <Shield className="h-8 w-8 text-purple-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-900">Security</p>
                <p className="text-xs text-gray-500">MFA & account security</p>
              </div>
            </Link>

            <Link
              to="/dashboard/profile"
              className="flex items-center p-4 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
            >
              <Users className="h-8 w-8 text-blue-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-900">Your Profile</p>
                <p className="text-xs text-gray-500">View your account</p>
              </div>
            </Link>
          </div>
        </div>

        {billingStatus?.usage && (
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Subscription & Usage</h2>
              <div className="flex items-center gap-2">
                <Crown className="h-5 w-5 text-yellow-500" />
                <span className="text-sm font-medium text-gray-900 bg-gradient-to-r from-yellow-100 to-yellow-50 px-3 py-1 rounded-full">
                  {billingStatus.usage.tier_name} Plan
                </span>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <UsageProgressBar
                  label="Shareholders"
                  current={billingStatus.usage.shareholders.current}
                  limit={billingStatus.usage.shareholders.limit}
                />
                <UsageProgressBar
                  label="Admin Users"
                  current={billingStatus.usage.admins.current}
                  limit={billingStatus.usage.admins.limit}
                />
              </div>
              
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-3">Features</h3>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(billingStatus.usage.features).map(([feature, enabled]) => (
                    <div key={feature} className="flex items-center gap-2 text-sm">
                      {enabled ? (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      ) : (
                        <XCircle className="h-4 w-4 text-gray-300" />
                      )}
                      <span className={enabled ? 'text-gray-700' : 'text-gray-400'}>
                        {feature.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            
            {!billingStatus.usage.shareholders.can_add && (
              <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-sm text-yellow-800">
                  You've reached your shareholder limit. 
                  <Link to="/dashboard/billing" className="ml-1 font-medium underline hover:text-yellow-900">
                    Upgrade your plan
                  </Link>
                </p>
              </div>
            )}
          </div>
        )}

        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Getting Started</h2>
          <div className="space-y-4">
            <div className="flex items-start">
              <div className="flex-shrink-0 h-6 w-6 rounded-full bg-indigo-100 flex items-center justify-center">
                <span className="text-xs font-medium text-indigo-600">1</span>
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-900">Set up your organization</p>
                <p className="text-xs text-gray-500">Configure your company details in Admin settings</p>
              </div>
            </div>
            <div className="flex items-start">
              <div className="flex-shrink-0 h-6 w-6 rounded-full bg-indigo-100 flex items-center justify-center">
                <span className="text-xs font-medium text-indigo-600">2</span>
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-900">Choose your subscription plan</p>
                <p className="text-xs text-gray-500">Select the plan that fits your needs in Billing</p>
              </div>
            </div>
            <div className="flex items-start">
              <div className="flex-shrink-0 h-6 w-6 rounded-full bg-indigo-100 flex items-center justify-center">
                <span className="text-xs font-medium text-indigo-600">3</span>
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-900">Enable two-factor authentication</p>
                <p className="text-xs text-gray-500">Secure your account with MFA in Security settings</p>
              </div>
            </div>
          </div>
        </div>

        {currentRole && (
          <div className="text-sm text-gray-500">
            Your role: <span className="font-medium">{currentRole.replace('_', ' ')}</span>
          </div>
        )}
      </div>
    );
  }

  // Shareholder Dashboard View
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Portfolio Overview</h1>
        <p className="mt-1 text-sm text-gray-600">View your shareholdings and portfolio summary</p>
      </div>

      {summary && (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Building2 className="h-6 w-6 text-indigo-600" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Total Companies</dt>
                    <dd className="text-2xl font-semibold text-gray-900">{summary.total_companies}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <TrendingUp className="h-6 w-6 text-green-600" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Total Shares</dt>
                    <dd className="text-2xl font-semibold text-gray-900">{formatNumber(summary.total_shares)}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Briefcase className="h-6 w-6 text-blue-600" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Total Holdings</dt>
                    <dd className="text-2xl font-semibold text-gray-900">{summary.total_holdings}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {holdings.length > 0 && <PortfolioCharts holdings={holdings} />}

      <div className="bg-white shadow overflow-hidden sm:rounded-lg">
        <div className="px-4 py-5 sm:px-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900">Your Holdings</h3>
          <p className="mt-1 max-w-2xl text-sm text-gray-500">Detailed view of all your shareholdings</p>
        </div>
        <div className="border-t border-gray-200">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Company
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Security Type
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Shares
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Ownership %
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Acquired
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {holdings.map((holding) => (
                  <tr key={holding.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{holding.issuer.name}</div>
                      <div className="text-sm text-gray-500">{holding.issuer.ticker || 'N/A'}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{holding.security_class.type}</div>
                      <div className="text-sm text-gray-500">{holding.security_class.designation}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatNumber(parseFloat(holding.share_quantity))}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {holding.percentage_ownership.toFixed(4)}%
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                        {holding.holding_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(holding.acquisition_date)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {holdings.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-500">No holdings found</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
