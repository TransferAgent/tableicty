# 📊 STEP 2: SHAREHOLDER PORTAL - BUILD PROGRESS

**Start Date:** November 17, 2025  
**Timeline:** 2-3 weeks (building systematically)  
**Approach:** Backend First → Frontend Second

---

## 🎯 PROJECT SCOPE

Building a shareholder-facing React portal with:
- JWT authentication (login/registration/password reset)
- Portfolio dashboard (view holdings with charts)
- Profile management (update contact info)
- Transaction history (view all account activity)
- Tax documents (download 1099s)
- Certificate conversion requests

---

## ✅ COMPLETED (Backend APIs - 50%)

### Phase 1: JWT Authentication Setup ✅
- ✅ Installed `djangorestframework-simplejwt==5.3.0`
- ✅ Added `rest_framework_simplejwt.token_blacklist` to INSTALLED_APPS
- ✅ Configured JWT token lifetimes:
  - Access token: 15 minutes
  - Refresh token: 7 days
  - Automatic rotation and blacklisting
- ✅ Created `apps/shareholder` Django app
- ✅ Ran migrations for token blacklist tables

### Phase 2: Authentication Endpoints ✅
- ✅ `POST /api/v1/shareholder/auth/register/` - Registration (links to existing Shareholder)
- ✅ `POST /api/v1/shareholder/auth/login/` - JWT login
- ✅ `POST /api/v1/shareholder/auth/logout/` - Logout with token blacklisting
- ✅ `POST /api/v1/shareholder/auth/refresh/` - Refresh access token
- ✅ `GET /api/v1/shareholder/auth/me/` - Get current user info

### Phase 3: Portfolio/Holdings API ✅
- ✅ `GET /api/v1/shareholder/holdings/` - All holdings with detailed info
- ✅ `GET /api/v1/shareholder/summary/` - Portfolio summary stats

### Phase 4: Transaction History API ✅
- ✅ `GET /api/v1/shareholder/transactions/` - All transfers (in/out)
- ✅ Filter support: transfer_type, status, year
- ✅ Direction indicator (IN/OUT based on context)
- ✅ Input validation prevents 500 errors

### Phase 5: Tax Documents API ✅
- ✅ `GET /api/v1/shareholder/tax-documents/` - Mock 1099-DIV records
- ✅ Generates documents for current + past 2 years
- ✅ Status tracking (AVAILABLE vs PENDING)
- ✅ Download URLs (placeholder for future implementation)

### Phase 6: Certificate Conversion API ✅
- ✅ `POST /api/v1/shareholder/certificate-conversion/` - Request conversions
- ✅ Supports CERT_TO_DRS and DRS_TO_CERT
- ✅ Certificate ownership validation
- ✅ Comprehensive audit logging with request tracking
- ✅ Returns request_id for tracking

### Phase 7: Profile Management API ✅
- ✅ `GET /api/v1/shareholder/profile/` - Get full profile
- ✅ `PATCH /api/v1/shareholder/profile/` - Update safe fields only
- ✅ Field-level change tracking in audit log
- ✅ Tax ID masking in responses

### Phase 8: Permissions & Security ✅
- ✅ `IsShareholderOwner` permission class
- ✅ Registration validates and links to existing Shareholder record
- ✅ Profile serializer masks tax IDs (`***-**-1234`)
- ✅ Profile serializer restricts updatable fields (address, phone, preferences only)
- ✅ Read-only fields enforced (name, tax ID, account type, etc.)

### Architect Review ✅
- ✅ Initial review: Fixed registration, token blacklist, profile protection
- ✅ Second review: Fixed certificate conversion crash, input validation, audit logging
- ✅ All 11 backend endpoints tested and working

---

## 🚧 IN PROGRESS

None - Ready for next phase decision

---

---

## 📝 UPCOMING TASKS

### Phase 2: Backend - Shareholder API Endpoints

**Portfolio & Holdings:**
- `GET /api/v1/shareholder/holdings/` - All holdings
- `GET /api/v1/shareholder/summary/` - Portfolio summary stats
- `GET /api/v1/shareholder/holdings/{id}/` - Single holding details

**Profile Management:**
- `GET /api/v1/shareholder/profile/` - Get current profile
- `PATCH /api/v1/shareholder/profile/` - Update profile
- `GET /api/v1/shareholder/profile/history/` - Change history (audit logs)

**Transactions:**
- `GET /api/v1/shareholder/transactions/` - Transaction history (paginated)
- `GET /api/v1/shareholder/transactions/{id}/` - Single transaction
- `GET /api/v1/shareholder/transactions/export/` - Export CSV/PDF

**Tax Documents:**
- `GET /api/v1/shareholder/tax-documents/` - List tax docs
- `GET /api/v1/shareholder/tax-documents/{id}/` - Single doc
- `GET /api/v1/shareholder/tax-documents/{id}/download/` - Download PDF

**Certificate Requests:**
- `POST /api/v1/shareholder/certificate-requests/` - Create request
- `GET /api/v1/shareholder/certificate-requests/` - List requests
- `GET /api/v1/shareholder/certificate-requests/{id}/` - Request details

### Phase 3: Backend - Permissions & Security

**Custom Permissions:**
- `IsShareholderOwner` - Shareholders can only access their own data
- Rate limiting for authentication endpoints
- Email verification for registration
- Password reset token generation

### Phase 4: Frontend - React App Setup

**Project Structure:**
```
frontend/
├── src/
│   ├── components/       # Reusable UI components
│   ├── pages/           # Page components
│   ├── services/        # API client
│   ├── hooks/           # Custom React hooks
│   ├── utils/           # Helper functions
│   ├── types/           # TypeScript interfaces
│   └── App.tsx
├── package.json
├── tailwind.config.js
└── tsconfig.json
```

**Tech Stack:**
- React 18 + TypeScript
- Tailwind CSS + shadcn/ui
- React Query (API data)
- Zustand (local state)
- React Router v6
- React Hook Form + Zod
- Axios
- Recharts

### Phase 5: Frontend - Authentication Flow

**Pages:**
- `/login` - Login page
- `/register` - Registration page (with invite token)
- `/forgot-password` - Password reset request
- `/reset-password/:token` - Password reset form
- Protected routes (require authentication)

**Components:**
- `LoginForm` - Email/password form
- `RegisterForm` - Registration form
- `ForgotPasswordForm` - Password reset request
- `ResetPasswordForm` - New password form
- `PrivateRoute` - Route protection wrapper

### Phase 6: Frontend - Portfolio Dashboard

**Page:** `/dashboard`

**Components:**
- `PortfolioSummary` - Total holdings, companies count
- `HoldingsTable` - Detailed holdings table
- `HoldingsChart` - Pie chart (Recharts)
- `CompanyCard` - Individual company holdings
- Filters (by company, security type, holding type)

### Phase 7: Frontend - Profile Management

**Page:** `/profile`

**Components:**
- `ProfileForm` - Editable profile fields
- `ProfileChangeHistory` - Audit log table
- Address, email, phone fields
- Read-only fields (name, tax ID masked)

### Phase 8: Frontend - Transaction History

**Page:** `/transactions`

**Components:**
- `TransactionTable` - Paginated transaction list
- `DateRangePicker` - Filter by date
- `TransactionFilters` - Type and issuer filters
- `ExportButton` - Download CSV/PDF

### Phase 9: Frontend - Tax Documents

**Page:** `/tax-documents`

**Components:**
- `TaxDocumentTable` - List of tax docs
- `YearFilter` - Filter by tax year
- `DownloadButton` - PDF download
- Empty state for new accounts

### Phase 10: Frontend - Certificate Requests

**Page:** `/certificate-requests`

**Components:**
- `CertificateRequestForm` - Create new request
- `RequestsList` - View existing requests
- `RequestStatusBadge` - Status indicator
- DRS ↔ Paper conversion options

### Phase 11: Integration & Testing

**Testing:**
- Backend API endpoints with pytest
- Frontend components with React Testing Library
- End-to-end authentication flow
- Permission testing (shareholders can't access others' data)
- CORS configuration verification

### Phase 12: Deployment Preparation

**Backend:**
- Update AWS deployment guide for new endpoints
- Add shareholder endpoints to API documentation

**Frontend:**
- Build for production (`npm run build`)
- Configure for S3 + CloudFront deployment
- Environment variables for API URL
- Create deployment guide for `portal.otcsimplified.com`

---

## 📅 ESTIMATED TIMELINE

| Phase | Task | Estimated Time | Status |
|-------|------|----------------|--------|
| 1 | JWT Authentication Setup | 2 hours | ✅ DONE |
| 2 | Authentication Endpoints | 4 hours | ✅ DONE |
| 3 | Shareholder Portfolio API | 4 hours | ✅ DONE |
| 4 | Transaction/Tax/Cert APIs | 1 day | ✅ DONE |
| 5 | Permissions & Security | 2 hours | ✅ DONE |
| 6 | Backend Testing & Fixes | 2 hours | ✅ DONE |
| 7 | React App Setup | 2 hours | 📝 PENDING |
| 8 | Authentication UI | 1 day | 📝 PENDING |
| 9 | Portfolio Dashboard UI | 2 days | 📝 PENDING |
| 10 | Profile Management UI | 1 day | 📝 PENDING |
| 11 | Transaction History UI | 1 day | 📝 PENDING |
| 12 | Tax Documents UI | 1 day | 📝 PENDING |
| 13 | Certificate Requests UI | 1 day | 📝 PENDING |
| 14 | Integration & Testing | 2 days | 📝 PENDING |
| 15 | Deployment Prep | 1 day | 📝 PENDING |
| **TOTAL** | | **2-3 weeks** | **50% COMPLETE** |

---

## 🔄 CURRENT FOCUS

**Now building:** JWT authentication endpoints in `apps/shareholder/`

**Next:** Shareholder-specific API views and permissions

---

## 📊 DEPLOYMENT ARCHITECTURE

```
┌─────────────────────────────────────────────────┐
│                                                 │
│  Shareholder Portal (React)                    │
│  https://portal.otcsimplified.com              │
│  (AWS S3 + CloudFront)                          │
│                                                 │
└─────────────────┬───────────────────────────────┘
                  │
                  │ HTTPS (JWT Bearer tokens)
                  │
                  ↓
┌─────────────────────────────────────────────────┐
│                                                 │
│  Django Backend API                            │
│  https://staging.otcsimplified.com/api/v1/     │
│  (AWS App Runner)                               │
│                                                 │
│  Endpoints:                                     │
│  ├── /admin/*         (Admin only)             │
│  ├── /api/v1/issuers/*    (Admin API)          │
│  ├── /api/v1/shareholders/* (Admin API)        │
│  └── /api/v1/shareholder/* (Shareholder Portal)│
│                                                 │
└─────────────────┬───────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────────┐
│                                                 │
│  PostgreSQL Database (RDS)                     │
│  - Encrypted at rest                            │
│  - Automated backups                            │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 🔐 SECURITY FEATURES

**Authentication:**
- ✅ JWT with 15-minute access tokens
- ✅ 7-day refresh tokens with rotation
- ✅ Token blacklisting after rotation
- ✅ HTTPS only (enforced in production)
- ✅ httpOnly cookies for token storage

**Authorization:**
- 🚧 Custom permissions (shareholders see only their data)
- 🚧 Rate limiting on auth endpoints
- 🚧 Failed login tracking (5 attempts = 30-min lock)

**Data Protection:**
- ✅ Tax IDs encrypted in database (pgcrypto)
- ✅ CORS restricted to known origins
- ✅ CSRF protection
- ✅ Audit logging for all changes

---

## 📝 NOTES

**Design Decisions:**
- JWT preferred over session-based auth for React SPA
- Shareholder API endpoints separate from admin API (`/api/v1/shareholder/*` vs `/api/v1/shareholders/*`)
- shadcn/ui for consistent, accessible UI components
- React Query for efficient API data caching
- Mock tax document data for Step 2 (actual generation in Step 7)

**CORS Configuration:**
- Development: `http://localhost:3000` (React dev server)
- Production: `https://portal.otcsimplified.com`

---

**Last Updated:** November 17, 2025 - 5:30 PM  
**Status:** Active Development - Phase 1 Complete
