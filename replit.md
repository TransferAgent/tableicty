# tableicty - Transfer Agent SaaS Platform

## Overview

tableicty is a modern Transfer Agent platform designed for OTC/micro-cap companies to manage shareholder registries, stock transfers, and cap tables with full TAVS (Transfer Agent Verified Shares) compliance readiness. The platform aims to provide cloud-based transfer agent services with a blockchain-ready architecture, targeting OTCQX, OTCQB, and OTC Pink companies, as well as micro-cap and small-cap public companies.

## User Preferences

I prefer detailed explanations.
I want iterative development.
Ask before making major changes.
I like clean, readable code with good documentation.
Do not make changes to the `AWS_DEPLOYMENT_GUIDE.md` file.
Do not make changes to the `AWS_SECRETS_TEMPLATE.md` file.
Do not make changes to the `AWS_DEPLOYMENT_READY.md` file.

## System Architecture

The system is built on a Python 3.11/Django 4.2 LTS backend with Django REST Framework for API services. It uses PostgreSQL 15+ with `pgcrypto` for robust data storage and PII encryption.

**Core Features Implemented (MVP):**
- **Database Models:** Seven core models (Issuer, SecurityClass, Shareholder, Holding, Certificate, Transfer, AuditLog) handle all essential transfer agent functionalities, including PII encryption and immutable audit trails.
- **Admin Interface:** Full Django Admin configuration for all models with search, filter, and custom actions.
- **REST API:** Comprehensive CRUD endpoints for all models, including custom actions for cap table generation, share summaries, and transfer approvals/execution. API documentation is auto-generated using OpenAPI/Swagger.
- **Security:** Features include PII encryption, brute force protection (`django-axes`), strong password validation, CORS, and a two-factor authentication framework (`django-otp`).
- **Sample Data:** A management command (`seed_data`) creates realistic test data for development and testing.

**Project Structure:**
The project is organized into `config/` for Django settings, `apps/` containing `core/` (models, admin, business logic), `api/` (serializers, views, URLs), and `reports/` (sample data generator).

**Step 2: Shareholder Portal (IN PROGRESS - 60% Complete):**
- **React Frontend (✅ 100%):** Vite + TypeScript + Tailwind CSS + React Router setup complete
- **Authentication (✅ 100%):** JWT-based auth with login/register, token refresh, protected routes
- **Dashboard Layout (✅ 100%):** Navigation, routing, user menu, responsive layout
- **Portfolio Dashboard (✅ 100%):** Holdings display with summary cards and detailed table
- **Profile Page (✅ 100%):** Display shareholder information with masked tax ID
- **Remaining:** Charts (Recharts), transaction history, tax documents, certificate conversion, UX polish

**Future Enhancements (Planned):**
- **Admin Dashboard UI:** React-based professional admin console with data visualization.
- **Billing & Subscriptions:** Integration with Stripe for tiered pricing.
- **TAVS Integration:** Real-time share count reporting and compliance.
- **Advanced Features:** Corporate actions, automated notifications, blockchain support.

## External Dependencies

**Backend & Database:**
- **Python 3.11**
- **Django 4.2 LTS**
- **Django REST Framework 3.14**
- **PostgreSQL 15+**

**Security & Compliance:**
- `django-pgcrypto-fields`: Field-level encryption for PII.
- `django-otp`: Two-factor authentication framework.
- `django-axes`: Brute force protection.
- `django-environ`: Secure environment variable management.

**API & Documentation:**
- `drf-spectacular`: OpenAPI 3.0 schema generation.
- `django-filter`: Advanced filtering for API endpoints.
- `django-cors-headers`: CORS support.

**Development Tools:**
- `pytest`: Testing framework.
- `Faker`: Realistic sample data generation.
- `black`, `flake8`, `isort`: Code quality tools.

**AWS Deployment (Planned):**
- AWS App Runner
- AWS RDS PostgreSQL
- AWS S3
- AWS Secrets Manager
- AWS Route 53
- AWS CloudWatch
- `boto3`, `django-storages` (for AWS integration)