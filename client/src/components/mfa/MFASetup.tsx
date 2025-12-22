import { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { apiClient } from '../../api/client';
import type { MFAStatus, MFASetupResponse } from '../../types';

interface MFASetupProps {
  onComplete?: () => void;
}

export function MFASetup({ onComplete }: MFASetupProps) {
  const [status, setStatus] = useState<MFAStatus | null>(null);
  const [setupData, setSetupData] = useState<MFASetupResponse | null>(null);
  const [verificationCode, setVerificationCode] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [step, setStep] = useState<'status' | 'setup' | 'verify'>('status');

  useEffect(() => {
    loadMFAStatus();
  }, []);

  const loadMFAStatus = async () => {
    try {
      const mfaStatus = await apiClient.getMFAStatus();
      setStatus(mfaStatus);
      if (mfaStatus.mfa_enabled) {
        setStep('status');
      } else if (mfaStatus.mfa_pending_setup) {
        setStep('verify');
      } else {
        setStep('status');
      }
    } catch (error) {
      console.error('Failed to load MFA status:', error);
      toast.error('Failed to load MFA status');
    } finally {
      setLoading(false);
    }
  };

  const handleSetup = async () => {
    setSubmitting(true);
    try {
      const data = await apiClient.setupMFA();
      setSetupData(data);
      setStep('verify');
      toast.success('Scan the QR code with your authenticator app');
    } catch (error: any) {
      const message = error.response?.data?.error || 'Failed to setup MFA';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (verificationCode.length !== 6) {
      toast.error('Please enter a 6-digit code');
      return;
    }

    setSubmitting(true);
    try {
      await apiClient.verifyMFASetup(verificationCode);
      toast.success('MFA enabled successfully!');
      setStatus({ mfa_enabled: true, mfa_pending_setup: false, device_count: 1 });
      setStep('status');
      setSetupData(null);
      setVerificationCode('');
      onComplete?.();
    } catch (error: any) {
      const message = error.response?.data?.error || 'Invalid verification code';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-1/4 mb-4"></div>
        <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
        <div className="h-4 bg-gray-200 rounded w-1/2"></div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border p-6">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">
        Two-Factor Authentication
      </h2>

      {status?.mfa_enabled ? (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
              Enabled
            </span>
            <span className="text-sm text-gray-500">
              Your account is protected with 2FA
            </span>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            Two-factor authentication adds an extra layer of security to your account
            by requiring a code from your authenticator app when you sign in.
          </p>
          <MFADisable onDisabled={loadMFAStatus} />
        </div>
      ) : step === 'verify' && setupData ? (
        <div>
          <p className="text-sm text-gray-600 mb-4">
            Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)
          </p>
          
          {setupData.qr_code_base64 && (
            <div className="flex justify-center mb-6">
              <img 
                src={setupData.qr_code_base64} 
                alt="MFA QR Code" 
                className="w-48 h-48 border rounded"
              />
            </div>
          )}

          <details className="mb-4">
            <summary className="text-sm text-indigo-600 cursor-pointer hover:text-indigo-500">
              Can&apos;t scan? Enter code manually
            </summary>
            <div className="mt-2 p-3 bg-gray-50 rounded text-xs font-mono break-all">
              {setupData.provisioning_uri}
            </div>
          </details>

          <form onSubmit={handleVerify} className="space-y-4">
            <div>
              <label htmlFor="verification-code" className="block text-sm font-medium text-gray-700">
                Enter 6-digit code from your app
              </label>
              <input
                type="text"
                id="verification-code"
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                placeholder="000000"
                maxLength={6}
                autoComplete="one-time-code"
              />
            </div>
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={submitting || verificationCode.length !== 6}
                className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? 'Verifying...' : 'Verify & Enable'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setStep('status');
                  setSetupData(null);
                  setVerificationCode('');
                }}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      ) : (
        <div>
          <p className="text-sm text-gray-600 mb-4">
            Add an extra layer of security to your account by enabling two-factor authentication.
            You&apos;ll need an authenticator app like Google Authenticator or Authy.
          </p>
          <button
            onClick={handleSetup}
            disabled={submitting}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
          >
            {submitting ? 'Setting up...' : 'Enable 2FA'}
          </button>
        </div>
      )}
    </div>
  );
}

function MFADisable({ onDisabled }: { onDisabled: () => void }) {
  const [showForm, setShowForm] = useState(false);
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleDisable = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password || code.length !== 6) {
      toast.error('Please enter your password and 6-digit code');
      return;
    }

    setSubmitting(true);
    try {
      await apiClient.disableMFA(password, code);
      toast.success('MFA disabled successfully');
      setShowForm(false);
      setPassword('');
      setCode('');
      onDisabled();
    } catch (error: any) {
      const message = error.response?.data?.error || 'Failed to disable MFA';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  if (!showForm) {
    return (
      <button
        onClick={() => setShowForm(true)}
        className="px-4 py-2 border border-red-300 text-red-700 rounded-md hover:bg-red-50"
      >
        Disable 2FA
      </button>
    );
  }

  return (
    <form onSubmit={handleDisable} className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg space-y-4">
      <p className="text-sm text-red-700">
        Disabling 2FA will make your account less secure. You&apos;ll need your current password
        and a code from your authenticator app to confirm.
      </p>
      <div>
        <label htmlFor="disable-password" className="block text-sm font-medium text-gray-700">
          Password
        </label>
        <input
          type="password"
          id="disable-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-red-500 focus:border-red-500"
          autoComplete="current-password"
        />
      </div>
      <div>
        <label htmlFor="disable-code" className="block text-sm font-medium text-gray-700">
          Authenticator Code
        </label>
        <input
          type="text"
          id="disable-code"
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-red-500 focus:border-red-500"
          placeholder="000000"
          maxLength={6}
          autoComplete="one-time-code"
        />
      </div>
      <div className="flex gap-3">
        <button
          type="submit"
          disabled={submitting || !password || code.length !== 6}
          className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting ? 'Disabling...' : 'Confirm Disable'}
        </button>
        <button
          type="button"
          onClick={() => {
            setShowForm(false);
            setPassword('');
            setCode('');
          }}
          className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
