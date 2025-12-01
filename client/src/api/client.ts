import axios, { type AxiosInstance, AxiosError } from 'axios';
import type {
  User,
  Holding,
  Transfer,
  TaxDocument,
  PortfolioSummary,
  LoginCredentials,
  RegisterData,
  AuthResponse,
  Shareholder,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL 
  ? `${import.meta.env.VITE_API_BASE_URL}/api/v1/shareholder`
  : '/api/v1/shareholder';

class APIClient {
  private client: AxiosInstance;
  private accessToken: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.client.interceptors.request.use((config) => {
      if (this.accessToken) {
        config.headers.Authorization = `Bearer ${this.accessToken}`;
      }
      return config;
    });

    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as any;

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            const newAccessToken = await this.refreshAccessToken();
            if (newAccessToken && originalRequest) {
              originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
              return this.client(originalRequest);
            }
          } catch (refreshError) {
            this.logout();
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  setAccessToken(access: string) {
    this.accessToken = access;
    sessionStorage.setItem('access_token', access);
  }

  getAccessToken() {
    return this.accessToken || sessionStorage.getItem('access_token');
  }

  loadTokens() {
    this.accessToken = sessionStorage.getItem('access_token');
  }

  clearTokens() {
    this.accessToken = null;
    sessionStorage.removeItem('access_token');
  }

  async register(data: RegisterData): Promise<AuthResponse> {
    const response = await this.client.post('/auth/register/', data);
    const authData = response.data;
    if (authData.access) {
      this.setAccessToken(authData.access);
    }
    return authData;
  }

  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await this.client.post('/auth/login/', credentials);
    const authData = response.data;
    this.setAccessToken(authData.access);
    return authData;
  }

  async logout(): Promise<void> {
    try {
      await this.client.post('/auth/logout/', {});
    } finally {
      this.clearTokens();
    }
  }

  async refreshAccessToken(): Promise<string | null> {
    try {
      const response = await this.client.post('/auth/refresh/', {});
      const { access } = response.data;
      this.accessToken = access;
      sessionStorage.setItem('access_token', access);
      return access;
    } catch (error) {
      this.clearTokens();
      return null;
    }
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get('/auth/me/');
    return response.data;
  }

  async getHoldings(): Promise<{ count: number; holdings: Holding[] }> {
    const response = await this.client.get('/holdings/');
    return response.data;
  }

  async getPortfolioSummary(): Promise<PortfolioSummary> {
    const response = await this.client.get('/summary/');
    return response.data;
  }

  async getTransactions(params?: {
    transfer_type?: string;
    status?: string;
    year?: number;
    page?: number;
    page_size?: number;
  }): Promise<{ count: number; transfers: Transfer[] }> {
    const response = await this.client.get('/transactions/', { params });
    return response.data;
  }

  async getTaxDocuments(params?: {
    year?: number;
    type?: string;
  }): Promise<{ count: number; documents: TaxDocument[] }> {
    const response = await this.client.get('/tax-documents/', { params });
    return response.data;
  }

  async getCertificateConversionRequests(): Promise<any[]> {
    const response = await this.client.get('/certificate-requests/');
    return response.data;
  }

  async submitCertificateConversion(data: { holding_id: number; conversion_type: string; share_quantity: number; mailing_address?: string }): Promise<any> {
    const response = await this.client.post('/certificate-conversion/', data);
    return response.data;
  }

  async getProfile(): Promise<Shareholder> {
    const response = await this.client.get('/profile/');
    return response.data;
  }

  async updateProfile(data: Partial<Shareholder>): Promise<{ message: string; profile: Shareholder }> {
    const response = await this.client.patch('/profile/', data);
    return response.data;
  }
}

export const apiClient = new APIClient();
