import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import type { AdminIssuer, AdminHolding } from '../types';
import { PieChart, Building, TrendingUp, Users, Percent } from 'lucide-react';
import toast from 'react-hot-toast';

interface CapTableEntry {
  shareholderId: string;
  shareholderName: string;
  shares: number;
  percentage: number;
  securityClass: string;
}

interface CapTableSummary {
  totalShares: number;
  totalShareholders: number;
  byClass: { className: string; shares: number; percentage: number }[];
  topShareholders: CapTableEntry[];
}

export function CapTablePage() {
  const [issuers, setIssuers] = useState<AdminIssuer[]>([]);
  const [holdings, setHoldings] = useState<AdminHolding[]>([]);
  const [selectedIssuerId, setSelectedIssuerId] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [capTable, setCapTable] = useState<CapTableSummary | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (selectedIssuerId && holdings.length > 0) {
      calculateCapTable();
    }
  }, [selectedIssuerId, holdings]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [issuersRes, holdingsRes] = await Promise.all([
        apiClient.getAdminIssuers(),
        apiClient.getAdminHoldings(),
      ]);
      setIssuers(issuersRes.results || []);
      setHoldings(holdingsRes.results || []);
      
      if (issuersRes.results && issuersRes.results.length > 0) {
        setSelectedIssuerId(issuersRes.results[0].id);
      }
    } catch (error) {
      console.error('Error loading data:', error);
      toast.error('Failed to load cap table data');
    } finally {
      setLoading(false);
    }
  };

  const calculateCapTable = () => {
    const issuerHoldings = holdings.filter((h) => h.issuer === selectedIssuerId);
    
    let totalShares = 0;
    const shareholderShares: Record<string, { name: string; shares: number }> = {};
    const classTotals: Record<string, { name: string; shares: number }> = {};

    for (const holding of issuerHoldings) {
      const shares = parseFloat(holding.share_quantity) || 0;
      totalShares += shares;

      const shareholderName = holding.shareholder_name || 'Unknown';
      if (!shareholderShares[holding.shareholder]) {
        shareholderShares[holding.shareholder] = { name: shareholderName, shares: 0 };
      }
      shareholderShares[holding.shareholder].shares += shares;

      const className = holding.security_class_name || 'Unknown';
      if (!classTotals[holding.security_class]) {
        classTotals[holding.security_class] = { name: className, shares: 0 };
      }
      classTotals[holding.security_class].shares += shares;
    }

    const byClass = Object.entries(classTotals).map(([, data]) => ({
      className: data.name,
      shares: data.shares,
      percentage: totalShares > 0 ? (data.shares / totalShares) * 100 : 0,
    }));

    const topShareholders = Object.entries(shareholderShares)
      .map(([shareholderId, data]) => ({
        shareholderId,
        shareholderName: data.name,
        shares: data.shares,
        percentage: totalShares > 0 ? (data.shares / totalShares) * 100 : 0,
        securityClass: '',
      }))
      .sort((a, b) => b.shares - a.shares)
      .slice(0, 10);

    setCapTable({
      totalShares,
      totalShareholders: Object.keys(shareholderShares).length,
      byClass,
      topShareholders,
    });
  };

  const formatNumber = (num: number): string => {
    return new Intl.NumberFormat('en-US').format(num);
  };

  const formatPercent = (num: number): string => {
    return num.toFixed(2) + '%';
  };

  const selectedIssuer = issuers.find((i) => i.id === selectedIssuerId);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="h-8 bg-gray-200 rounded w-48 animate-pulse" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white shadow rounded-lg p-6">
              <div className="h-20 bg-gray-100 rounded animate-pulse" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <PieChart className="w-8 h-8 text-indigo-600" />
          <h1 className="text-2xl font-bold text-gray-900">Cap Table</h1>
        </div>

        {issuers.length > 1 && (
          <select
            value={selectedIssuerId}
            onChange={(e) => setSelectedIssuerId(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
          >
            {issuers.map((issuer) => (
              <option key={issuer.id} value={issuer.id}>
                {issuer.company_name} ({issuer.ticker_symbol})
              </option>
            ))}
          </select>
        )}
      </div>

      {issuers.length === 0 ? (
        <div className="bg-white shadow rounded-lg p-12 text-center">
          <Building className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Issuers Found</h3>
          <p className="text-gray-500">
            Create an issuer (company) first to view cap table data.
          </p>
        </div>
      ) : !capTable ? (
        <div className="bg-white shadow rounded-lg p-12 text-center">
          <PieChart className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Holdings Data</h3>
          <p className="text-gray-500">Issue shares to shareholders to see cap table data.</p>
        </div>
      ) : (
        <>
          {selectedIssuer && (
            <div className="bg-white shadow rounded-lg p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-indigo-100 flex items-center justify-center">
                  <Building className="w-6 h-6 text-indigo-600" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">
                    {selectedIssuer.company_name}
                  </h2>
                  <p className="text-gray-500">
                    {selectedIssuer.ticker_symbol} | {selectedIssuer.otc_tier || 'Private'}
                  </p>
                </div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white shadow rounded-lg p-6">
              <div className="flex items-center gap-3 mb-2">
                <TrendingUp className="w-5 h-5 text-green-600" />
                <h3 className="text-sm font-medium text-gray-500 uppercase">Total Shares</h3>
              </div>
              <p className="text-3xl font-bold text-gray-900">{formatNumber(capTable.totalShares)}</p>
            </div>

            <div className="bg-white shadow rounded-lg p-6">
              <div className="flex items-center gap-3 mb-2">
                <Users className="w-5 h-5 text-blue-600" />
                <h3 className="text-sm font-medium text-gray-500 uppercase">Shareholders</h3>
              </div>
              <p className="text-3xl font-bold text-gray-900">{capTable.totalShareholders}</p>
            </div>

            <div className="bg-white shadow rounded-lg p-6">
              <div className="flex items-center gap-3 mb-2">
                <Percent className="w-5 h-5 text-purple-600" />
                <h3 className="text-sm font-medium text-gray-500 uppercase">Security Classes</h3>
              </div>
              <p className="text-3xl font-bold text-gray-900">{capTable.byClass.length}</p>
            </div>
          </div>

          {capTable.byClass.length > 0 && (
            <div className="bg-white shadow rounded-lg overflow-hidden">
              <div className="p-6 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Shares by Security Class</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Class
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                        Shares
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                        Percentage
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Distribution
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {capTable.byClass.map((classData, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                          {classData.className}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-gray-600">
                          {formatNumber(classData.shares)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-gray-600">
                          {formatPercent(classData.percentage)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="w-full bg-gray-200 rounded-full h-2.5">
                            <div
                              className="bg-indigo-600 h-2.5 rounded-full"
                              style={{ width: `${Math.min(classData.percentage, 100)}%` }}
                            />
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {capTable.topShareholders.length > 0 && (
            <div className="bg-white shadow rounded-lg overflow-hidden">
              <div className="p-6 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Top Shareholders</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Rank
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Shareholder
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                        Shares
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                        Ownership
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Distribution
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {capTable.topShareholders.map((entry, idx) => (
                      <tr key={entry.shareholderId} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-gray-100 text-sm font-medium text-gray-600">
                            {idx + 1}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center mr-3">
                              <span className="text-indigo-600 text-sm font-medium">
                                {entry.shareholderName.charAt(0).toUpperCase()}
                              </span>
                            </div>
                            <span className="font-medium text-gray-900">{entry.shareholderName}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-gray-600">
                          {formatNumber(entry.shares)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right font-medium text-gray-900">
                          {formatPercent(entry.percentage)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="w-full bg-gray-200 rounded-full h-2.5">
                            <div
                              className="bg-green-600 h-2.5 rounded-full"
                              style={{ width: `${Math.min(entry.percentage, 100)}%` }}
                            />
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
