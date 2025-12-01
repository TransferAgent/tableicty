import { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { apiClient } from '../api/client';
import type { TaxDocument } from '../types';
import { Download, FileText } from 'lucide-react';

export function TaxDocumentsPage() {
  const [documents, setDocuments] = useState<TaxDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    year: new Date().getFullYear(),
    type: '',
  });

  useEffect(() => {
    loadDocuments();
  }, [filters]);

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (filters.year) params.year = filters.year;
      if (filters.type) params.type = filters.type;
      
      const response = await apiClient.getTaxDocuments(params);
      setDocuments(response.documents);
    } catch (err: any) {
      const message = err.response?.data?.error || 'Failed to load tax documents';
      toast.error(message);
      console.error('Failed to load tax documents:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (doc: TaxDocument) => {
    try {
      toast.success(`Downloading ${doc.document_type}...`);
      // Actual download logic would go here
      console.log('Downloading document:', doc.document_type);
    } catch (err) {
      toast.error('Failed to download document');
    }
  };

  const getDocumentTypeBadge = (type: string) => {
    const colors: Record<string, string> = {
      '1099-DIV': 'bg-blue-100 text-blue-800',
      '1099-B': 'bg-purple-100 text-purple-800',
      'STATEMENT': 'bg-gray-100 text-gray-800',
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      'AVAILABLE': 'bg-green-100 text-green-800',
      'PROCESSING': 'bg-yellow-100 text-yellow-800',
      'NOT_APPLICABLE': 'bg-gray-100 text-gray-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return <div className="text-center py-12">Loading tax documents...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Tax Documents</h1>
        <p className="mt-1 text-sm text-gray-600">View and download your tax-related documents</p>
      </div>

      <div className="bg-white shadow rounded-lg p-4">
        <div className="flex gap-4">
          <select
            value={filters.year}
            onChange={(e) => setFilters({ ...filters, year: parseInt(e.target.value) })}
            className="border border-gray-300 rounded-md px-3 py-2"
          >
            {[2024, 2023, 2022, 2021, 2020].map(year => (
              <option key={year} value={year}>{year}</option>
            ))}
          </select>

          <select
            value={filters.type}
            onChange={(e) => setFilters({ ...filters, type: e.target.value })}
            className="border border-gray-300 rounded-md px-3 py-2"
          >
            <option value="">All Types</option>
            <option value="1099-DIV">1099-DIV</option>
            <option value="1099-B">1099-B</option>
            <option value="STATEMENT">Account Statement</option>
          </select>
        </div>
      </div>

      <div className="bg-white shadow overflow-hidden sm:rounded-lg">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tax Year</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Document Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Generated Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Download</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {documents.map((doc) => (
                <tr key={doc.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{doc.tax_year}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 rounded text-xs ${getDocumentTypeBadge(doc.document_type)}`}>
                      {doc.document_type}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{new Date(doc.generated_date).toLocaleDateString()}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 rounded text-xs ${getStatusBadge(doc.status)}`}>
                      {doc.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {doc.status === 'AVAILABLE' && (
                      <button
                        onClick={() => handleDownload(doc)}
                        className="text-indigo-600 hover:text-indigo-900"
                        title="Download document"
                      >
                        <Download className="w-5 h-5" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {documents.length === 0 && (
          <div className="text-center py-12">
            <FileText className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No tax documents available</h3>
            <p className="mt-1 text-sm text-gray-500">
              Tax documents are typically available in January each year.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
