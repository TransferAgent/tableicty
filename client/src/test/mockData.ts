import { Holding, Transfer, TaxDocument, CertificateRequest, Shareholder } from '../types';

export const mockShareholder: Shareholder = {
  id: 1,
  email: 'test@example.com',
  first_name: 'John',
  last_name: 'Doe',
  address_line1: '123 Main St',
  address_line2: 'Apt 4',
  city: 'New York',
  state: 'NY',
  postal_code: '10001',
  country: 'USA',
  phone: '555-123-4567',
  tax_id: '***-**-1234',
  date_of_birth: '1980-01-15',
  created_at: '2024-01-01T00:00:00Z',
};

export const mockHoldings: Holding[] = [
  {
    id: 1,
    shareholder: 1,
    security_class: 1,
    issuer_name: 'Acme Corp',
    security_class_name: 'Common Stock',
    total_shares: 1000,
    available_shares: 1000,
    restricted_shares: 0,
    certificate_count: 1,
    last_updated: '2024-01-15T10:00:00Z',
  },
  {
    id: 2,
    shareholder: 1,
    security_class: 2,
    issuer_name: 'TechStart Inc',
    security_class_name: 'Preferred Stock',
    total_shares: 500,
    available_shares: 500,
    restricted_shares: 0,
    certificate_count: 1,
    last_updated: '2024-01-20T10:00:00Z',
  },
];

export const mockTransfers: Transfer[] = [
  {
    id: 1,
    security_class: 1,
    from_shareholder: 1,
    to_shareholder: 2,
    shares: 100,
    transfer_type: 'SALE',
    status: 'COMPLETED',
    price_per_share: '10.50',
    total_value: '1050.00',
    requested_date: '2024-01-10T00:00:00Z',
    executed_date: '2024-01-15T00:00:00Z',
    notes: 'Sale to investor',
    issuer_name: 'Acme Corp',
    security_class_name: 'Common Stock',
    from_shareholder_name: 'John Doe',
    to_shareholder_name: 'Jane Smith',
  },
  {
    id: 2,
    security_class: 2,
    from_shareholder: 1,
    to_shareholder: null,
    shares: 50,
    transfer_type: 'GIFT',
    status: 'PENDING',
    price_per_share: null,
    total_value: null,
    requested_date: '2024-01-20T00:00:00Z',
    executed_date: null,
    notes: 'Gift transfer',
    issuer_name: 'TechStart Inc',
    security_class_name: 'Preferred Stock',
    from_shareholder_name: 'John Doe',
    to_shareholder_name: null,
  },
];

export const mockTaxDocuments: TaxDocument[] = [
  {
    id: 1,
    shareholder: 1,
    tax_year: 2024,
    document_type: '1099-DIV',
    status: 'AVAILABLE',
    generated_date: '2024-01-31T00:00:00Z',
    file_path: '/documents/2024-1099-div.pdf',
  },
  {
    id: 2,
    shareholder: 1,
    tax_year: 2023,
    document_type: '1099-B',
    status: 'AVAILABLE',
    generated_date: '2023-01-31T00:00:00Z',
    file_path: '/documents/2023-1099-b.pdf',
  },
];

export const mockCertificateRequests: CertificateRequest[] = [
  {
    id: 1,
    shareholder: 1,
    certificate_number: 'CERT-001',
    shares_to_convert: 100,
    status: 'PENDING',
    requested_date: '2024-01-15T10:00:00Z',
    completed_date: null,
    issuer_name: 'Acme Corp',
    security_class_name: 'Common Stock',
    notes: 'Converting physical certificate to book entry',
  },
  {
    id: 2,
    shareholder: 1,
    certificate_number: 'CERT-002',
    shares_to_convert: 50,
    status: 'COMPLETED',
    requested_date: '2024-01-01T10:00:00Z',
    completed_date: '2024-01-05T10:00:00Z',
    issuer_name: 'TechStart Inc',
    security_class_name: 'Preferred Stock',
    notes: null,
  },
];

export const mockPortfolioSummary = {
  total_value: 15750.0,
  total_positions: 2,
  total_shares: 1500,
  total_companies: 2,
};
