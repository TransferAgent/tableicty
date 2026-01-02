import { useState, useEffect } from 'react';
import { apiClient } from '../../api/client';
import { Mail, Plus, X, Save, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';

interface CertificateSettingsCardProps {
  className?: string;
}

export function CertificateSettingsCard({ className = '' }: CertificateSettingsCardProps) {
  const [emails, setEmails] = useState<string[]>([]);
  const [newEmail, setNewEmail] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const settings = await apiClient.getCertificateSettings();
      setEmails(settings.certificate_notification_emails || []);
      setError(null);
    } catch (err: any) {
      console.error('Failed to load certificate settings:', err);
      setError('Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const handleAddEmail = () => {
    const email = newEmail.trim().toLowerCase();
    if (!email) return;

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      toast.error('Please enter a valid email address');
      return;
    }

    if (emails.includes(email)) {
      toast.error('This email is already in the list');
      return;
    }

    setEmails([...emails, email]);
    setNewEmail('');
  };

  const handleRemoveEmail = (emailToRemove: string) => {
    setEmails(emails.filter(e => e !== emailToRemove));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await apiClient.updateCertificateSettings({
        certificate_notification_emails: emails,
      });
      toast.success('Certificate notification settings saved');
    } catch (err: any) {
      const message = err.response?.data?.error || 'Failed to save settings';
      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddEmail();
    }
  };

  if (loading) {
    return (
      <div className={`bg-white rounded-lg shadow-sm border p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="h-4 bg-gray-200 rounded w-2/3 mb-4"></div>
          <div className="h-10 bg-gray-200 rounded mb-2"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-white rounded-lg shadow-sm border p-6 ${className}`}>
        <div className="flex items-center gap-2 text-red-600">
          <AlertCircle className="w-5 h-5" />
          <span>{error}</span>
        </div>
        <button
          onClick={loadSettings}
          className="mt-2 text-sm text-indigo-600 hover:text-indigo-500"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg shadow-sm border p-6 ${className}`}>
      <div className="flex items-center gap-2 mb-4">
        <Mail className="w-5 h-5 text-indigo-600" />
        <h3 className="text-lg font-medium text-gray-900">Certificate Notifications</h3>
      </div>
      
      <p className="text-sm text-gray-600 mb-4">
        Receive email alerts when shareholders submit certificate conversion requests.
      </p>

      <div className="space-y-3">
        <div className="flex gap-2">
          <input
            type="email"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Enter email address"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
          />
          <button
            onClick={handleAddEmail}
            disabled={!newEmail.trim()}
            className="px-3 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        {emails.length > 0 ? (
          <div className="space-y-2">
            {emails.map((email) => (
              <div
                key={email}
                className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-md"
              >
                <span className="text-sm text-gray-700">{email}</span>
                <button
                  onClick={() => handleRemoveEmail(email)}
                  className="text-gray-400 hover:text-red-500"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500 italic">
            No notification emails configured. Add emails to receive alerts.
          </p>
        )}

        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full mt-4 flex items-center justify-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
}
