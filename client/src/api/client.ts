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
  MFAStatus,
  MFASetupResponse,
  MFAVerifyResponse,
  CurrentTenantResponse,
  TenantRegistrationData,
  Tenant,
  TenantInvitation,
  SubscriptionPlan,
  BillingStatus,
  AdminShareholder,
  AdminSecurityClass,
  AdminHolding,
  AdminIssuer,
  PaginatedResponse,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL 
  ? `${import.meta.env.VITE_API_BASE_URL}/api/v1/shareholder`
  : '/api/v1/shareholder';

class APIClient {
  private client: AxiosInstance;
  private adminClient!: AxiosInstance;
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

  async submitCertificateConversion(data: { holding_id: string; conversion_type: string; share_quantity: number; mailing_address?: string }): Promise<any> {
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

  async getMFAStatus(): Promise<MFAStatus> {
    const response = await this.client.get('/auth/mfa/status/');
    return response.data;
  }

  async setupMFA(): Promise<MFASetupResponse> {
    const response = await this.client.post('/auth/mfa/setup/', {});
    return response.data;
  }

  async verifyMFASetup(code: string): Promise<MFAVerifyResponse> {
    const response = await this.client.post('/auth/mfa/verify-setup/', { code });
    return response.data;
  }

  async verifyMFALogin(code: string): Promise<MFAVerifyResponse> {
    const response = await this.client.post('/auth/mfa/verify/', { code });
    if (response.data.access) {
      this.setAccessToken(response.data.access);
    }
    return response.data;
  }

  async disableMFA(password: string, code: string): Promise<MFAVerifyResponse> {
    const response = await this.client.post('/auth/mfa/disable/', { password, code });
    if (response.data.access) {
      this.setAccessToken(response.data.access);
    }
    return response.data;
  }

  async getBackupCodes(): Promise<{ message: string; backup_codes: string[] }> {
    const response = await this.client.get('/auth/mfa/backup-codes/');
    return response.data;
  }

  async getCurrentTenant(): Promise<CurrentTenantResponse> {
    const tenantBaseUrl = import.meta.env.VITE_API_BASE_URL 
      ? `${import.meta.env.VITE_API_BASE_URL}/api/v1/tenant`
      : '/api/v1/tenant';
    const response = await axios.get(`${tenantBaseUrl}/current/`, {
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json',
        ...(this.accessToken ? { Authorization: `Bearer ${this.accessToken}` } : {}),
      },
    });
    return response.data;
  }

  async registerTenant(data: TenantRegistrationData): Promise<{ tenant: Tenant; user: User; access: string }> {
    const tenantBaseUrl = import.meta.env.VITE_API_BASE_URL 
      ? `${import.meta.env.VITE_API_BASE_URL}/api/v1/tenant`
      : '/api/v1/tenant';
    
    // Transform frontend field names to backend expected names
    const backendData = {
      company_name: data.tenant_name,
      company_slug: data.tenant_slug,
      email: data.admin_email,
      password: data.admin_password,
      first_name: data.admin_first_name,
      last_name: data.admin_last_name,
    };
    
    const response = await axios.post(`${tenantBaseUrl}/register/`, backendData, {
      withCredentials: true,
      headers: { 'Content-Type': 'application/json' },
    });
    if (response.data.access) {
      this.setAccessToken(response.data.access);
    }
    return response.data;
  }

  async getSubscriptionPlans(): Promise<SubscriptionPlan[]> {
    const tenantBaseUrl = import.meta.env.VITE_API_BASE_URL 
      ? `${import.meta.env.VITE_API_BASE_URL}/api/v1/tenant`
      : '/api/v1/tenant';
    const response = await axios.get(`${tenantBaseUrl}/subscription-plans/`, {
      headers: { 'Content-Type': 'application/json' },
    });
    return response.data;
  }

  async getTenantSettings(): Promise<Tenant> {
    const tenantBaseUrl = import.meta.env.VITE_API_BASE_URL 
      ? `${import.meta.env.VITE_API_BASE_URL}/api/v1/tenant`
      : '/api/v1/tenant';
    const response = await axios.get(`${tenantBaseUrl}/settings/`, {
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json',
        ...(this.accessToken ? { Authorization: `Bearer ${this.accessToken}` } : {}),
      },
    });
    return response.data;
  }

  async updateTenantSettings(data: Partial<Tenant>): Promise<Tenant> {
    const tenantBaseUrl = import.meta.env.VITE_API_BASE_URL 
      ? `${import.meta.env.VITE_API_BASE_URL}/api/v1/tenant`
      : '/api/v1/tenant';
    const response = await axios.put(`${tenantBaseUrl}/settings/`, data, {
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json',
        ...(this.accessToken ? { Authorization: `Bearer ${this.accessToken}` } : {}),
      },
    });
    return response.data;
  }

  async getTenantMembers(): Promise<{ id: string; user_email: string; role: string; joined_at: string }[]> {
    const tenantBaseUrl = import.meta.env.VITE_API_BASE_URL 
      ? `${import.meta.env.VITE_API_BASE_URL}/api/v1/tenant`
      : '/api/v1/tenant';
    const response = await axios.get(`${tenantBaseUrl}/members/`, {
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json',
        ...(this.accessToken ? { Authorization: `Bearer ${this.accessToken}` } : {}),
      },
    });
    return response.data;
  }

  async createInvitation(email: string, role: string): Promise<TenantInvitation> {
    const tenantBaseUrl = import.meta.env.VITE_API_BASE_URL 
      ? `${import.meta.env.VITE_API_BASE_URL}/api/v1/tenant`
      : '/api/v1/tenant';
    const response = await axios.post(`${tenantBaseUrl}/invitations/`, { email, role }, {
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json',
        ...(this.accessToken ? { Authorization: `Bearer ${this.accessToken}` } : {}),
      },
    });
    return response.data;
  }

  async getBillingStatus(): Promise<BillingStatus> {
    const tenantBaseUrl = import.meta.env.VITE_API_BASE_URL 
      ? `${import.meta.env.VITE_API_BASE_URL}/api/v1/tenant`
      : '/api/v1/tenant';
    const response = await axios.get(`${tenantBaseUrl}/billing/`, {
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json',
        ...(this.accessToken ? { Authorization: `Bearer ${this.accessToken}` } : {}),
      },
    });
    return response.data;
  }

  async createCheckoutSession(planId: string, billingCycle: 'monthly' | 'yearly'): Promise<{ session_id: string; url: string }> {
    const tenantBaseUrl = import.meta.env.VITE_API_BASE_URL 
      ? `${import.meta.env.VITE_API_BASE_URL}/api/v1/tenant`
      : '/api/v1/tenant';
    const response = await axios.post(`${tenantBaseUrl}/billing/checkout/`, 
      { plan_id: planId, billing_cycle: billingCycle },
      {
        withCredentials: true,
        headers: {
          'Content-Type': 'application/json',
          ...(this.accessToken ? { Authorization: `Bearer ${this.accessToken}` } : {}),
        },
      }
    );
    return response.data;
  }

  async createBillingPortalSession(): Promise<{ url: string }> {
    const tenantBaseUrl = import.meta.env.VITE_API_BASE_URL 
      ? `${import.meta.env.VITE_API_BASE_URL}/api/v1/tenant`
      : '/api/v1/tenant';
    const response = await axios.post(`${tenantBaseUrl}/billing/portal/`, {}, {
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json',
        ...(this.accessToken ? { Authorization: `Bearer ${this.accessToken}` } : {}),
      },
    });
    return response.data;
  }

  async cancelSubscription(atPeriodEnd: boolean = true): Promise<{ status: string; at_period_end: boolean }> {
    const tenantBaseUrl = import.meta.env.VITE_API_BASE_URL 
      ? `${import.meta.env.VITE_API_BASE_URL}/api/v1/tenant`
      : '/api/v1/tenant';
    const response = await axios.post(`${tenantBaseUrl}/billing/cancel/`, 
      { at_period_end: atPeriodEnd },
      {
        withCredentials: true,
        headers: {
          'Content-Type': 'application/json',
          ...(this.accessToken ? { Authorization: `Bearer ${this.accessToken}` } : {}),
        },
      }
    );
    return response.data;
  }

  private initAdminClient() {
    const adminBaseUrl = import.meta.env.VITE_API_BASE_URL 
      ? `${import.meta.env.VITE_API_BASE_URL}/api/v1`
      : '/api/v1';
    
    this.adminClient = axios.create({
      baseURL: adminBaseUrl,
      withCredentials: true,
      headers: { 'Content-Type': 'application/json' },
    });

    this.adminClient.interceptors.request.use((config) => {
      const token = this.accessToken || sessionStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    this.adminClient.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as any;
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;
          try {
            const newAccessToken = await this.refreshAccessToken();
            if (newAccessToken && originalRequest) {
              originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
              return this.adminClient(originalRequest);
            } else {
              this.logout();
              window.location.href = '/login';
              return Promise.reject(new Error('Session expired'));
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

  async getAdminShareholders(params?: { search?: string; page?: number }): Promise<PaginatedResponse<AdminShareholder>> {
    if (!this.adminClient) this.initAdminClient();
    const response = await this.adminClient.get('/shareholders/', { params });
    return response.data;
  }

  async getAdminShareholder(id: string): Promise<AdminShareholder> {
    if (!this.adminClient) this.initAdminClient();
    const response = await this.adminClient.get(`/shareholders/${id}/`);
    return response.data;
  }

  async createAdminShareholder(data: Partial<AdminShareholder>): Promise<AdminShareholder> {
    if (!this.adminClient) this.initAdminClient();
    const response = await this.adminClient.post('/shareholders/', data);
    return response.data;
  }

  async updateAdminShareholder(id: string, data: Partial<AdminShareholder>): Promise<AdminShareholder> {
    if (!this.adminClient) this.initAdminClient();
    const response = await this.adminClient.patch(`/shareholders/${id}/`, data);
    return response.data;
  }

  async deleteAdminShareholder(id: string): Promise<void> {
    if (!this.adminClient) this.initAdminClient();
    await this.adminClient.delete(`/shareholders/${id}/`);
  }

  async getAdminHoldings(params?: { shareholder?: string; page?: number }): Promise<PaginatedResponse<AdminHolding>> {
    if (!this.adminClient) this.initAdminClient();
    const response = await this.adminClient.get('/holdings/', { params });
    return response.data;
  }

  async createAdminHolding(data: Partial<AdminHolding>): Promise<AdminHolding> {
    if (!this.adminClient) this.initAdminClient();
    const response = await this.adminClient.post('/holdings/', data);
    return response.data;
  }

  async updateAdminHolding(id: string, data: Partial<AdminHolding>): Promise<AdminHolding> {
    if (!this.adminClient) this.initAdminClient();
    const response = await this.adminClient.patch(`/holdings/${id}/`, data);
    return response.data;
  }

  async getAdminSecurityClasses(): Promise<PaginatedResponse<AdminSecurityClass>> {
    if (!this.adminClient) this.initAdminClient();
    const response = await this.adminClient.get('/security-classes/');
    return response.data;
  }

  async createAdminSecurityClass(data: Partial<AdminSecurityClass>): Promise<AdminSecurityClass> {
    if (!this.adminClient) this.initAdminClient();
    const response = await this.adminClient.post('/security-classes/', data);
    return response.data;
  }

  async getAdminIssuers(): Promise<PaginatedResponse<AdminIssuer>> {
    if (!this.adminClient) this.initAdminClient();
    const response = await this.adminClient.get('/issuers/');
    return response.data;
  }

  async createAdminIssuer(data: Partial<AdminIssuer>): Promise<AdminIssuer> {
    if (!this.adminClient) this.initAdminClient();
    const response = await this.adminClient.post('/issuers/', data);
    return response.data;
  }

  async getCapTable(issuerId: string): Promise<{ shareholders: { name: string; shares: string; percentage: number }[]; total_shares: string }> {
    if (!this.adminClient) this.initAdminClient();
    const response = await this.adminClient.get(`/issuers/${issuerId}/cap_table/`);
    return response.data;
  }

  async inviteShareholder(shareholderId: string, holdingId?: string): Promise<{ success: boolean; message?: string; error?: string; expires_at?: string }> {
    if (!this.adminClient) this.initAdminClient();
    const response = await this.adminClient.post('/tenant/email/invite-shareholder/', {
      shareholder_id: shareholderId,
      holding_id: holdingId,
    });
    return response.data;
  }
}

export const apiClient = new APIClient();
