import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useTenant } from '../contexts/TenantContext';
import { apiClient } from '../api/client';
import type { Tenant, AdminCertificateRequest } from '../types';
import { Users, FileCheck, Clock, CheckCircle, XCircle, AlertCircle, RefreshCw } from 'lucide-react';
import { CertificateSettingsCard, CertificateRequestModal } from '../components/certificates';

interface Member {
  id: string;
  user_email: string;
  role: string;
  joined_at: string;
}

export function AdminPage() {
  const { isAdmin, isPlatformAdmin } = useTenant();
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [certificateRequests, setCertificateRequests] = useState<AdminCertificateRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'members' | 'certificates' | 'settings'>('overview');
  const [selectedRequest, setSelectedRequest] = useState<AdminCertificateRequest | null>(null);
  const [certStatusFilter, setCertStatusFilter] = useState<string>('');

  useEffect(() => {
    if (isAdmin) {
      loadAdminData();
    }
  }, [isAdmin]);

  const loadAdminData = async () => {
    try {
      const tenantData = await apiClient.getTenantSettings();
      setTenant(tenantData);
    } catch (error) {
      console.error('Failed to load tenant settings:', error);
    }
    
    try {
      const membersData = await apiClient.getTenantMembers();
      setMembers(membersData || []);
    } catch (error) {
      console.error('Failed to load members:', error);
      setMembers([]);
    }
    
    try {
      const certData = await apiClient.getAdminCertificateRequests();
      setCertificateRequests(certData.results || []);
    } catch (error) {
      console.error('Failed to load certificate requests:', error);
      setCertificateRequests([]);
    }
    
    setLoading(false);
  };

  const [refreshingCerts, setRefreshingCerts] = useState(false);

  const handleCertificateRequestUpdate = async (updated: AdminCertificateRequest) => {
    setCertificateRequests((prev) =>
      prev.map((r) => (r.id === updated.id ? updated : r))
    );
    setSelectedRequest(null);
    await loadCertificateRequests();
  };

  const loadCertificateRequests = async () => {
    setRefreshingCerts(true);
    try {
      const certData = await apiClient.getAdminCertificateRequests();
      setCertificateRequests(certData.results || []);
    } catch (error) {
      console.error('Failed to load certificate requests:', error);
    } finally {
      setRefreshingCerts(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'certificates' && isAdmin) {
      loadCertificateRequests();
    }
  }, [activeTab, isAdmin]);

  const pendingCertCount = certificateRequests.filter((r) => r.status === 'PENDING').length;

  if (!isAdmin) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Access Denied</h2>
        <p className="text-gray-600">You do not have permission to access this page.</p>
        <Link to="/dashboard" className="text-indigo-600 hover:text-indigo-500 mt-4 inline-block">
          Return to Dashboard
        </Link>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-8 bg-gray-200 rounded w-1/4"></div>
        <div className="h-64 bg-gray-200 rounded"></div>
      </div>
    );
  }

  const roleLabels: Record<string, string> = {
    'PLATFORM_ADMIN': 'Platform Admin',
    'TENANT_ADMIN': 'Admin',
    'TENANT_STAFF': 'Staff',
    'SHAREHOLDER': 'Shareholder',
  };

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'members', label: 'Team Members' },
    { id: 'certificates', label: 'Certificates', badge: pendingCertCount > 0 ? pendingCertCount : undefined },
    { id: 'settings', label: 'Settings' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Admin Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage your organization settings and team members.
          </p>
        </div>
        {isPlatformAdmin && (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-800">
            Platform Admin
          </span>
        )}
      </div>

      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${
                activeTab === tab.id
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
              {tab.badge && (
                <span className="inline-flex items-center justify-center px-2 py-0.5 text-xs font-medium bg-yellow-100 text-yellow-800 rounded-full">
                  {tab.badge}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {activeTab === 'overview' && (
        <div className="grid gap-6 md:grid-cols-3">
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h3 className="text-sm font-medium text-gray-500">Organization</h3>
            <p className="mt-2 text-2xl font-semibold text-gray-900">{tenant?.name}</p>
            <p className="mt-1 text-sm text-gray-500">/{tenant?.slug}</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h3 className="text-sm font-medium text-gray-500">Team Members</h3>
            <p className="mt-2 text-2xl font-semibold text-gray-900">{members.length}</p>
            <p className="mt-1 text-sm text-gray-500">Active members</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h3 className="text-sm font-medium text-gray-500">Status</h3>
            <p className="mt-2">
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-medium ${
                tenant?.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
              }`}>
                {tenant?.status || 'Active'}
              </span>
            </p>
            <p className="mt-2 text-sm text-gray-500">Organization status</p>
          </div>
        </div>
      )}

      {activeTab === 'members' && (
        <div className="bg-white rounded-lg shadow-sm border">
          <div className="p-4 border-b flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-900">Team Members</h3>
            <button className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 text-sm">
              Invite Member
            </button>
          </div>
          <div className="divide-y">
            {members.map((member) => (
              <div key={member.id} className="p-4 flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">{member.user_email}</p>
                  <p className="text-sm text-gray-500">
                    Joined {new Date(member.joined_at).toLocaleDateString()}
                  </p>
                </div>
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  member.role === 'TENANT_ADMIN' ? 'bg-indigo-100 text-indigo-800' : 'bg-gray-100 text-gray-800'
                }`}>
                  {roleLabels[member.role] || member.role}
                </span>
              </div>
            ))}
            {members.length === 0 && (
              <div className="p-12 text-center">
                <Users className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No team members yet</h3>
                <p className="mt-1 text-sm text-gray-500">
                  Get started by inviting your first team member.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'certificates' && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow-sm border">
            <div className="p-4 border-b flex items-center justify-between">
              <h3 className="text-lg font-medium text-gray-900">Certificate Requests</h3>
              <div className="flex items-center gap-3">
                <button
                  onClick={loadCertificateRequests}
                  disabled={refreshingCerts}
                  className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg disabled:opacity-50"
                  title="Refresh"
                >
                  <RefreshCw className={`w-4 h-4 ${refreshingCerts ? 'animate-spin' : ''}`} />
                </button>
                <select
                  value={certStatusFilter}
                  onChange={(e) => setCertStatusFilter(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                >
                  <option value="">All Statuses</option>
                  <option value="PENDING">Pending</option>
                  <option value="PROCESSING">Processing</option>
                  <option value="COMPLETED">Completed</option>
                  <option value="REJECTED">Rejected</option>
                </select>
              </div>
            </div>
            <div className="divide-y">
              {certificateRequests
                .filter((r) => !certStatusFilter || r.status === certStatusFilter)
                .map((request) => (
                  <div
                    key={request.id}
                    className="p-4 flex items-center justify-between hover:bg-gray-50 cursor-pointer"
                    onClick={() => setSelectedRequest(request)}
                  >
                    <div className="flex items-center gap-4">
                      <div className={`p-2 rounded-lg ${
                        request.status === 'PENDING' ? 'bg-yellow-100' :
                        request.status === 'PROCESSING' ? 'bg-blue-100' :
                        request.status === 'COMPLETED' ? 'bg-green-100' :
                        'bg-red-100'
                      }`}>
                        {request.status === 'PENDING' && <Clock className="w-5 h-5 text-yellow-600" />}
                        {request.status === 'PROCESSING' && <AlertCircle className="w-5 h-5 text-blue-600" />}
                        {request.status === 'COMPLETED' && <CheckCircle className="w-5 h-5 text-green-600" />}
                        {request.status === 'REJECTED' && <XCircle className="w-5 h-5 text-red-600" />}
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">{request.shareholder?.full_name || 'Unknown Shareholder'}</p>
                        <p className="text-sm text-gray-500">
                          {request.conversion_type === 'DRS_TO_CERT' ? 'DRS to Certificate' : 'Certificate to DRS'} - {request.share_quantity} shares
                        </p>
                        <p className="text-xs text-gray-400">
                          {request.holding?.issuer?.company_name || 'Unknown Issuer'} - {new Date(request.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      request.status === 'PENDING' ? 'bg-yellow-100 text-yellow-800' :
                      request.status === 'PROCESSING' ? 'bg-blue-100 text-blue-800' :
                      request.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {request.status}
                    </span>
                  </div>
                ))}
              {certificateRequests.filter((r) => !certStatusFilter || r.status === certStatusFilter).length === 0 && (
                <div className="p-12 text-center">
                  <FileCheck className="mx-auto h-12 w-12 text-gray-400" />
                  <h3 className="mt-2 text-sm font-medium text-gray-900">No certificate requests</h3>
                  <p className="mt-1 text-sm text-gray-500">
                    {certStatusFilter ? `No ${certStatusFilter.toLowerCase()} requests found.` : 'Certificate requests from shareholders will appear here.'}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {selectedRequest && (
        <CertificateRequestModal
          request={selectedRequest}
          onClose={() => setSelectedRequest(null)}
          onUpdate={handleCertificateRequestUpdate}
        />
      )}

      {activeTab === 'settings' && (
        <div className="grid gap-6 md:grid-cols-2">
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Organization Settings</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Organization Name</label>
                <input
                  type="text"
                  value={tenant?.name || ''}
                  disabled
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm bg-gray-50 text-gray-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">URL Slug</label>
                <input
                  type="text"
                  value={tenant?.slug || ''}
                  disabled
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm bg-gray-50 text-gray-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Primary Email</label>
                <input
                  type="email"
                  value={tenant?.primary_email || ''}
                  disabled
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm bg-gray-50 text-gray-500"
                />
              </div>
            </div>
            <p className="mt-4 text-sm text-gray-500">
              Contact support to update organization settings.
            </p>
          </div>
          
          <CertificateSettingsCard />
        </div>
      )}
    </div>
  );
}
