import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { apiClient } from '../../api/client';
import type { SubscriptionPlan, TenantRegistrationData } from '../../types';

interface Step {
  id: number;
  name: string;
  status: 'complete' | 'current' | 'upcoming';
}

export function TenantOnboarding() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  
  const [formData, setFormData] = useState<TenantRegistrationData>({
    tenant_name: '',
    tenant_slug: '',
    admin_email: '',
    admin_password: '',
    admin_first_name: '',
    admin_last_name: '',
    plan_tier: 'STARTER',
  });
  const [passwordConfirm, setPasswordConfirm] = useState('');

  const steps: Step[] = [
    { id: 1, name: 'Company Info', status: currentStep === 1 ? 'current' : currentStep > 1 ? 'complete' : 'upcoming' },
    { id: 2, name: 'Admin Account', status: currentStep === 2 ? 'current' : currentStep > 2 ? 'complete' : 'upcoming' },
    { id: 3, name: 'Select Plan', status: currentStep === 3 ? 'current' : currentStep > 3 ? 'complete' : 'upcoming' },
  ];

  useEffect(() => {
    loadPlans();
  }, []);

  const loadPlans = async () => {
    try {
      const planList = await apiClient.getSubscriptionPlans();
      setPlans(planList);
    } catch (error) {
      console.error('Failed to load plans:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateSlug = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '');
  };

  const handleNameChange = (name: string) => {
    setFormData({
      ...formData,
      tenant_name: name,
      tenant_slug: generateSlug(name),
    });
  };

  const validateStep = (step: number): boolean => {
    switch (step) {
      case 1:
        if (!formData.tenant_name.trim()) {
          toast.error('Company name is required');
          return false;
        }
        if (!formData.tenant_slug.trim() || formData.tenant_slug.length < 3) {
          toast.error('Company slug must be at least 3 characters');
          return false;
        }
        return true;
      case 2:
        if (!formData.admin_email.trim() || !formData.admin_email.includes('@')) {
          toast.error('Valid email is required');
          return false;
        }
        if (!formData.admin_password || formData.admin_password.length < 8) {
          toast.error('Password must be at least 8 characters');
          return false;
        }
        if (formData.admin_password !== passwordConfirm) {
          toast.error('Passwords do not match');
          return false;
        }
        if (!formData.admin_first_name.trim() || !formData.admin_last_name.trim()) {
          toast.error('First and last name are required');
          return false;
        }
        return true;
      case 3:
        return !!formData.plan_tier;
      default:
        return true;
    }
  };

  const handleNext = () => {
    if (validateStep(currentStep)) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    setCurrentStep(currentStep - 1);
  };

  const handleSubmit = async () => {
    if (!validateStep(currentStep)) return;

    setSubmitting(true);
    try {
      await apiClient.registerTenant(formData);
      toast.success('Account created successfully!');
      navigate('/dashboard');
    } catch (error: any) {
      const message = error.response?.data?.error || 'Registration failed. Please try again.';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Create Your Account</h1>
          <p className="mt-2 text-gray-600">Get started with tableicty in a few simple steps</p>
        </div>

        <nav aria-label="Progress" className="mb-8">
          <ol className="flex items-center justify-center">
            {steps.map((step, stepIdx) => (
              <li key={step.name} className={stepIdx !== steps.length - 1 ? 'pr-8 sm:pr-20' : ''}>
                <div className="flex items-center">
                  <div
                    className={`flex h-10 w-10 items-center justify-center rounded-full ${
                      step.status === 'complete'
                        ? 'bg-indigo-600'
                        : step.status === 'current'
                        ? 'border-2 border-indigo-600 bg-white'
                        : 'border-2 border-gray-300 bg-white'
                    }`}
                  >
                    {step.status === 'complete' ? (
                      <svg className="h-6 w-6 text-white" viewBox="0 0 24 24" fill="currentColor">
                        <path fillRule="evenodd" d="M19.916 4.626a.75.75 0 01.208 1.04l-9 13.5a.75.75 0 01-1.154.114l-6-6a.75.75 0 011.06-1.06l5.353 5.353 8.493-12.739a.75.75 0 011.04-.208z" clipRule="evenodd" />
                      </svg>
                    ) : (
                      <span className={step.status === 'current' ? 'text-indigo-600' : 'text-gray-500'}>
                        {step.id}
                      </span>
                    )}
                  </div>
                  {stepIdx !== steps.length - 1 && (
                    <div className={`hidden sm:block ml-4 w-20 h-0.5 ${step.status === 'complete' ? 'bg-indigo-600' : 'bg-gray-300'}`} />
                  )}
                </div>
                <div className="mt-2">
                  <span className={`text-sm font-medium ${step.status === 'current' ? 'text-indigo-600' : 'text-gray-500'}`}>
                    {step.name}
                  </span>
                </div>
              </li>
            ))}
          </ol>
        </nav>

        <div className="bg-white rounded-lg shadow-sm border p-8">
          {currentStep === 1 && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-gray-900">Company Information</h2>
              <div>
                <label htmlFor="tenant-name" className="block text-sm font-medium text-gray-700">
                  Company Name
                </label>
                <input
                  type="text"
                  id="tenant-name"
                  value={formData.tenant_name}
                  onChange={(e) => handleNameChange(e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Acme Corporation"
                />
              </div>
              <div>
                <label htmlFor="tenant-slug" className="block text-sm font-medium text-gray-700">
                  Company URL Slug
                </label>
                <div className="mt-1 flex rounded-md shadow-sm">
                  <span className="inline-flex items-center px-3 rounded-l-md border border-r-0 border-gray-300 bg-gray-50 text-gray-500 text-sm">
                    tableicty.com/
                  </span>
                  <input
                    type="text"
                    id="tenant-slug"
                    value={formData.tenant_slug}
                    onChange={(e) => setFormData({ ...formData, tenant_slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '') })}
                    className="flex-1 block w-full px-3 py-2 border border-gray-300 rounded-none rounded-r-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="acme-corp"
                  />
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  This will be used in your unique URL. Only lowercase letters, numbers, and hyphens.
                </p>
              </div>
            </div>
          )}

          {currentStep === 2 && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-gray-900">Administrator Account</h2>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="first-name" className="block text-sm font-medium text-gray-700">
                    First Name
                  </label>
                  <input
                    type="text"
                    id="first-name"
                    value={formData.admin_first_name}
                    onChange={(e) => setFormData({ ...formData, admin_first_name: e.target.value })}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label htmlFor="last-name" className="block text-sm font-medium text-gray-700">
                    Last Name
                  </label>
                  <input
                    type="text"
                    id="last-name"
                    value={formData.admin_last_name}
                    onChange={(e) => setFormData({ ...formData, admin_last_name: e.target.value })}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
              </div>
              <div>
                <label htmlFor="admin-email" className="block text-sm font-medium text-gray-700">
                  Email Address
                </label>
                <input
                  type="email"
                  id="admin-email"
                  value={formData.admin_email}
                  onChange={(e) => setFormData({ ...formData, admin_email: e.target.value })}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
              <div>
                <label htmlFor="admin-password" className="block text-sm font-medium text-gray-700">
                  Password
                </label>
                <input
                  type="password"
                  id="admin-password"
                  value={formData.admin_password}
                  onChange={(e) => setFormData({ ...formData, admin_password: e.target.value })}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                />
                <p className="mt-1 text-xs text-gray-500">Minimum 8 characters</p>
              </div>
              <div>
                <label htmlFor="password-confirm" className="block text-sm font-medium text-gray-700">
                  Confirm Password
                </label>
                <input
                  type="password"
                  id="password-confirm"
                  value={passwordConfirm}
                  onChange={(e) => setPasswordConfirm(e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
            </div>
          )}

          {currentStep === 3 && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-gray-900">Select Your Plan</h2>
              <p className="text-sm text-gray-600">Start with a 14-day free trial. No credit card required.</p>
              
              <div className="grid gap-4">
                {plans.map((plan) => (
                  <label
                    key={plan.id}
                    className={`relative flex cursor-pointer rounded-lg border p-4 shadow-sm focus:outline-none ${
                      formData.plan_tier === plan.tier
                        ? 'border-indigo-600 ring-2 ring-indigo-600'
                        : 'border-gray-300'
                    }`}
                  >
                    <input
                      type="radio"
                      name="plan"
                      value={plan.tier}
                      checked={formData.plan_tier === plan.tier}
                      onChange={() => setFormData({ ...formData, plan_tier: plan.tier })}
                      className="sr-only"
                    />
                    <div className="flex flex-1 justify-between">
                      <div>
                        <span className="block text-lg font-semibold text-gray-900">
                          {plan.name}
                        </span>
                        <span className="mt-1 flex items-center text-sm text-gray-500">
                          Up to {plan.max_shareholders.toLocaleString()} shareholders, {plan.max_users} users
                        </span>
                      </div>
                      <div className="text-right">
                        <span className="text-2xl font-bold text-gray-900">
                          ${parseFloat(plan.price_monthly).toFixed(0)}
                        </span>
                        <span className="text-gray-500">/mo</span>
                      </div>
                    </div>
                    {formData.plan_tier === plan.tier && (
                      <div className="absolute -inset-px rounded-lg border-2 border-indigo-600 pointer-events-none" />
                    )}
                  </label>
                ))}
              </div>
            </div>
          )}

          <div className="mt-8 flex justify-between">
            {currentStep > 1 ? (
              <button
                type="button"
                onClick={handleBack}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
              >
                Back
              </button>
            ) : (
              <div />
            )}
            
            {currentStep < 3 ? (
              <button
                type="button"
                onClick={handleNext}
                className="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
              >
                Continue
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSubmit}
                disabled={submitting}
                className="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
              >
                {submitting ? 'Creating Account...' : 'Start Free Trial'}
              </button>
            )}
          </div>
        </div>

        <p className="mt-4 text-center text-sm text-gray-500">
          Already have an account?{' '}
          <a href="/login" className="text-indigo-600 hover:text-indigo-500">
            Sign in
          </a>
        </p>
      </div>
    </div>
  );
}
