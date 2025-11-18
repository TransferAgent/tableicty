import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import type { Holding, PortfolioSummary } from '../types';
import { formatNumber, formatDate } from '../lib/utils';
import { TrendingUp, Building2, Briefcase } from 'lucide-react';
import { PortfolioCharts } from '../components/charts/PortfolioCharts';

export function DashboardPage() {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [holdingsData, summaryData] = await Promise.all([
        apiClient.getHoldings(),
        apiClient.getPortfolioSummary(),
      ]);
      setHoldings(holdingsData.holdings);
      setSummary(summaryData);
    } catch (err: any) {
      setError('Failed to load portfolio data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading portfolio...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md bg-red-50 p-4">
        <p className="text-sm text-red-800">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Portfolio Overview</h1>
        <p className="mt-1 text-sm text-gray-600">View your shareholdings and portfolio summary</p>
      </div>

      {summary && (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Building2 className="h-6 w-6 text-indigo-600" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Total Companies</dt>
                    <dd className="text-2xl font-semibold text-gray-900">{summary.total_companies}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <TrendingUp className="h-6 w-6 text-green-600" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Total Shares</dt>
                    <dd className="text-2xl font-semibold text-gray-900">{formatNumber(summary.total_shares)}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Briefcase className="h-6 w-6 text-blue-600" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Total Holdings</dt>
                    <dd className="text-2xl font-semibold text-gray-900">{summary.total_holdings}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {holdings.length > 0 && <PortfolioCharts holdings={holdings} />}

      <div className="bg-white shadow overflow-hidden sm:rounded-lg">
        <div className="px-4 py-5 sm:px-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900">Your Holdings</h3>
          <p className="mt-1 max-w-2xl text-sm text-gray-500">Detailed view of all your shareholdings</p>
        </div>
        <div className="border-t border-gray-200">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Company
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Security Type
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Shares
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Ownership %
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Acquired
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {holdings.map((holding) => (
                  <tr key={holding.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{holding.issuer.name}</div>
                      <div className="text-sm text-gray-500">{holding.issuer.ticker || 'N/A'}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{holding.security_class.type}</div>
                      <div className="text-sm text-gray-500">{holding.security_class.designation}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatNumber(parseFloat(holding.share_quantity))}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {holding.percentage_ownership.toFixed(4)}%
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                        {holding.holding_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(holding.acquisition_date)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {holdings.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-500">No holdings found</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
