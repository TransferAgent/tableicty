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
    it('should login successfully and return auth data', async () => {
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
      expect(result.access).toBe('access-token');
      expect(result.refresh).toBe('refresh-token');
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

    it('should logout successfully', async () => {
      mockAxiosInstance.post.mockResolvedValueOnce({ data: {} });

      await apiClient.logout();

      // Verify logout completes without throwing
      expect(true).toBe(true);
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
    it('should fetch certificate conversion requests', async () => {
      const mockResponse = mockCertificateRequests;
      mockAxiosInstance.get.mockResolvedValueOnce({ data: mockResponse });

      const result = await apiClient.getCertificateConversionRequests();

      expect(mockAxiosInstance.get).toHaveBeenCalled();
      expect(result).toEqual(mockResponse);
    });

    it('should submit certificate conversion request', async () => {
      const requestData = {
        holding_id: 1,
        conversion_type: 'CERT_TO_BOOK',
        share_quantity: 100,
        mailing_address: '123 Main St',
      };
      const mockResponse = { id: 1, ...requestData, status: 'PENDING' };
      mockAxiosInstance.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await apiClient.submitCertificateConversion(requestData);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/certificate-conversion/',
        requestData
      );
      expect(result).toEqual(mockResponse);
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
    it('should propagate API errors', async () => {
      const error = new Error('Network error');
      mockAxiosInstance.post.mockRejectedValueOnce(error);

      await expect(
        apiClient.login({ email: 'test@example.com', password: 'wrong' })
      ).rejects.toThrow('Network error');
    });
  });
});
