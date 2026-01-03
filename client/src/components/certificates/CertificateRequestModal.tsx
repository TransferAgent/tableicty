import { useState } from 'react';
import { X, Check, XCircle, FileText, User, Calendar, Package } from 'lucide-react';
import { apiClient } from '../../api/client';
import type { AdminCertificateRequest } from '../../types';
import toast from 'react-hot-toast';

interface CertificateRequestModalProps {
  request: AdminCertificateRequest;
  onClose: () => void;
  onUpdate: (updated: AdminCertificateRequest) => void;
}

export function CertificateRequestModal({ request, onClose, onUpdate }: CertificateRequestModalProps) {
  const [mode, setMode] = useState<'view' | 'approve' | 'reject'>('view');
  const [certificateNumber, setCertificateNumber] = useState(request.certificate_number || '');
  const [adminNotes, setAdminNotes] = useState(request.admin_notes || '');
  const [rejectionReason, setRejectionReason] = useState(request.rejection_reason || '');
  const [sendEmail, setSendEmail] = useState(true);
  const [loading, setLoading] = useState(false);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatShareQuantity = (qty: string | number) => {
    const num = typeof qty === 'string' ? parseFloat(qty) : qty;
    if (num % 1 === 0) {
      return num.toLocaleString();
    }
    return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 });
  };

  const handleApprove = async () => {
    setLoading(true);
    try {
      const updated = await apiClient.approveCertificateRequest(request.id, {
        certificate_number: certificateNumber || undefined,
        admin_notes: adminNotes || undefined,
        send_email: sendEmail,
      });
      toast.success('Certificate request approved');
      onUpdate(updated);
      onClose();
    } catch (err: any) {
      const message = err.response?.data?.error || 'Failed to approve request';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    if (!rejectionReason.trim()) {
      toast.error('Please provide a rejection reason');
      return;
    }
    setLoading(true);
    try {
      const updated = await apiClient.rejectCertificateRequest(request.id, {
        rejection_reason: rejectionReason,
        admin_notes: adminNotes || undefined,
      });
      toast.success('Certificate request rejected');
      onUpdate(updated);
      onClose();
    } catch (err: any) {
      const message = err.response?.data?.error || 'Failed to reject request';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const statusColors = {
    PENDING: 'bg-yellow-100 text-yellow-800',
    PROCESSING: 'bg-blue-100 text-blue-800',
    COMPLETED: 'bg-green-100 text-green-800',
    REJECTED: 'bg-red-100 text-red-800',
  };

  const conversionTypeLabels = {
    DRS_TO_CERT: 'DRS to Physical Certificate',
    CERT_TO_DRS: 'Physical Certificate to DRS',
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold text-gray-900">Certificate Request Details</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          <div className="flex items-center justify-between">
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusColors[request.status]}`}>
              {request.status}
            </span>
            <span className="text-sm text-gray-500">
              {conversionTypeLabels[request.conversion_type]}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <User className="w-5 h-5 text-gray-400 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-gray-500">Shareholder</p>
                  <p className="text-gray-900">{request.shareholder?.full_name || 'Unknown'}</p>
                  <p className="text-sm text-gray-500">{request.shareholder?.email || ''}</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <Package className="w-5 h-5 text-gray-400 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-gray-500">Shares</p>
                  <p className="text-gray-900">{formatShareQuantity(request.share_quantity)} shares</p>
                  <p className="text-sm text-gray-500">
                    {request.holding?.issuer?.company_name || 'Unknown Issuer'} - {request.holding?.security_class?.name || 'Unknown Class'}
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <Calendar className="w-5 h-5 text-gray-400 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-gray-500">Submitted</p>
                  <p className="text-gray-900">{formatDate(request.created_at)}</p>
                </div>
              </div>

              {request.mailing_address && (
                <div className="flex items-start gap-3">
                  <FileText className="w-5 h-5 text-gray-400 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-gray-500">Mailing Address</p>
                    <p className="text-gray-900 whitespace-pre-line">{request.mailing_address}</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {request.shareholder_notes && (
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm font-medium text-gray-500 mb-1">Shareholder Notes</p>
              <p className="text-gray-900">{request.shareholder_notes}</p>
            </div>
          )}

          {request.status === 'COMPLETED' && request.certificate_number && (
            <div className="bg-green-50 rounded-lg p-4">
              <p className="text-sm font-medium text-green-700 mb-1">Certificate Number</p>
              <p className="text-green-900 font-mono">{request.certificate_number}</p>
            </div>
          )}

          {request.status === 'REJECTED' && request.rejection_reason && (
            <div className="bg-red-50 rounded-lg p-4">
              <p className="text-sm font-medium text-red-700 mb-1">Rejection Reason</p>
              <p className="text-red-900">{request.rejection_reason}</p>
            </div>
          )}

          {request.status === 'PENDING' && mode === 'view' && (
            <div className="flex gap-3">
              <button
                onClick={() => setMode('approve')}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                <Check className="w-4 h-4" />
                Approve
              </button>
              <button
                onClick={() => setMode('reject')}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                <XCircle className="w-4 h-4" />
                Reject
              </button>
            </div>
          )}

          {mode === 'approve' && (
            <div className="border-t pt-6 space-y-4">
              <h3 className="text-lg font-medium text-gray-900">Approve Request</h3>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Certificate Number (optional)
                </label>
                <input
                  type="text"
                  value={certificateNumber}
                  onChange={(e) => setCertificateNumber(e.target.value)}
                  placeholder="e.g., CERT-2026-001"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Admin Notes (optional)
                </label>
                <textarea
                  value={adminNotes}
                  onChange={(e) => setAdminNotes(e.target.value)}
                  placeholder="Internal notes about this approval..."
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="sendEmail"
                  checked={sendEmail}
                  onChange={(e) => setSendEmail(e.target.checked)}
                  className="w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500"
                />
                <label htmlFor="sendEmail" className="text-sm text-gray-700">
                  Send email notification to shareholder
                </label>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setMode('view')}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                  disabled={loading}
                >
                  Cancel
                </button>
                <button
                  onClick={handleApprove}
                  disabled={loading}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                >
                  {loading ? 'Processing...' : 'Confirm Approval'}
                </button>
              </div>
            </div>
          )}

          {mode === 'reject' && (
            <div className="border-t pt-6 space-y-4">
              <h3 className="text-lg font-medium text-gray-900">Reject Request</h3>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Rejection Reason *
                </label>
                <textarea
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="Explain why this request is being rejected..."
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Admin Notes (optional)
                </label>
                <textarea
                  value={adminNotes}
                  onChange={(e) => setAdminNotes(e.target.value)}
                  placeholder="Internal notes about this rejection..."
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500"
                />
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setMode('view')}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                  disabled={loading}
                >
                  Cancel
                </button>
                <button
                  onClick={handleReject}
                  disabled={loading || !rejectionReason.trim()}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
                >
                  {loading ? 'Processing...' : 'Confirm Rejection'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
