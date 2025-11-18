import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../../test/test-utils';
import { DashboardPage } from '../DashboardPage';
import { apiClient } from '../../api/client';
import { mockHoldings, mockPortfolioSummary } from '../../test/mockData';

vi.mock('../../api/client', () => ({
  apiClient: {
    getHoldings: vi.fn(),
    getPortfolioSummary: vi.fn(),
    login: vi.fn(),
    getCurrentUser: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
    loadTokens: vi.fn(),
    getTokens: vi.fn(() => ({ access: null, refresh: null })),
    clearTokens: vi.fn(),
  },
}));

vi.mock('../../components/charts/PortfolioCharts', () => ({
  PortfolioCharts: ({ holdings }: any) => (
    <div data-testid="portfolio-charts">
      <svg data-testid="chart-svg">
        <text>Mock Chart with {holdings.length} holdings</text>
      </svg>
    </div>
  ),
}));

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state while fetching data', () => {
    vi.mocked(apiClient.getHoldings).mockImplementation(() => 
      new Promise(() => {})
    );
    vi.mocked(apiClient.getPortfolioSummary).mockImplementation(() => 
      new Promise(() => {})
    );
    
    renderWithProviders(<DashboardPage />);
    
    expect(screen.getByText(/loading portfolio/i)).toBeInTheDocument();
  });

  it('displays portfolio summary cards with data', async () => {
    vi.mocked(apiClient.getHoldings).mockResolvedValue({
      count: mockHoldings.length,
      holdings: mockHoldings,
    });
    vi.mocked(apiClient.getPortfolioSummary).mockResolvedValue(mockPortfolioSummary);
    
    renderWithProviders(<DashboardPage />);
    
    await waitFor(() => {
      expect(screen.queryByText(/loading portfolio/i)).not.toBeInTheDocument();
    }, { timeout: 3000 });
    
    expect(screen.getByText('Total Companies')).toBeInTheDocument();
    expect(screen.getByText(mockPortfolioSummary.total_companies.toString())).toBeInTheDocument();
    expect(screen.getByText('Total Shares')).toBeInTheDocument();
  });

  it('displays holdings table with data', async () => {
    vi.mocked(apiClient.getHoldings).mockResolvedValue({
      count: mockHoldings.length,
      holdings: mockHoldings,
    });
    vi.mocked(apiClient.getPortfolioSummary).mockResolvedValue(mockPortfolioSummary);
    
    renderWithProviders(<DashboardPage />);
    
    await waitFor(() => {
      expect(screen.getByText(mockHoldings[0].issuer.name)).toBeInTheDocument();
      expect(screen.getByText(mockHoldings[0].security_class.type)).toBeInTheDocument();
    });
  });

  it('renders portfolio charts when holdings exist', async () => {
    vi.mocked(apiClient.getHoldings).mockResolvedValue({
      count: mockHoldings.length,
      holdings: mockHoldings,
    });
    vi.mocked(apiClient.getPortfolioSummary).mockResolvedValue(mockPortfolioSummary);
    
    renderWithProviders(<DashboardPage />);
    
    await waitFor(() => {
      expect(screen.getByTestId('portfolio-charts')).toBeInTheDocument();
      expect(screen.getByTestId('chart-svg')).toBeInTheDocument();
    });
  });

  it('does not render charts when holdings are empty', async () => {
    vi.mocked(apiClient.getHoldings).mockResolvedValue({
      count: 0,
      holdings: [],
    });
    vi.mocked(apiClient.getPortfolioSummary).mockResolvedValue({
      total_companies: 0,
      total_shares: 0,
      total_holdings: 0,
    });
    
    renderWithProviders(<DashboardPage />);
    
    await waitFor(() => {
      expect(screen.queryByTestId('portfolio-charts')).not.toBeInTheDocument();
    });
  });

  it('handles API error gracefully with error message', async () => {
    const errorMessage = 'Failed to load portfolio data';
    vi.mocked(apiClient.getHoldings).mockRejectedValue({
      response: { data: { error: errorMessage } }
    });
    vi.mocked(apiClient.getPortfolioSummary).mockRejectedValue({
      response: { data: { error: errorMessage } }
    });
    
    renderWithProviders(<DashboardPage />);
    
    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });

  it('fetches both holdings and summary on mount', async () => {
    vi.mocked(apiClient.getHoldings).mockResolvedValue({
      count: mockHoldings.length,
      holdings: mockHoldings,
    });
    vi.mocked(apiClient.getPortfolioSummary).mockResolvedValue(mockPortfolioSummary);
    
    renderWithProviders(<DashboardPage />);
    
    await waitFor(() => {
      expect(apiClient.getHoldings).toHaveBeenCalledTimes(1);
      expect(apiClient.getPortfolioSummary).toHaveBeenCalledTimes(1);
    });
  });

  it('displays correctly formatted share quantities with commas', async () => {
    vi.mocked(apiClient.getHoldings).mockResolvedValue({
      count: mockHoldings.length,
      holdings: mockHoldings,
    });
    vi.mocked(apiClient.getPortfolioSummary).mockResolvedValue(mockPortfolioSummary);
    
    renderWithProviders(<DashboardPage />);
    
    await waitFor(() => {
      expect(screen.getByText('50,000')).toBeInTheDocument();
      expect(screen.getByText('25,000')).toBeInTheDocument();
    });
  });

  it('displays percentage ownership with correct formatting', async () => {
    vi.mocked(apiClient.getHoldings).mockResolvedValue({
      count: mockHoldings.length,
      holdings: mockHoldings,
    });
    vi.mocked(apiClient.getPortfolioSummary).mockResolvedValue(mockPortfolioSummary);
    
    renderWithProviders(<DashboardPage />);
    
    await waitFor(() => {
      expect(screen.getByText('2.5000%')).toBeInTheDocument();
      expect(screen.getByText('5.0000%')).toBeInTheDocument();
    });
  });

  it('passes correct holdings data to PortfolioCharts component', async () => {
    vi.mocked(apiClient.getHoldings).mockResolvedValue({
      count: mockHoldings.length,
      holdings: mockHoldings,
    });
    vi.mocked(apiClient.getPortfolioSummary).mockResolvedValue(mockPortfolioSummary);
    
    renderWithProviders(<DashboardPage />);
    
    await waitFor(() => {
      const chartsComponent = screen.getByTestId('portfolio-charts');
      expect(chartsComponent).toBeInTheDocument();
      expect(screen.getByText(/Mock Chart with 2 holdings/i)).toBeInTheDocument();
    });
  });
});
