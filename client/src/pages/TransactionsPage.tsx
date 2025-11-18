import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import type { Transfer } from '../types';
import { formatNumber, formatDate } from '../lib/utils';
import { Download, Filter, ChevronLeft, ChevronRight } from 'lucide-react';

export function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transfer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedTransaction, setSelectedTransaction] = useState<Transfer | null>(null);
  
  const [filters, setFilters] = useState({
    transfer_type: '',
    status: '',
    year: new Date().getFullYear(),
  });
  
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const pageSize = 50;

  useEffect(() => {
    loadTransactions();
  }, [filters, page]);

  const loadTransactions = async () => {
    setLoading(true);
    try {
      const params: any = { page, page_size: pageSize };
      if (filters.transfer_type) params.transfer_type = filters.transfer_type;
      if (filters.status) params.status = filters.status;
      if (filters.year) params.year = filters.year;
      
      const response = await apiClient.getTransactions(params);
      setTransactions(response.transfers);
      setTotalPages(Math.ceil(response.count / pageSize));
    } catch (err: any) {
      setError('Failed to load transactions');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = async () => {
    try {
      const params: any = {};
      if (filters.transfer_type) params.transfer_type = filters.transfer_type;
      if (filters.status) params.status = filters.status;
      if (filters.year) params.year = filters.year;
      
      const response = await apiClient.getTransactions(params);
      const csvContent = convertToCSV(response.transfers);
      downloadCSV(csvContent, `transactions_${new Date().toISOString().split('T')[0]}.csv`);
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  const convertToCSV = (data: Transfer[]) => {
    const headers = ['Date', 'Type', 'Issuer', 'Security Class', 'Shares', 'Status'];
    const rows = data.map(t => [
      formatDate(t.transfer_date),
      t.transfer_type,
      t.security_class.issuer.name,
      t.security_class.type,
      t.share_quantity,
      t.status,
    ]);
    
    return [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n');
  };

  const downloadCSV = (content: string, filename: string) => {
    const blob = new Blob([content], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const TransactionDetailModal = ({ transaction, onClose }: { transaction: Transfer; onClose: () => void }) => (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-xl font-bold mb-4">Transaction Details</h2>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-500">Transfer Date</p>
              <p className="font-medium">{formatDate(transaction.transfer_date)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Type</p>
              <p className="font-medium">{transaction.transfer_type}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Status</p>
              <span className={`px-2 py-1 rounded text-sm ${
                transaction.status === 'EXECUTED' ? 'bg-green-100 text-green-800' :
                transaction.status === 'PENDING' ? 'bg-yellow-100 text-yellow-800' :
                'bg-red-100 text-red-800'
              }`}>
                {transaction.status}
              </span>
            </div>
            <div>
              <p className="text-sm text-gray-500">Shares</p>
              <p className="font-medium">{formatNumber(parseFloat(transaction.share_quantity))}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Issuer</p>
              <p className="font-medium">{transaction.security_class.issuer.name}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Security Class</p>
              <p className="font-medium">{transaction.security_class.type}</p>
            </div>
          </div>
        </div>
        <button
          onClick={onClose}
          className="mt-6 px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
        >
          Close
        </button>
      </div>
    </div>
  );

  if (loading && transactions.length === 0) {
    return <div className="text-center py-12">Loading transactions...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Transaction History</h1>
          <p className="mt-1 text-sm text-gray-600">View all your stock transfer transactions</p>
        </div>
        <button
          onClick={handleExportCSV}
          className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
        >
          <Download className="w-4 h-4 mr-2" />
          Export CSV
        </button>
      </div>

      <div className="bg-white shadow rounded-lg p-4">
        <div className="flex items-center gap-4 mb-4">
          <Filter className="w-5 h-5 text-gray-400" />
          <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-4">
            <select
              value={filters.transfer_type}
              onChange={(e) => setFilters({ ...filters, transfer_type: e.target.value })}
              className="border border-gray-300 rounded-md px-3 py-2"
            >
              <option value="">All Types</option>
              <option value="TRANSFER_IN">Transfer In</option>
              <option value="TRANSFER_OUT">Transfer Out</option>
              <option value="DIVIDEND">Dividend</option>
              <option value="CORPORATE_ACTION">Corporate Action</option>
            </select>

            <select
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              className="border border-gray-300 rounded-md px-3 py-2"
            >
              <option value="">All Status</option>
              <option value="EXECUTED">Executed</option>
              <option value="PENDING">Pending</option>
              <option value="CANCELLED">Cancelled</option>
            </select>

            <select
              value={filters.year}
              onChange={(e) => setFilters({ ...filters, year: parseInt(e.target.value) })}
              className="border border-gray-300 rounded-md px-3 py-2"
            >
              {[2024, 2023, 2022, 2021, 2020].map(year => (
                <option key={year} value={year}>{year}</option>
              ))}
              <option value={0}>All Years</option>
            </select>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      <div className="bg-white shadow overflow-hidden sm:rounded-lg">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Issuer</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Security</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Shares</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {transactions.map((transaction) => (
                <tr
                  key={transaction.id}
                  onClick={() => setSelectedTransaction(transaction)}
                  className="hover:bg-gray-50 cursor-pointer"
                >
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{formatDate(transaction.transfer_date)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{transaction.transfer_type}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{transaction.security_class.issuer.name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{transaction.security_class.type}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{formatNumber(parseFloat(transaction.share_quantity))}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 rounded text-xs ${
                      transaction.status === 'EXECUTED' ? 'bg-green-100 text-green-800' :
                      transaction.status === 'PENDING' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {transaction.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {transactions.length === 0 && !loading && (
          <div className="text-center py-12">
            <p className="text-gray-500">No transactions found</p>
          </div>
        )}

        {totalPages > 1 && (
          <div className="px-6 py-4 flex items-center justify-between border-t border-gray-200">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="flex items-center px-3 py-2 border rounded-md disabled:opacity-50"
            >
              <ChevronLeft className="w-4 h-4 mr-1" />
              Previous
            </button>
            <span className="text-sm text-gray-700">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="flex items-center px-3 py-2 border rounded-md disabled:opacity-50"
            >
              Next
              <ChevronRight className="w-4 h-4 ml-1" />
            </button>
          </div>
        )}
      </div>

      {selectedTransaction && (
        <TransactionDetailModal
          transaction={selectedTransaction}
          onClose={() => setSelectedTransaction(null)}
        />
      )}
    </div>
  );
}
