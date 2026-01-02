import type { Holding, Transfer, TaxDocument, CertificateRequest, Shareholder } from '../types';

export const mockShareholder: Shareholder = {
  id: '1',
  email: 'test@example.com',
  account_type: 'INDIVIDUAL',
  first_name: 'John',
  middle_name: '',
  last_name: 'Doe',
  entity_name: null,
  tax_id_masked: '***-**-1234',
  tax_id_type: 'SSN',
  address_line1: '123 Main St',
  address_line2: 'Apt 4',
  city: 'New York',
  state: 'NY',
  zip_code: '10001',
  country: 'USA',
  phone: '555-123-4567',
  is_accredited_investor: false,
  email_alerts_enabled: true,
  paper_statements_enabled: false,
};

export const mockHoldings: Holding[] = [
  {
    id: '1',
    issuer: {
      name: 'Green Energy Corp',
      ticker: 'GREC',
      otc_tier: 'OTCQB',
    },
    security_class: {
      type: 'Common Stock',
      designation: 'Class A',
    },
    share_quantity: '50000',
    acquisition_date: '2023-06-15',
    holding_type: 'BOOK',
    percentage_ownership: 2.5,
  },
  {
    id: '2',
    issuer: {
      name: 'TechStart Inc',
      ticker: 'TECH',
      otc_tier: 'OTCQX',
    },
    security_class: {
      type: 'Preferred Stock',
      designation: 'Series A',
    },
    share_quantity: '25000',
    acquisition_date: '2023-09-20',
    holding_type: 'CERTIFICATE',
    percentage_ownership: 5.0,
  },
];

export const mockTransfers: Transfer[] = [
  {
    id: '1',
    issuer_name: 'Green Energy Corp',
    issuer_ticker: 'GREC',
    security_type: 'Common Stock',
    security_designation: 'Class A',
    from_shareholder_name: 'John Doe',
    to_shareholder_name: 'Jane Smith',
    share_quantity: '100',
    transfer_price: '10.50',
    executed_date: '2024-01-15',
    transfer_type: 'SALE',
    status: 'COMPLETED',
    direction: 'OUT',
    notes: 'Sale to investor',
    created_at: '2024-01-10T00:00:00Z',
  },
  {
    id: '2',
    issuer_name: 'TechStart Inc',
    issuer_ticker: 'TECH',
    security_type: 'Preferred Stock',
    security_designation: 'Series A',
    from_shareholder_name: 'John Doe',
    to_shareholder_name: 'Bob Johnson',
    share_quantity: '50',
    transfer_price: null,
    executed_date: '2024-01-20',
    transfer_type: 'GIFT',
    status: 'PENDING',
    direction: 'OUT',
    notes: 'Gift transfer',
    created_at: '2024-01-18T00:00:00Z',
  },
];

export const mockTaxDocuments: TaxDocument[] = [
  {
    id: '1',
    document_type: '1099-DIV',
    tax_year: 2024,
    issuer_name: 'Green Energy Corp',
    issuer_ticker: 'GREC',
    generated_date: '2024-01-31',
    status: 'AVAILABLE',
    download_url: '/api/tax-documents/1/download/',
  },
  {
    id: '2',
    document_type: '1099-B',
    tax_year: 2023,
    issuer_name: 'TechStart Inc',
    issuer_ticker: 'TECH',
    generated_date: '2023-01-31',
    status: 'AVAILABLE',
    download_url: '/api/tax-documents/2/download/',
  },
];

export const mockCertificateRequests: CertificateRequest[] = [
  {
    id: '1',
    conversion_type: 'CERT_TO_DRS',
    share_quantity: 100,
    status: 'PENDING',
    mailing_address: '123 Main St, New York, NY 10001',
    issuer_name: 'Green Energy Corp',
    security_type: 'Common Stock',
    created_at: '2024-01-15T00:00:00Z',
    processed_at: null,
    rejection_reason: '',
  },
  {
    id: '2',
    conversion_type: 'DRS_TO_CERT',
    share_quantity: 50,
    status: 'COMPLETED',
    mailing_address: '456 Oak Ave, Brooklyn, NY 11201',
    issuer_name: 'TechStart Inc',
    security_type: 'Common Stock',
    created_at: '2024-01-01T00:00:00Z',
    processed_at: '2024-01-05T00:00:00Z',
    rejection_reason: '',
  },
];

export const mockPortfolioSummary = {
  total_companies: 3,
  total_shares: 75000,
  total_holdings: 2,
};
