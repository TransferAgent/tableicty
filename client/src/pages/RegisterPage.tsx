import { useState, useEffect } from 'react';
import { useNavigate, Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../api/client';
import { Loader2, Gift, CheckCircle } from 'lucide-react';

interface InvitationInfo {
  email: string;
  companyName: string;
  shareCount: number;
  shareClass: string;
}

export function RegisterPage() {
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [inviteToken, setInviteToken] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [validatingToken, setValidatingToken] = useState(false);
  const [invitationInfo, setInvitationInfo] = useState<InvitationInfo | null>(null);
  const [tokenValidated, setTokenValidated] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const tokenFromUrl = searchParams.get('token');
    if (tokenFromUrl) {
      setInviteToken(tokenFromUrl);
      validateToken(tokenFromUrl);
    }
  }, [searchParams]);

  const validateToken = async (token: string) => {
    setValidatingToken(true);
    setError('');
    
    try {
      const result = await apiClient.validateInviteToken(token);
      
      if (result.valid && result.email) {
        setEmail(result.email);
        setInvitationInfo({
          email: result.email,
          companyName: result.company_name || 'Company',
          shareCount: result.share_count || 0,
          shareClass: result.share_class || '',
        });
        setTokenValidated(true);
      } else {
        setError(result.error || 'Invalid or expired invitation token');
        setTokenValidated(false);
      }
    } catch (err: any) {
      setError(
        err.response?.data?.error || 
        err.response?.data?.detail || 
        'Failed to validate invitation token'
      );
      setTokenValidated(false);
    } finally {
      setValidatingToken(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== passwordConfirm) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setLoading(true);

    try {
      await register({
        email,
        password,
        password_confirm: passwordConfirm,
        invite_token: inviteToken,
      });
      navigate('/dashboard');
    } catch (err: any) {
      setError(
        err.response?.data?.email?.[0] ||
          err.response?.data?.detail ||
          err.response?.data?.error ||
          'Registration failed. Please check your information and try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 bg-white p-10 rounded-xl shadow-lg">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Create your account
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Join the Shareholder Portal
          </p>
        </div>

        {validatingToken && (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="h-6 w-6 animate-spin text-indigo-600 mr-2" />
            <span className="text-gray-600">Validating invitation...</span>
          </div>
        )}

        {invitationInfo && tokenValidated && (
          <div className="rounded-lg bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-200 p-4">
            <div className="flex items-start">
              <Gift className="h-6 w-6 text-purple-600 mt-0.5 mr-3 flex-shrink-0" />
              <div>
                <h3 className="text-sm font-semibold text-purple-900">
                  You've been invited!
                </h3>
                <p className="mt-1 text-sm text-purple-700">
                  Welcome to <strong>{invitationInfo.companyName}</strong>
                </p>
                {invitationInfo.shareCount > 0 && (
                  <p className="mt-1 text-sm text-purple-600">
                    You have <strong>{invitationInfo.shareCount.toLocaleString()}</strong> {invitationInfo.shareClass} shares
                  </p>
                )}
                <div className="mt-2 flex items-center text-xs text-green-600">
                  <CheckCircle className="h-4 w-4 mr-1" />
                  Invitation verified
                </div>
              </div>
            </div>
          </div>
        )}

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}
          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                readOnly={tokenValidated}
                className={`mt-1 appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm ${
                  tokenValidated ? 'bg-gray-100 cursor-not-allowed' : ''
                }`}
                placeholder="you@example.com"
                value={email}
                onChange={(e) => !tokenValidated && setEmail(e.target.value)}
              />
              {tokenValidated && (
                <p className="mt-1 text-xs text-gray-500">
                  Email is locked to match your invitation
                </p>
              )}
            </div>

            {!searchParams.get('token') && (
              <div>
                <label htmlFor="invite-token" className="block text-sm font-medium text-gray-700">
                  Invite Token
                </label>
                <input
                  id="invite-token"
                  name="invite-token"
                  type="text"
                  required
                  className="mt-1 appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  placeholder="Paste your invitation token"
                  value={inviteToken}
                  onChange={(e) => setInviteToken(e.target.value)}
                  onBlur={() => inviteToken && !tokenValidated && validateToken(inviteToken)}
                />
                <p className="mt-1 text-xs text-gray-500">
                  Enter the token from your invitation email
                </p>
              </div>
            )}

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                required
                className="mt-1 appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <p className="mt-1 text-xs text-gray-500">
                Must be at least 8 characters
              </p>
            </div>
            <div>
              <label htmlFor="password-confirm" className="block text-sm font-medium text-gray-700">
                Confirm Password
              </label>
              <input
                id="password-confirm"
                name="password-confirm"
                type="password"
                autoComplete="new-password"
                required
                className="mt-1 appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                placeholder="••••••••"
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={loading || validatingToken}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Creating account...
                </>
              ) : (
                'Create account'
              )}
            </button>
          </div>

          <div className="text-sm text-center space-y-2">
            <p>
              <Link to="/login" className="font-medium text-indigo-600 hover:text-indigo-500">
                Already have an account? Sign in
              </Link>
            </p>
            <p className="text-gray-500">
              Want to create a new company account?{' '}
              <Link to="/onboarding" className="font-medium text-indigo-600 hover:text-indigo-500">
                Get started here
              </Link>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}
