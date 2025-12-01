import { PieChart, Pie, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import type { Holding } from '../../types';

const COLORS = ['#4F46E5', '#7C3AED', '#EC4899', '#F59E0B', '#10B981', '#3B82F6', '#8B5CF6', '#EF4444'];

interface PortfolioChartsProps {
  holdings: Holding[];
}

interface PieDataItem {
  name: string;
  value: number;
  percentage: string;
  [key: string]: string | number;
}

export function PortfolioCharts({ holdings }: PortfolioChartsProps) {
  const holdingsByCompany = holdings.reduce((acc, holding) => {
    const company = holding.issuer.name;
    const shares = parseFloat(holding.share_quantity);
    
    const existing = acc.find(item => item.name === company);
    if (existing) {
      existing.shares += shares;
    } else {
      acc.push({ name: company, shares });
    }
    return acc;
  }, [] as Array<{ name: string; shares: number }>);

  const holdingsBySecurityClass = holdings.reduce((acc, holding) => {
    const securityType = holding.security_class.type;
    const shares = parseFloat(holding.share_quantity);
    
    const existing = acc.find(item => item.name === securityType);
    if (existing) {
      existing.shares += shares;
    } else {
      acc.push({ name: securityType, shares });
    }
    return acc;
  }, [] as Array<{ name: string; shares: number }>);

  const totalShares = holdingsByCompany.reduce((sum, item) => sum + item.shares, 0);

  const pieData: PieDataItem[] = holdingsByCompany.map(item => ({
    name: item.name,
    value: item.shares,
    percentage: ((item.shares / totalShares) * 100).toFixed(2),
  }));

  const barData = holdingsBySecurityClass.map(item => ({
    name: item.name,
    shares: item.shares,
  }));

  const renderLabel = (props: { name?: string; payload?: PieDataItem }) => {
    const { name, payload } = props;
    if (name && payload?.percentage) {
      return `${name}: ${payload.percentage}%`;
    }
    return '';
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Holdings by Company</h3>
        {pieData.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={renderLabel}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {pieData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number, _name: string, props: { payload?: PieDataItem }) => [
                  `${value.toLocaleString()} shares (${props.payload?.percentage || 0}%)`,
                  props.payload?.name || ''
                ]}
              />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-[300px] text-gray-500">
            No holdings data available
          </div>
        )}
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Share Distribution by Security Class</h3>
        {barData.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={barData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip
                formatter={(value: number) => [`${value.toLocaleString()} shares`, 'Total Shares']}
              />
              <Legend />
              <Bar dataKey="shares" fill="#4F46E5" name="Total Shares" />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-[300px] text-gray-500">
            No holdings data available
          </div>
        )}
      </div>
    </div>
  );
}
