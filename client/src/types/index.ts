export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  shareholder: Shareholder;
}

export interface Shareholder {
  id: string;
  email: string;
  account_type: string;
  first_name: string;
  middle_name: string;
  last_name: string;
  entity_name: string | null;
  tax_id_masked: string;
  tax_id_type: string;
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  zip_code: string;
  country: string;
  phone: string;
  is_accredited_investor: boolean;
  email_alerts_enabled: boolean;
  paper_statements_enabled: boolean;
}

export interface Holding {
  id: string;
  issuer: {
    name: string;
    ticker: string;
    otc_tier: string;
  };
  security_class: {
    type: string;
    designation: string;
  };
  share_quantity: string;
  acquisition_date: string;
  holding_type: string;
  percentage_ownership: number;
}

export interface Transfer {
  id: string;
  issuer_name: string;
  issuer_ticker: string;
  security_type: string;
  security_designation: string;
  from_shareholder_name: string;
  to_shareholder_name: string;
  share_quantity: string;
  transfer_price: string | null;
  executed_date: string;
  transfer_type: string;
  status: string;
  direction: 'IN' | 'OUT' | null;
  notes: string;
  created_at: string;
}

export interface TaxDocument {
  id: string;
  document_type: string;
  tax_year: number;
  issuer_name: string;
  issuer_ticker: string;
  generated_date: string;
  status: string;
  download_url: string;
}

export interface PortfolioSummary {
  total_companies: number;
  total_shares: number;
  total_holdings: number;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  password_confirm: string;
  invite_token?: string;
  invitation_token?: string;
}

export interface AuthResponse {
  access: string;
  user?: User;
  message?: string;
}

export interface CertificateConversionSubmission {
  holding_id: string;
  conversion_type: 'CERT_TO_DRS' | 'DRS_TO_CERT';
  share_quantity: number;
  mailing_address?: string;
}

export interface CertificateRequest {
  id: string;
  holding_id: string;
  conversion_type: string;
  share_quantity: number;
  status: string;
  requested_date: string;
  mailing_address: string;
}

export interface MFAStatus {
  mfa_enabled: boolean;
  mfa_pending_setup: boolean;
  device_count: number;
}

export interface MFASetupResponse {
  message: string;
  provisioning_uri: string;
  device_name: string;
  qr_code_base64?: string;
}

export interface MFAVerifyResponse {
  message: string;
  mfa_enabled?: boolean;
  mfa_verified?: boolean;
  access?: string;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  primary_email: string;
  phone: string;
  status: 'active' | 'suspended' | 'pending';
  logo_url: string | null;
  created_at: string;
}

export interface TenantMembership {
  tenant: Tenant;
  role: 'PLATFORM_ADMIN' | 'TENANT_ADMIN' | 'TENANT_STAFF' | 'SHAREHOLDER';
  joined_at: string;
}

export interface CurrentTenantResponse {
  current_tenant: Tenant | null;
  current_role: string | null;
  available_tenants: TenantMembership[];
}

export interface SubscriptionPlan {
  id: string;
  name: string;
  tier: 'STARTER' | 'GROWTH' | 'ENTERPRISE';
  price_monthly: string;
  price_yearly: string;
  max_shareholders: number;
  max_transfers_per_month: number;
  max_users: number;
}

export interface BillingStatus {
  stripe_configured: boolean;
  stripe_publishable_key: string | null;
  subscription: {
    id: string;
    status: string;
    billing_cycle: string;
    plan: SubscriptionPlan | null;
    trial_end: string | null;
    current_period_end: string | null;
  } | null;
}

export interface TenantRegistrationData {
  tenant_name: string;
  tenant_slug: string;
  admin_email: string;
  admin_password: string;
  admin_first_name: string;
  admin_last_name: string;
  plan_tier?: string;
}

export interface TenantInvitation {
  id: string;
  email: string;
  role: string;
  token: string;
  expires_at: string;
  accepted: boolean;
}

export interface AdminShareholder {
  id: string;
  tenant: string;
  user: number | null;
  account_type: 'INDIVIDUAL' | 'JOINT' | 'TRUST' | 'IRA' | 'ENTITY' | 'ESTATE';
  first_name: string;
  middle_name: string;
  last_name: string;
  entity_name: string;
  email: string;
  phone: string;
  tax_id_type: 'SSN' | 'EIN' | 'ITIN' | 'FOREIGN';
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  zip_code: string;
  country: string;
  is_accredited_investor: boolean;
  is_insider: boolean;
  is_affiliate: boolean;
  is_restricted: boolean;
  email_alerts_enabled: boolean;
  paper_statements_enabled: boolean;
  created_at: string;
  updated_at: string;
  full_name: string;
}

export interface AdminSecurityClass {
  id: string;
  tenant: string;
  issuer: string;
  issuer_name: string;
  class_designation: string;
  security_type: 'COMMON' | 'PREFERRED' | 'WARRANT' | 'OPTION' | 'CONVERTIBLE' | 'CONVERTIBLE_NOTE' | 'TOKEN' | 'NFT_SECURITY';
  shares_authorized: string;
  par_value: string;
  voting_rights: boolean;
  votes_per_share: string;
  created_at: string;
  updated_at: string;
}

export interface AdminHolding {
  id: string;
  tenant: string;
  shareholder: string;
  shareholder_name: string;
  issuer: string;
  issuer_name: string;
  security_class: string;
  security_class_name: string;
  share_quantity: string;
  cost_basis: string;
  cost_basis_per_share: string;
  acquisition_date: string;
  acquisition_type: 'PURCHASE' | 'GIFT' | 'INHERITANCE' | 'STOCK_SPLIT' | 'DIVIDEND' | 'TRANSFER' | 'ISSUANCE';
  holding_type: 'CERTIFICATE' | 'DRS' | 'BOOK_ENTRY';
  is_restricted: boolean;
  restriction_end_date: string | null;
  legend_code: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface AdminIssuer {
  id: string;
  tenant: string;
  company_name: string;
  legal_name: string;
  ticker_symbol: string;
  cusip: string;
  cik: string;
  ein: string;
  state_of_incorporation: string;
  date_of_incorporation: string | null;
  fiscal_year_end: string;
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  zip_code: string;
  country: string;
  phone: string;
  website: string;
  otc_tier: string;
  total_authorized_shares: string;
  tavs_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
