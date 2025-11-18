import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import type { Holding } from '../types';
import { Plus, X } from 'lucide-react';

export function CertificatesPage() {
  const [showModal, setShowModal] = useState(false);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [requests, setRequests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [formData, setFormData] = useState<{
    holding_id: string;
    conversion_type: 'DRS_TO_CERT' | 'CERT_TO_DRS';
    share_quantity: string;
    mailing_address: string;
  }>({
    holding_id: '',
    conversion_type: 'DRS_TO_CERT',
    share_quantity: '',
    mailing_address: '',
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [holdingsData, requestsData] = await Promise.all([
        apiClient.getHoldings(),
        apiClient.getCertificateConversionRequests(),
      ]);
      setHoldings(holdingsData.holdings);
      setRequests(requestsData);
    } catch (err) {
      console.error('Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiClient.submitCertificateConversion({
        holding_id: parseInt(formData.holding_id),
        conversion_type: formData.conversion_type,
        share_quantity: parseInt(formData.share_quantity),
        mailing_address: formData.mailing_address || undefined,
      });
      setShowModal(false);
      setFormData({
        holding_id: '',
        conversion_type: 'DRS_TO_CERT',
        share_quantity: '',
        mailing_address: '',
      });
      loadData();
    } catch (err) {
      console.error('Failed to submit request:', err);
    }
  };

  const selectedHolding = holdings.find(h => h.id.toString() === formData.holding_id);
  const maxShares = selectedHolding ? parseFloat(selectedHolding.share_quantity) : 0;

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      'PENDING': 'bg-yellow-100 text-yellow-800',
      'PROCESSING': 'bg-blue-100 text-blue-800',
      'COMPLETED': 'bg-green-100 text-green-800',
      'REJECTED': 'bg-red-100 text-red-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return <div className="text-center py-12">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Certificate Management</h1>
          <p className="mt-1 text-sm text-gray-600">Request conversion between DRS and paper certificates</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
        >
          <Plus className="w-4 h-4 mr-2" />
          Request Conversion
        </button>
      </div>

      <div className="bg-white shadow overflow-hidden sm:rounded-lg">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Request Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Issuer</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Security Class</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Shares</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {requests.map((request, idx) => (
                <tr key={request.id || idx} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {request.created_at ? new Date(request.created_at).toLocaleDateString() : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{request.issuer_name || '-'}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{request.security_type || '-'}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{request.conversion_type || '-'}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{request.share_quantity || '-'}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 rounded text-xs ${getStatusBadge(request.status || 'PENDING')}`}>
                      {request.status || 'PENDING'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {requests.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500">No conversion requests yet</p>
          </div>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Request Certificate Conversion</h2>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Select Holding</label>
                <select
                  required
                  value={formData.holding_id}
                  onChange={(e) => setFormData({ ...formData, holding_id: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                >
                  <option value="">Choose a holding...</option>
                  {holdings.map((holding) => (
                    <option key={holding.id} value={holding.id}>
                      {holding.issuer.name} - {holding.security_class.type} ({parseFloat(holding.share_quantity).toLocaleString()} shares)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Conversion Type</label>
                <div className="space-y-2">
                  <label className="flex items-center">
                    <input
                      type="radio"
                      value="DRS_TO_CERT"
                      checked={formData.conversion_type === 'DRS_TO_CERT'}
                      onChange={(e) => setFormData({ ...formData, conversion_type: e.target.value as 'DRS_TO_CERT' | 'CERT_TO_DRS' })}
                      className="mr-2"
                    />
                    <span className="text-sm">DRS → Paper Certificate (request physical cert)</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="radio"
                      value="CERT_TO_DRS"
                      checked={formData.conversion_type === 'CERT_TO_DRS'}
                      onChange={(e) => setFormData({ ...formData, conversion_type: e.target.value as 'DRS_TO_CERT' | 'CERT_TO_DRS' })}
                      className="mr-2"
                    />
                    <span className="text-sm">Paper Certificate → DRS (convert to electronic)</span>
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Share Quantity</label>
                <input
                  type="number"
                  required
                  min="1"
                  max={maxShares}
                  value={formData.share_quantity}
                  onChange={(e) => setFormData({ ...formData, share_quantity: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                  placeholder="Enter number of shares"
                />
                {selectedHolding && (
                  <p className="text-xs text-gray-500 mt-1">Maximum: {maxShares.toLocaleString()} shares</p>
                )}
              </div>

              {formData.conversion_type === 'DRS_TO_CERT' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Mailing Address</label>
                  <textarea
                    value={formData.mailing_address}
                    onChange={(e) => setFormData({ ...formData, mailing_address: e.target.value })}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                    rows={3}
                    placeholder="Enter mailing address for physical certificate"
                  />
                </div>
              )}

              <div className="flex gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                >
                  Submit Request
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
