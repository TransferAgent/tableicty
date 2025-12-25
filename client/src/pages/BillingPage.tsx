import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { useTenant } from '../contexts/TenantContext';
import toast from 'react-hot-toast';
import type { BillingStatus, SubscriptionPlan } from '../types';

const formatLimit = (value: number): string => {
  return value === -1 ? 'Unlimited' : value.toLocaleString();
};

export default function BillingPage() {
  const { isAdmin } = useTenant();
  const [billingStatus, setBillingStatus] = useState<BillingStatus | null>(null);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('monthly');
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    loadBillingData();
  }, []);

  const loadBillingData = async () => {
    try {
      setLoading(true);
      const [statusData, plansData] = await Promise.all([
        apiClient.getBillingStatus(),
        apiClient.getSubscriptionPlans(),
      ]);
      setBillingStatus(statusData);
      setPlans(plansData);
    } catch (error) {
      console.error('Failed to load billing data:', error);
      toast.error('Failed to load billing information');
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (planId: string) => {
    if (!isAdmin) {
      toast.error('Only admins can manage billing');
      return;
    }

    try {
      setProcessing(true);
      const { url } = await apiClient.createCheckoutSession(planId, billingCycle);
      window.location.href = url;
    } catch (error) {
      console.error('Failed to create checkout session:', error);
      toast.error('Failed to start checkout. Please try again.');
    } finally {
      setProcessing(false);
    }
  };

  const handleManageBilling = async () => {
    if (!isAdmin) {
      toast.error('Only admins can manage billing');
      return;
    }

    try {
      setProcessing(true);
      const { url } = await apiClient.createBillingPortalSession();
      window.location.href = url;
    } catch (error) {
      console.error('Failed to open billing portal:', error);
      toast.error('Failed to open billing portal. Please try again.');
    } finally {
      setProcessing(false);
    }
  };

  const handleCancelSubscription = async () => {
    if (!isAdmin) {
      toast.error('Only admins can manage billing');
      return;
    }

    if (!confirm('Are you sure you want to cancel your subscription? You will lose access at the end of your billing period.')) {
      return;
    }

    try {
      setProcessing(true);
      await apiClient.cancelSubscription(true);
      toast.success('Subscription will be canceled at the end of your billing period');
      loadBillingData();
    } catch (error) {
      console.error('Failed to cancel subscription:', error);
      toast.error('Failed to cancel subscription. Please try again.');
    } finally {
      setProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  const subscription = billingStatus?.subscription;
  const currentPlan = subscription?.plan;

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Billing & Subscription</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage your subscription and billing settings
        </p>
      </div>

      {!billingStatus?.stripe_configured && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex">
            <svg className="h-5 w-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800">
                Stripe Not Configured
              </h3>
              <p className="mt-1 text-sm text-yellow-700">
                Payment processing is not yet available. Contact support to enable billing.
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Current Subscription</h2>
        </div>
        <div className="px-6 py-5">
          {subscription ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-500">Plan</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {currentPlan?.name || 'Unknown Plan'}
                  </p>
                </div>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  subscription.status === 'ACTIVE' ? 'bg-green-100 text-green-800' :
                  subscription.status === 'TRIALING' ? 'bg-blue-100 text-blue-800' :
                  subscription.status === 'PAST_DUE' ? 'bg-red-100 text-red-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {subscription.status}
                </span>
              </div>

              {currentPlan && (
                <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-200">
                  <div>
                    <p className="text-sm text-gray-500">Max Shareholders</p>
                    <p className="text-lg font-medium">{formatLimit(currentPlan.max_shareholders)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Max Transfers/Month</p>
                    <p className="text-lg font-medium">{formatLimit(currentPlan.max_transfers_per_month)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Max Users</p>
                    <p className="text-lg font-medium">{formatLimit(currentPlan.max_users)}</p>
                  </div>
                </div>
              )}

              {subscription.trial_end && (
                <div className="pt-4 border-t border-gray-200">
                  <p className="text-sm text-gray-500">Trial ends</p>
                  <p className="text-lg font-medium">
                    {new Date(subscription.trial_end).toLocaleDateString()}
                  </p>
                </div>
              )}

              {subscription.current_period_end && (
                <div className="pt-4 border-t border-gray-200">
                  <p className="text-sm text-gray-500">Next billing date</p>
                  <p className="text-lg font-medium">
                    {new Date(subscription.current_period_end).toLocaleDateString()}
                  </p>
                </div>
              )}

              {billingStatus?.stripe_configured && isAdmin && (
                <div className="pt-4 border-t border-gray-200 flex gap-4">
                  <button
                    onClick={handleManageBilling}
                    disabled={processing}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {processing ? 'Loading...' : 'Manage Payment Method'}
                  </button>
                  {subscription.status !== 'CANCELED' && (
                    <button
                      onClick={handleCancelSubscription}
                      disabled={processing}
                      className="px-4 py-2 border border-red-300 text-red-700 rounded-md hover:bg-red-50 disabled:opacity-50"
                    >
                      Cancel Subscription
                    </button>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
              </svg>
              <h3 className="mt-2 text-sm font-medium text-gray-900">No active subscription</h3>
              <p className="mt-1 text-sm text-gray-500">
                Choose a plan below to get started
              </p>
            </div>
          )}
        </div>
      </div>

      {billingStatus?.stripe_configured && isAdmin && plans.length > 0 && (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <div className="px-6 py-5 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-medium text-gray-900">Available Plans</h2>
              <div className="flex items-center gap-2">
                <span className={`text-sm ${billingCycle === 'monthly' ? 'text-gray-900 font-medium' : 'text-gray-500'}`}>Monthly</span>
                <button
                  onClick={() => setBillingCycle(billingCycle === 'monthly' ? 'yearly' : 'monthly')}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    billingCycle === 'yearly' ? 'bg-indigo-600' : 'bg-gray-200'
                  }`}
                >
                  <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    billingCycle === 'yearly' ? 'translate-x-6' : 'translate-x-1'
                  }`} />
                </button>
                <span className={`text-sm ${billingCycle === 'yearly' ? 'text-gray-900 font-medium' : 'text-gray-500'}`}>
                  Yearly <span className="text-green-600">(Save 20%)</span>
                </span>
              </div>
            </div>
          </div>
          <div className="px-6 py-5">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {plans.map((plan) => {
                const isCurrentPlan = currentPlan?.id === plan.id;
                const price = billingCycle === 'yearly' ? plan.price_yearly : plan.price_monthly;
                const period = billingCycle === 'yearly' ? '/year' : '/month';
                
                return (
                  <div
                    key={plan.id}
                    className={`border rounded-lg p-6 ${
                      isCurrentPlan ? 'border-indigo-500 ring-2 ring-indigo-500' : 'border-gray-200'
                    }`}
                  >
                    <div className="text-center">
                      <h3 className="text-lg font-semibold text-gray-900">{plan.name}</h3>
                      <p className="mt-2">
                        <span className="text-3xl font-bold">${parseFloat(price).toLocaleString()}</span>
                        <span className="text-gray-500">{period}</span>
                      </p>
                    </div>
                    <ul className="mt-6 space-y-3">
                      <li className="flex items-center text-sm text-gray-600">
                        <svg className="h-5 w-5 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                        Up to {formatLimit(plan.max_shareholders)} shareholders
                      </li>
                      <li className="flex items-center text-sm text-gray-600">
                        <svg className="h-5 w-5 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                        {formatLimit(plan.max_transfers_per_month)} transfers/month
                      </li>
                      <li className="flex items-center text-sm text-gray-600">
                        <svg className="h-5 w-5 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                        {formatLimit(plan.max_users)} team members
                      </li>
                    </ul>
                    <button
                      onClick={() => handleUpgrade(plan.id)}
                      disabled={isCurrentPlan || processing}
                      className={`mt-6 w-full py-2 px-4 rounded-md font-medium ${
                        isCurrentPlan
                          ? 'bg-gray-100 text-gray-500 cursor-not-allowed'
                          : 'bg-indigo-600 text-white hover:bg-indigo-700'
                      } disabled:opacity-50`}
                    >
                      {isCurrentPlan ? 'Current Plan' : processing ? 'Loading...' : 'Select Plan'}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
