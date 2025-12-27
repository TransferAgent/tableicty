import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import type { AdminShareholder, AdminSecurityClass, AdminIssuer } from '../types';
import { Users, Plus, Search, Edit, Trash2, DollarSign, X, Building, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';

type ShareholderFormData = {
  account_type: AdminShareholder['account_type'];
  first_name: string;
  middle_name: string;
  last_name: string;
  entity_name: string;
  email: string;
  phone: string;
  tax_id: string;
  tax_id_type: AdminShareholder['tax_id_type'];
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  zip_code: string;
  country: string;
  is_accredited_investor: boolean;
  is_insider: boolean;
  is_affiliate: boolean;
};

type HoldingFormData = {
  shareholder: string;
  issuer: string;
  security_class: string;
  share_quantity: string;
  cost_basis: string;
  acquisition_date: string;
  acquisition_type: string;
  holding_type: string;
  is_restricted: boolean;
  notes: string;
};

type IssuerFormData = {
  company_name: string;
  ticker_symbol: string;
  cusip: string;
  cik: string;
  incorporation_state: string;
  incorporation_country: string;
  total_authorized_shares: string;
  par_value: string;
  agreement_start_date: string;
  annual_fee: string;
  is_active: boolean;
};

const ACCOUNT_TYPES = [
  { value: 'INDIVIDUAL', label: 'Individual' },
  { value: 'JOINT_TENANTS', label: 'Joint Tenants (JTWROS)' },
  { value: 'TENANTS_COMMON', label: 'Tenants in Common' },
  { value: 'ENTITY', label: 'Entity (Corp/LLC/Trust)' },
  { value: 'CUSTODIAN', label: 'Custodian (UTMA/UGMA)' },
  { value: 'IRA', label: 'Individual Retirement Account' },
] as const;
const TAX_ID_TYPES = ['SSN', 'EIN', 'ITIN', 'FOREIGN'] as const;
const ACQUISITION_TYPES = ['PURCHASE', 'GIFT', 'INHERITANCE', 'STOCK_SPLIT', 'DIVIDEND', 'TRANSFER', 'ISSUANCE'] as const;
const HOLDING_TYPES = ['CERTIFICATE', 'DRS', 'BOOK_ENTRY'] as const;

export function ShareholdersPage() {
  const [shareholders, setShareholders] = useState<AdminShareholder[]>([]);
  const [securityClasses, setSecurityClasses] = useState<AdminSecurityClass[]>([]);
  const [issuers, setIssuers] = useState<AdminIssuer[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showHoldingModal, setShowHoldingModal] = useState(false);
  const [showIssuerModal, setShowIssuerModal] = useState(false);
  const [selectedShareholder, setSelectedShareholder] = useState<AdminShareholder | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const initialFormData: ShareholderFormData = {
    account_type: 'INDIVIDUAL',
    first_name: '',
    middle_name: '',
    last_name: '',
    entity_name: '',
    email: '',
    phone: '',
    tax_id: '',
    tax_id_type: 'SSN',
    address_line1: '',
    address_line2: '',
    city: '',
    state: '',
    zip_code: '',
    country: 'USA',
    is_accredited_investor: false,
    is_insider: false,
    is_affiliate: false,
  };

  const initialHoldingData: HoldingFormData = {
    shareholder: '',
    issuer: '',
    security_class: '',
    share_quantity: '',
    cost_basis: '',
    acquisition_date: new Date().toISOString().split('T')[0],
    acquisition_type: 'ISSUANCE',
    holding_type: 'DRS',
    is_restricted: false,
    notes: '',
  };

  const [formData, setFormData] = useState<ShareholderFormData>(initialFormData);
  const [holdingFormData, setHoldingFormData] = useState<HoldingFormData>(initialHoldingData);

  const initialIssuerData: IssuerFormData = {
    company_name: '',
    ticker_symbol: '',
    cusip: '',
    cik: '',
    incorporation_state: 'DE',
    incorporation_country: 'US',
    total_authorized_shares: '100000000',
    par_value: '0.0001',
    agreement_start_date: new Date().toISOString().split('T')[0],
    annual_fee: '5000.00',
    is_active: true,
  };
  const [issuerFormData, setIssuerFormData] = useState<IssuerFormData>(initialIssuerData);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [shareholdersRes, classesRes, issuersRes] = await Promise.all([
        apiClient.getAdminShareholders(),
        apiClient.getAdminSecurityClasses(),
        apiClient.getAdminIssuers(),
      ]);
      setShareholders(shareholdersRes.results || []);
      setSecurityClasses(classesRes.results || []);
      setIssuers(issuersRes.results || []);
    } catch (error) {
      console.error('Error loading data:', error);
      toast.error('Failed to load shareholders');
    } finally {
      setLoading(false);
    }
  };

  const filteredShareholders = shareholders.filter((s) => {
    const searchLower = searchQuery.toLowerCase();
    return (
      s.full_name?.toLowerCase().includes(searchLower) ||
      s.email?.toLowerCase().includes(searchLower) ||
      s.entity_name?.toLowerCase().includes(searchLower)
    );
  });

  const handleAddShareholder = () => {
    setFormData(initialFormData);
    setShowAddModal(true);
  };

  const handleEditShareholder = (shareholder: AdminShareholder) => {
    setSelectedShareholder(shareholder);
    setFormData({
      account_type: shareholder.account_type,
      first_name: shareholder.first_name || '',
      middle_name: shareholder.middle_name || '',
      last_name: shareholder.last_name || '',
      entity_name: shareholder.entity_name || '',
      email: shareholder.email || '',
      phone: shareholder.phone || '',
      tax_id: '',
      tax_id_type: shareholder.tax_id_type,
      address_line1: shareholder.address_line1 || '',
      address_line2: shareholder.address_line2 || '',
      city: shareholder.city || '',
      state: shareholder.state || '',
      zip_code: shareholder.zip_code || '',
      country: shareholder.country || 'USA',
      is_accredited_investor: shareholder.is_accredited_investor,
      is_insider: shareholder.is_insider,
      is_affiliate: shareholder.is_affiliate,
    });
    setShowEditModal(true);
  };

  const handleIssueShares = (shareholder: AdminShareholder) => {
    setSelectedShareholder(shareholder);
    setHoldingFormData({
      ...initialHoldingData,
      shareholder: shareholder.id,
    });
    setShowHoldingModal(true);
  };

  const handleDeleteShareholder = async (shareholder: AdminShareholder) => {
    if (!confirm(`Are you sure you want to delete ${shareholder.full_name}? This cannot be undone.`)) {
      return;
    }
    try {
      await apiClient.deleteAdminShareholder(shareholder.id);
      toast.success('Shareholder deleted');
      loadData();
    } catch (error) {
      console.error('Error deleting shareholder:', error);
      toast.error('Failed to delete shareholder');
    }
  };

  const handleSubmitShareholder = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const data: any = { ...formData };
      if (!data.tax_id) {
        delete data.tax_id;
      }
      if (showEditModal && selectedShareholder) {
        await apiClient.updateAdminShareholder(selectedShareholder.id, data);
        toast.success('Shareholder updated');
      } else {
        await apiClient.createAdminShareholder(data);
        toast.success('Shareholder created');
      }
      setShowAddModal(false);
      setShowEditModal(false);
      loadData();
    } catch (error: any) {
      console.error('Error saving shareholder:', error);
      const message = error.response?.data?.detail || error.response?.data?.message || 'Failed to save shareholder';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmitHolding = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await apiClient.createAdminHolding(holdingFormData as any);
      toast.success('Shares issued successfully');
      setShowHoldingModal(false);
      loadData();
    } catch (error: any) {
      console.error('Error issuing shares:', error);
      const message = error.response?.data?.detail || error.response?.data?.message || 'Failed to issue shares';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmitIssuer = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await apiClient.createAdminIssuer(issuerFormData as any);
      toast.success('Issuer created successfully');
      setShowIssuerModal(false);
      setIssuerFormData(initialIssuerData);
      loadData();
    } catch (error: any) {
      console.error('Error creating issuer:', error);
      const message = error.response?.data?.detail || error.response?.data?.message || 
        Object.values(error.response?.data || {}).flat().join(', ') || 'Failed to create issuer';
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const filteredSecurityClasses = securityClasses.filter(
    (sc) => sc.issuer === holdingFormData.issuer
  );

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="h-8 bg-gray-200 rounded w-48 animate-pulse" />
          <div className="h-10 bg-gray-200 rounded w-40 animate-pulse" />
        </div>
        <div className="bg-white shadow rounded-lg p-6">
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-12 bg-gray-100 rounded animate-pulse" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Users className="w-8 h-8 text-indigo-600" />
          <h1 className="text-2xl font-bold text-gray-900">Shareholders</h1>
          <span className="bg-gray-100 text-gray-600 px-2 py-1 rounded-full text-sm">
            {shareholders.length} total
          </span>
        </div>
        <button
          onClick={() => setShowIssuerModal(true)}
          className="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
        >
          <Building className="w-5 h-5 mr-2" />
          Add Issuer
        </button>
        <button
          onClick={handleAddShareholder}
          className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
        >
          <Plus className="w-5 h-5 mr-2" />
          Add Shareholder
        </button>
      </div>

      <div className="bg-white shadow rounded-lg">
        <div className="p-4 border-b border-gray-200">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by name or email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
        </div>

        {filteredShareholders.length === 0 ? (
          <div className="p-12 text-center">
            <Users className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              {searchQuery ? 'No shareholders found' : 'No shareholders yet'}
            </h3>
            <p className="text-gray-500 mb-4">
              {searchQuery
                ? 'Try adjusting your search terms'
                : 'Add your first shareholder to start managing your cap table'}
            </p>
            {!searchQuery && (
              <button
                onClick={handleAddShareholder}
                className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
              >
                <Plus className="w-5 h-5 mr-2" />
                Add First Shareholder
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Email
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Location
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredShareholders.map((shareholder) => (
                  <tr key={shareholder.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center">
                          <span className="text-indigo-600 font-medium">
                            {shareholder.full_name?.charAt(0)?.toUpperCase() || '?'}
                          </span>
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">
                            {shareholder.full_name}
                          </div>
                          <div className="text-sm text-gray-500">
                            Added {new Date(shareholder.created_at).toLocaleDateString()}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-600">
                        {shareholder.account_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {shareholder.email || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {shareholder.city && shareholder.state
                        ? `${shareholder.city}, ${shareholder.state}`
                        : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex flex-wrap gap-1">
                        {shareholder.is_accredited_investor && (
                          <span className="px-2 py-0.5 text-xs font-medium rounded bg-green-100 text-green-700">
                            Accredited
                          </span>
                        )}
                        {shareholder.is_insider && (
                          <span className="px-2 py-0.5 text-xs font-medium rounded bg-yellow-100 text-yellow-700">
                            Insider
                          </span>
                        )}
                        {shareholder.is_affiliate && (
                          <span className="px-2 py-0.5 text-xs font-medium rounded bg-blue-100 text-blue-700">
                            Affiliate
                          </span>
                        )}
                        {!shareholder.is_accredited_investor && !shareholder.is_insider && !shareholder.is_affiliate && (
                          <span className="text-gray-400 text-xs">Standard</span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleIssueShares(shareholder)}
                          className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                          title="Issue Shares"
                        >
                          <DollarSign className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleEditShareholder(shareholder)}
                          className="p-2 text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                          title="Edit"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteShareholder(shareholder)}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {(showAddModal || showEditModal) && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b">
              <h2 className="text-xl font-semibold text-gray-900">
                {showEditModal ? 'Edit Shareholder' : 'Add New Shareholder'}
              </h2>
              <button
                onClick={() => {
                  setShowAddModal(false);
                  setShowEditModal(false);
                }}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleSubmitShareholder} className="p-6 space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Account Type
                  </label>
                  <select
                    value={formData.account_type}
                    onChange={(e) =>
                      setFormData({ ...formData, account_type: e.target.value as any })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  >
                    {ACCOUNT_TYPES.map((type) => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}
                  </select>
                </div>

                {formData.account_type === 'ENTITY' ? (
                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Entity Name *
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.entity_name}
                      onChange={(e) => setFormData({ ...formData, entity_name: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                ) : (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        First Name *
                      </label>
                      <input
                        type="text"
                        required
                        value={formData.first_name}
                        onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Last Name *
                      </label>
                      <input
                        type="text"
                        required
                        value={formData.last_name}
                        onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                      />
                    </div>
                  </>
                )}

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                  <input
                    type="tel"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Tax ID Type
                  </label>
                  <select
                    value={formData.tax_id_type}
                    onChange={(e) =>
                      setFormData({ ...formData, tax_id_type: e.target.value as any })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  >
                    {TAX_ID_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {type}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Tax ID {showEditModal && '(leave blank to keep existing)'}
                  </label>
                  <input
                    type="text"
                    value={formData.tax_id}
                    onChange={(e) => setFormData({ ...formData, tax_id: e.target.value })}
                    placeholder={showEditModal ? '***-**-****' : ''}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Address Line 1
                  </label>
                  <input
                    type="text"
                    value={formData.address_line1}
                    onChange={(e) => setFormData({ ...formData, address_line1: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Address Line 2
                  </label>
                  <input
                    type="text"
                    value={formData.address_line2}
                    onChange={(e) => setFormData({ ...formData, address_line2: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">City</label>
                  <input
                    type="text"
                    value={formData.city}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">State</label>
                  <input
                    type="text"
                    value={formData.state}
                    onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">ZIP Code</label>
                  <input
                    type="text"
                    value={formData.zip_code}
                    onChange={(e) => setFormData({ ...formData, zip_code: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Country</label>
                  <input
                    type="text"
                    value={formData.country}
                    onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div className="col-span-2 space-y-3">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.is_accredited_investor}
                      onChange={(e) =>
                        setFormData({ ...formData, is_accredited_investor: e.target.checked })
                      }
                      className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                    />
                    <span className="text-sm text-gray-700">Accredited Investor</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.is_insider}
                      onChange={(e) => setFormData({ ...formData, is_insider: e.target.checked })}
                      className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                    />
                    <span className="text-sm text-gray-700">Insider (10% owner, officer, or director)</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.is_affiliate}
                      onChange={(e) =>
                        setFormData({ ...formData, is_affiliate: e.target.checked })
                      }
                      className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                    />
                    <span className="text-sm text-gray-700">Affiliate</span>
                  </label>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => {
                    setShowAddModal(false);
                    setShowEditModal(false);
                  }}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                >
                  {submitting ? 'Saving...' : showEditModal ? 'Save Changes' : 'Add Shareholder'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showHoldingModal && selectedShareholder && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg">
            <div className="flex items-center justify-between p-6 border-b">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">Issue Shares</h2>
                <p className="text-sm text-gray-500 mt-1">
                  To: {selectedShareholder.full_name}
                </p>
              </div>
              <button
                onClick={() => setShowHoldingModal(false)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {issuers.length === 0 ? (
              <div className="p-6 text-center">
                <Building className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">No Issuers Found</h3>
                <p className="text-gray-500 text-sm">
                  You need to create an issuer (company) before you can issue shares.
                </p>
              </div>
            ) : (
              <form onSubmit={handleSubmitHolding} className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Issuer (Company) *
                  </label>
                  <select
                    required
                    value={holdingFormData.issuer}
                    onChange={(e) =>
                      setHoldingFormData({
                        ...holdingFormData,
                        issuer: e.target.value,
                        security_class: '',
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Select issuer...</option>
                    {issuers.map((issuer) => (
                      <option key={issuer.id} value={issuer.id}>
                        {issuer.company_name} ({issuer.ticker_symbol})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Security Class *
                  </label>
                  <select
                    required
                    value={holdingFormData.security_class}
                    onChange={(e) =>
                      setHoldingFormData({ ...holdingFormData, security_class: e.target.value })
                    }
                    disabled={!holdingFormData.issuer}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-100"
                  >
                    <option value="">
                      {holdingFormData.issuer ? 'Select class...' : 'Select issuer first'}
                    </option>
                    {filteredSecurityClasses.map((sc) => (
                      <option key={sc.id} value={sc.id}>
                        {sc.class_name} - {sc.security_type}
                      </option>
                    ))}
                  </select>
                  {holdingFormData.issuer && filteredSecurityClasses.length === 0 && (
                    <p className="mt-1 text-sm text-amber-600 flex items-center gap-1">
                      <AlertCircle className="w-4 h-4" />
                      No security classes found for this issuer
                    </p>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Number of Shares *
                    </label>
                    <input
                      type="number"
                      required
                      min="1"
                      value={holdingFormData.share_quantity}
                      onChange={(e) =>
                        setHoldingFormData({ ...holdingFormData, share_quantity: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Cost Basis ($)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={holdingFormData.cost_basis}
                      onChange={(e) =>
                        setHoldingFormData({ ...holdingFormData, cost_basis: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Acquisition Date *
                    </label>
                    <input
                      type="date"
                      required
                      value={holdingFormData.acquisition_date}
                      onChange={(e) =>
                        setHoldingFormData({ ...holdingFormData, acquisition_date: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Acquisition Type
                    </label>
                    <select
                      value={holdingFormData.acquisition_type}
                      onChange={(e) =>
                        setHoldingFormData({ ...holdingFormData, acquisition_type: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    >
                      {ACQUISITION_TYPES.map((type) => (
                        <option key={type} value={type}>
                          {type}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Holding Type
                  </label>
                  <select
                    value={holdingFormData.holding_type}
                    onChange={(e) =>
                      setHoldingFormData({ ...holdingFormData, holding_type: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  >
                    {HOLDING_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {type}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={holdingFormData.is_restricted}
                      onChange={(e) =>
                        setHoldingFormData({ ...holdingFormData, is_restricted: e.target.checked })
                      }
                      className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                    />
                    <span className="text-sm text-gray-700">Restricted Shares (Rule 144)</span>
                  </label>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                  <textarea
                    value={holdingFormData.notes}
                    onChange={(e) =>
                      setHoldingFormData({ ...holdingFormData, notes: e.target.value })
                    }
                    rows={2}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div className="flex justify-end gap-3 pt-4 border-t">
                  <button
                    type="button"
                    onClick={() => setShowHoldingModal(false)}
                    className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting || !holdingFormData.security_class}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                  >
                    {submitting ? 'Issuing...' : 'Issue Shares'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {showIssuerModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-semibold text-gray-900">Add Issuer (Company)</h2>
              <button
                onClick={() => setShowIssuerModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
            <form onSubmit={handleSubmitIssuer} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Company Name *
                  </label>
                  <input
                    type="text"
                    value={issuerFormData.company_name}
                    onChange={(e) =>
                      setIssuerFormData({ ...issuerFormData, company_name: e.target.value })
                    }
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    placeholder="Full legal company name"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Ticker Symbol
                  </label>
                  <input
                    type="text"
                    value={issuerFormData.ticker_symbol}
                    onChange={(e) =>
                      setIssuerFormData({ ...issuerFormData, ticker_symbol: e.target.value.toUpperCase() })
                    }
                    maxLength={10}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    placeholder="e.g., AAPL"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    CUSIP
                  </label>
                  <input
                    type="text"
                    value={issuerFormData.cusip}
                    onChange={(e) =>
                      setIssuerFormData({ ...issuerFormData, cusip: e.target.value.toUpperCase() })
                    }
                    maxLength={9}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    placeholder="9-character ID"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    SEC CIK
                  </label>
                  <input
                    type="text"
                    value={issuerFormData.cik}
                    onChange={(e) =>
                      setIssuerFormData({ ...issuerFormData, cik: e.target.value })
                    }
                    maxLength={10}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    placeholder="Central Index Key"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    State of Incorporation *
                  </label>
                  <input
                    type="text"
                    value={issuerFormData.incorporation_state}
                    onChange={(e) =>
                      setIssuerFormData({ ...issuerFormData, incorporation_state: e.target.value.toUpperCase() })
                    }
                    required
                    maxLength={2}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    placeholder="e.g., DE"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Country of Incorporation
                  </label>
                  <input
                    type="text"
                    value={issuerFormData.incorporation_country}
                    onChange={(e) =>
                      setIssuerFormData({ ...issuerFormData, incorporation_country: e.target.value.toUpperCase() })
                    }
                    maxLength={2}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    placeholder="e.g., US"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Total Authorized Shares *
                  </label>
                  <input
                    type="number"
                    value={issuerFormData.total_authorized_shares}
                    onChange={(e) =>
                      setIssuerFormData({ ...issuerFormData, total_authorized_shares: e.target.value })
                    }
                    required
                    min={1}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Par Value
                  </label>
                  <input
                    type="number"
                    value={issuerFormData.par_value}
                    onChange={(e) =>
                      setIssuerFormData({ ...issuerFormData, par_value: e.target.value })
                    }
                    step="0.0001"
                    min={0}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Agreement Start Date *
                  </label>
                  <input
                    type="date"
                    value={issuerFormData.agreement_start_date}
                    onChange={(e) =>
                      setIssuerFormData({ ...issuerFormData, agreement_start_date: e.target.value })
                    }
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Annual Fee ($)
                  </label>
                  <input
                    type="number"
                    value={issuerFormData.annual_fee}
                    onChange={(e) =>
                      setIssuerFormData({ ...issuerFormData, annual_fee: e.target.value })
                    }
                    step="0.01"
                    min={0}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div className="col-span-2">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={issuerFormData.is_active}
                      onChange={(e) =>
                        setIssuerFormData({ ...issuerFormData, is_active: e.target.checked })
                      }
                      className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                    />
                    <span className="text-sm text-gray-700">Active</span>
                  </label>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => setShowIssuerModal(false)}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                >
                  {submitting ? 'Creating...' : 'Create Issuer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
