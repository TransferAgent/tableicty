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
  CertificateConversionRequest,
} from '../types';

const API_BASE_URL = '/api/v1/shareholders';

class APIClient {
  private client: AxiosInstance;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
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

  setTokens(access: string, refresh: string) {
    this.accessToken = access;
    this.refreshToken = refresh;
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
  }

  getTokens() {
    return {
      access: this.accessToken || localStorage.getItem('access_token'),
      refresh: this.refreshToken || localStorage.getItem('refresh_token'),
    };
  }

  loadTokens() {
    this.accessToken = localStorage.getItem('access_token');
    this.refreshToken = localStorage.getItem('refresh_token');
  }

  clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  async register(data: RegisterData): Promise<AuthResponse> {
    const response = await this.client.post('/auth/register/', data);
    const authData = response.data;
    if (authData.access && authData.refresh) {
      this.setTokens(authData.access, authData.refresh);
    }
    return authData;
  }

  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await this.client.post('/auth/login/', credentials);
    const authData = response.data;
    this.setTokens(authData.access, authData.refresh);
    return authData;
  }

  async logout(): Promise<void> {
    try {
      if (this.refreshToken) {
        await this.client.post('/auth/logout/', { refresh: this.refreshToken });
      }
    } finally {
      this.clearTokens();
    }
  }

  async refreshAccessToken(): Promise<string | null> {
    if (!this.refreshToken) {
      return null;
    }

    try {
      const response = await this.client.post('/auth/refresh/', {
        refresh: this.refreshToken,
      });
      const { access } = response.data;
      this.accessToken = access;
      localStorage.setItem('access_token', access);
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
  }): Promise<{ count: number; transfers: Transfer[] }> {
    const response = await this.client.get('/transactions/', { params });
    return response.data;
  }

  async getTaxDocuments(): Promise<{ count: number; documents: TaxDocument[] }> {
    const response = await this.client.get('/tax-documents/');
    return response.data;
  }

  async submitCertificateConversion(data: CertificateConversionRequest): Promise<any> {
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
