import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mockHoldings, mockTransfers, mockTaxDocuments, mockCertificateRequests, mockPortfolioSummary, mockShareholder } from '../test/mockData';

// Create a mock axios instance
const mockAxiosInstance = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
  interceptors: {
    request: { use: vi.fn(), eject: vi.fn() },
    response: { use: vi.fn(), eject: vi.fn() },
  },
};

// Mock axios module
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => mockAxiosInstance),
  },
}));

// Import apiClient after mock is set up
const { apiClient } = await import('./client');

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  describe('Authentication', () => {
    it('should login successfully and store tokens', async () => {
      const mockResponse = {
        data: {
          access: 'access-token',
          refresh: 'refresh-token',
          user: { id: 1, email: 'test@example.com' },
        },
      };
      mockAxiosInstance.post.mockResolvedValueOnce(mockResponse);

      const credentials = { email: 'test@example.com', password: 'password123' };
      const result = await apiClient.login(credentials);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/auth/login/', credentials);
      expect(result).toEqual(mockResponse.data);
      expect(localStorage.getItem('accessToken')).toBe('access-token');
      expect(localStorage.getItem('refreshToken')).toBe('refresh-token');
    });

    it('should register successfully', async () => {
      const registerData = {
        email: 'new@example.com',
        password: 'password123',
        first_name: 'John',
        last_name: 'Doe',
      };
      const mockResponse = { data: { message: 'User created' } };
      mockAxiosInstance.post.mockResolvedValueOnce(mockResponse);

      const result = await apiClient.register(registerData);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/auth/register/', registerData);
      expect(result).toEqual(mockResponse.data);
    });

    it('should logout and clear tokens', () => {
      localStorage.setItem('accessToken', 'token');
      localStorage.setItem('refreshToken', 'token');

      apiClient.logout();

      expect(localStorage.getItem('accessToken')).toBeNull();
      expect(localStorage.getItem('refreshToken')).toBeNull();
    });
  });

  describe('Portfolio Data', () => {
    it('should fetch holdings', async () => {
      const mockResponse = { data: { holdings: mockHoldings } };
      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse);

      const result = await apiClient.getHoldings();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/holdings/');
      expect(result).toEqual(mockResponse.data);
    });

    it('should fetch portfolio summary', async () => {
      const mockResponse = { data: mockPortfolioSummary };
      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse);

      const result = await apiClient.getPortfolioSummary();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/summary/');
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('Transactions', () => {
    it('should fetch transactions with filters', async () => {
      const mockResponse = { data: { transfers: mockTransfers, total_count: 2 } };
      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse);

      const filters = { status: 'COMPLETED', limit: 50, offset: 0 };
      const result = await apiClient.getTransactions(filters);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/transactions/', {
        params: filters,
      });
      expect(result).toEqual(mockResponse.data);
    });

    it('should fetch transaction details', async () => {
      const mockResponse = { data: mockTransfers[0] };
      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse);

      const result = await apiClient.getTransactionDetails(1);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/transactions/1/');
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('Tax Documents', () => {
    it('should fetch tax documents with filters', async () => {
      const mockResponse = { data: { documents: mockTaxDocuments } };
      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse);

      const filters = { year: 2024, type: '1099-DIV' };
      const result = await apiClient.getTaxDocuments(filters);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/tax-documents/', {
        params: filters,
      });
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('Certificate Conversion', () => {
    it('should fetch certificate requests', async () => {
      const mockResponse = { data: { requests: mockCertificateRequests } };
      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse);

      const result = await apiClient.getCertificateRequests();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/certificate-requests/');
      expect(result).toEqual(mockResponse.data);
    });

    it('should submit certificate conversion request', async () => {
      const requestData = {
        certificate_number: 'CERT-123',
        shares_to_convert: 100,
        notes: 'Test conversion',
      };
      const mockResponse = { data: { id: 1, ...requestData, status: 'PENDING' } };
      mockAxiosInstance.post.mockResolvedValueOnce(mockResponse);

      const result = await apiClient.submitCertificateConversion(requestData);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/certificate-conversion/',
        requestData
      );
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('Profile', () => {
    it('should fetch shareholder profile', async () => {
      const mockResponse = { data: mockShareholder };
      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse);

      const result = await apiClient.getProfile();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/profile/');
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('Error Handling', () => {
    it('should handle API errors properly', async () => {
      const errorResponse = {
        response: {
          data: { error: 'Invalid credentials' },
          status: 401,
        },
      };
      mockAxiosInstance.post.mockRejectedValueOnce(errorResponse);

      await expect(
        apiClient.login({ email: 'test@example.com', password: 'wrong' })
      ).rejects.toEqual(errorResponse);
    });
  });
});
