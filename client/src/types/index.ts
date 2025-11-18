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
  transfer_date: string;
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
  invite_token: string;
}

export interface AuthResponse {
  access: string;
  refresh: string;
  user?: User;
  message?: string;
}

export interface CertificateConversionRequest {
  certificate_number: string;
  issuer_id: string;
  conversion_type: 'CERT_TO_DRS' | 'DRS_TO_CERT';
  notes?: string;
}

export interface CertificateConversionSubmission {
  holding_id: number;
  conversion_type: 'CERT_TO_DRS' | 'DRS_TO_CERT';
  share_quantity: number;
  mailing_address?: string;
}
