import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../test/test-utils';
import { TransactionsPage } from '../TransactionsPage';
import { apiClient } from '../../api/client';
import { mockTransfers } from '../../test/mockData';

vi.mock('../../api/client', () => ({
  apiClient: {
    getTransactions: vi.fn(),
    login: vi.fn(),
    getCurrentUser: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
    loadTokens: vi.fn(),
    getTokens: vi.fn(() => ({ access: null, refresh: null })),
    clearTokens: vi.fn(),
  },
}));

describe('TransactionsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state while fetching transactions', () => {
    vi.mocked(apiClient.getTransactions).mockImplementation(() => 
      new Promise(() => {})
    );
    
    renderWithProviders(<TransactionsPage />);
    
    expect(screen.getByText(/loading transactions/i)).toBeInTheDocument();
  });

  it('displays transactions table with data', async () => {
    vi.mocked(apiClient.getTransactions).mockResolvedValue({
      transfers: mockTransfers,
      count: mockTransfers.length,
    });
    
    renderWithProviders(<TransactionsPage />);
    
    await waitFor(() => {
      expect(screen.getByText(mockTransfers[0].issuer_name)).toBeInTheDocument();
      expect(screen.getByText(mockTransfers[0].security_type)).toBeInTheDocument();
    });
  });

  it('allows filtering by transfer type', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.getTransactions).mockResolvedValue({
      transfers: mockTransfers,
      count: mockTransfers.length,
    });
    
    renderWithProviders(<TransactionsPage />);
    
    await waitFor(() => {
      expect(screen.getByDisplayValue('All Types')).toBeInTheDocument();
    });
    
    const typeFilter = screen.getByDisplayValue('All Types');
    await user.selectOptions(typeFilter, 'TRANSFER_IN');
    
    await waitFor(() => {
      expect(apiClient.getTransactions).toHaveBeenCalledWith(
        expect.objectContaining({ transfer_type: 'TRANSFER_IN' })
      );
    });
  });

  it('allows filtering by status', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.getTransactions).mockResolvedValue({
      transfers: mockTransfers,
      count: mockTransfers.length,
    });
    
    renderWithProviders(<TransactionsPage />);
    
    await waitFor(() => {
      expect(screen.getByDisplayValue('All Status')).toBeInTheDocument();
    });
    
    const statusFilter = screen.getByDisplayValue('All Status');
    await user.selectOptions(statusFilter, 'EXECUTED');
    
    await waitFor(() => {
      expect(apiClient.getTransactions).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'EXECUTED' })
      );
    });
  });

  it('opens detail modal when clicking on transaction row', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.getTransactions).mockResolvedValue({
      transfers: mockTransfers,
      count: mockTransfers.length,
    });
    
    renderWithProviders(<TransactionsPage />);
    
    await waitFor(() => {
      expect(screen.getByText(mockTransfers[0].issuer_name)).toBeInTheDocument();
    });
    
    const firstRow = screen.getByText(mockTransfers[0].issuer_name).closest('tr');
    if (firstRow) {
      await user.click(firstRow);
      
      await waitFor(() => {
        expect(screen.getByText('Transaction Details')).toBeInTheDocument();
      });
    }
  });

  it('handles pagination correctly', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.getTransactions).mockResolvedValue({
      transfers: mockTransfers,
      count: 100,
    });
    
    renderWithProviders(<TransactionsPage />);
    
    await waitFor(() => {
      expect(screen.getByText(/page 1 of 2/i)).toBeInTheDocument();
    });
    
    const nextButton = screen.getByRole('button', { name: /next/i });
    await user.click(nextButton);
    
    await waitFor(() => {
      expect(apiClient.getTransactions).toHaveBeenCalledWith(
        expect.objectContaining({ page: 2 })
      );
    });
  });

  it('exports transactions to CSV', async () => {
    const user = userEvent.setup();
    const createElementSpy = vi.spyOn(document, 'createElement');
    
    vi.mocked(apiClient.getTransactions).mockResolvedValue({
      transfers: mockTransfers,
      count: mockTransfers.length,
    });
    
    renderWithProviders(<TransactionsPage />);
    
    await waitFor(() => {
      expect(screen.getByText(/export csv/i)).toBeInTheDocument();
    });
    
    const exportButton = screen.getByText(/export csv/i);
    await user.click(exportButton);
    
    await waitFor(() => {
      expect(createElementSpy).toHaveBeenCalledWith('a');
    });
    
    createElementSpy.mockRestore();
  });

  it('handles API error gracefully', async () => {
    vi.mocked(apiClient.getTransactions).mockRejectedValue({
      response: { data: { error: 'Failed to load transactions' } }
    });
    
    renderWithProviders(<TransactionsPage />);
    
    await waitFor(() => {
      expect(screen.queryByTestId('skeleton-table')).not.toBeInTheDocument();
    });
  });

  it('displays empty state when no transactions found', async () => {
    vi.mocked(apiClient.getTransactions).mockResolvedValue({
      transfers: [],
      count: 0,
    });
    
    renderWithProviders(<TransactionsPage />);
    
    await waitFor(() => {
      expect(screen.getByText(/no transactions found/i)).toBeInTheDocument();
    });
  });

  it('calls API with correct pagination parameters on mount', async () => {
    vi.mocked(apiClient.getTransactions).mockResolvedValue({
      transfers: mockTransfers,
      count: mockTransfers.length,
    });
    
    renderWithProviders(<TransactionsPage />);
    
    await waitFor(() => {
      expect(apiClient.getTransactions).toHaveBeenCalledWith(
        expect.objectContaining({ 
          page: 1,
          page_size: 50,
        })
      );
    });
  });
});
