# AWS Deployment Checklist - tableicty Transfer Agent Platform

**Deployment Target Date**: November 21-23, 2025  
**Production Domain**: tableicty.com  
**Current Status**: Step 2 Complete - Ready for Production Deployment

---

## Prerequisites

### AWS Account & Permissions

- [ ] AWS account created and verified
- [ ] IAM user created with appropriate permissions:
  - [ ] AWS App Runner (full access)
  - [ ] Amazon RDS (full access)
  - [ ] Amazon S3 (full access)
  - [ ] Amazon CloudFront (full access)
  - [ ] AWS Certificate Manager (full access)
  - [ ] Amazon Route 53 (full access or DNS delegation)
  - [ ] AWS Secrets Manager (full access)
  - [ ] AWS CloudWatch (read/write logs)
- [ ] AWS CLI installed and configured locally
- [ ] MFA enabled on AWS account (security best practice)

### Domain & SSL

- [ ] Domain name registered: `tableicty.com`
  - Option 1: Register with Route 53 (recommended for easy integration)
  - Option 2: Transfer existing domain to Route 53
  - Option 3: Use external registrar with DNS delegation
- [ ] SSL certificate requested via AWS Certificate Manager
  - [ ] Certificate for: `*.tableicty.com` (wildcard certificate)
  - [ ] Certificate validated (DNS or email validation)
  - [ ] Certificate status: **Issued**

### Development Environment Verification

- [ ] All tests passing locally:
  - [ ] Backend: 40/40 tests passing
  - [ ] Frontend: 46/46 tests passing
  - [ ] Total: 86/86 tests (100% pass rate)
- [ ] Code committed to GitHub main branch
- [ ] No uncommitted changes in working directory
- [ ] All environment variables documented
- [ ] Dependencies up-to-date (no security vulnerabilities)

---

## Backend Deployment (AWS App Runner)

### 1. Database Setup (Amazon RDS PostgreSQL)

- [ ] Create RDS PostgreSQL instance:
  - [ ] Engine: PostgreSQL 15.x
  - [ ] Instance class: `db.t3.micro` (development) or `db.t3.small` (production)
  - [ ] Storage: 20 GB SSD (General Purpose - gp3)
  - [ ] Multi-AZ: **Yes** (for production high availability)
  - [ ] VPC: Default VPC or create dedicated VPC
  - [ ] Security group: Allow inbound on port 5432 from App Runner service
  - [ ] Public accessibility: **No** (App Runner connects via VPC)
  - [ ] Database name: `tableicty_production`
  - [ ] Master username: `tableicty_admin`
  - [ ] Master password: **Generated and stored in Secrets Manager**

- [ ] Enable pgcrypto extension:
  ```sql
  -- Connect to the database as master user
  psql -h <rds-endpoint> -U tableicty_admin -d tableicty_production
  
  -- Enable pgcrypto extension
  CREATE EXTENSION IF NOT EXISTS pgcrypto;
  
  -- Verify extension is installed
  \dx
  ```

- [ ] Create read-only replica (optional, for production):
  - [ ] Same instance class as primary
  - [ ] Same VPC and security group configuration
  - [ ] Use for reporting queries (future enhancement)

- [ ] Configure automated backups:
  - [ ] Backup retention: 7 days minimum (30 days recommended)
  - [ ] Backup window: During low-traffic hours (e.g., 3:00 AM UTC)
  - [ ] Enable automated minor version upgrades

- [ ] Record database connection details:
  - [ ] RDS Endpoint: `_______________________________`
  - [ ] Port: `5432`
  - [ ] Database name: `tableicty_production`
  - [ ] Store in AWS Secrets Manager (see Environment Variables section)

### 2. AWS Secrets Manager Setup

- [ ] Create secret: `tableicty/production/backend`
  - [ ] Secret type: Other type of secret (Key/value pairs)
  - [ ] Add key-value pairs (see Environment Variables section below)
  - [ ] Encryption key: Use default AWS managed key or create custom KMS key
  - [ ] Automatic rotation: Disabled initially (enable for SECRET_KEY after deployment)

- [ ] Create IAM policy for App Runner to access secrets:
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ],
        "Resource": "arn:aws:secretsmanager:REGION:ACCOUNT_ID:secret:tableicty/production/backend-*"
      }
    ]
  }
  ```

### 3. Environment Variables Configuration

**Configure in AWS Secrets Manager (`tableicty/production/backend`):**

```json
{
  "SECRET_KEY": "<generate-50-character-random-string>",
  "DEBUG": "False",
  "ALLOWED_HOSTS": "api.tableicty.com,.app-runner.amazonaws.com",
  "IS_PRODUCTION": "True",
  "DATABASE_URL": "postgresql://tableicty_admin:<password>@<rds-endpoint>:5432/tableicty_production",
  "PGCRYPTO_KEY": "<generate-32-character-random-string>",
  "CORS_ALLOWED_ORIGINS": "https://app.tableicty.com,https://www.tableicty.com"
}
```

**Generate secure random values:**
```bash
# For SECRET_KEY (50 characters)
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# For PGCRYPTO_KEY (32 characters)
python -c "import secrets; print(secrets.token_urlsafe(32)[:32])"
```

- [ ] SECRET_KEY generated and added ✅
- [ ] PGCRYPTO_KEY generated and added ✅
- [ ] DATABASE_URL configured with RDS endpoint ✅
- [ ] ALLOWED_HOSTS includes production domain ✅
- [ ] CORS_ALLOWED_ORIGINS includes frontend domain ✅
- [ ] IS_PRODUCTION set to "True" ✅
- [ ] DEBUG set to "False" ✅

### 4. AWS App Runner Service Setup

- [ ] Create App Runner service:
  - [ ] Source: Source code repository
  - [ ] Repository provider: GitHub
  - [ ] Connect to GitHub and authorize AWS App Runner
  - [ ] Repository: `yourusername/tableicty`
  - [ ] Branch: `main`
  - [ ] Configuration: Use configuration file (`apprunner.yaml`)

- [ ] Create `apprunner.yaml` in repository root:
  ```yaml
  version: 1.0
  runtime: python311
  build:
    commands:
      pre-build:
        - pip install --upgrade pip
      build:
        - pip install -r requirements.txt
      post-build:
        - python manage.py collectstatic --noinput
  run:
    runtime-version: 3.11
    command: gunicorn --bind=0.0.0.0:8000 --workers=4 --timeout=120 --reuse-port config.wsgi:application
    network:
      port: 8000
    env:
      - name: PYTHONUNBUFFERED
        value: "1"
  ```

- [ ] Configure service settings:
  - [ ] Service name: `tableicty-backend-production`
  - [ ] Virtual CPU: 1 vCPU
  - [ ] Memory: 2 GB
  - [ ] Port: 8000
  - [ ] Auto-scaling configuration:
    - [ ] Min instances: 1
    - [ ] Max instances: 3 (adjust based on expected traffic)
    - [ ] Concurrency: 100 (requests per instance)

- [ ] Add environment variables reference:
  - [ ] Link to AWS Secrets Manager secret created above
  - [ ] App Runner will automatically inject secrets as environment variables

- [ ] Configure VPC connector:
  - [ ] Create VPC connector to access RDS in private subnet
  - [ ] Attach security group allowing outbound to RDS port 5432

- [ ] Configure custom domain:
  - [ ] Add custom domain: `api.tableicty.com`
  - [ ] Validation method: DNS (CNAME record)
  - [ ] Add CNAME record in Route 53 (see DNS Configuration section)

- [ ] Deploy service:
  - [ ] Click "Create & Deploy"
  - [ ] Wait for deployment (typically 5-10 minutes)
  - [ ] Status: **Running** ✅

### 5. Database Migration

**After App Runner service is deployed:**

- [ ] Connect to App Runner container (via AWS Console or CLI):
  ```bash
  # Get App Runner service ARN
  aws apprunner list-services
  
  # Start a session (if configured)
  aws apprunner start-deployment --service-arn <service-arn>
  ```

- [ ] Run database migrations:
  ```bash
  # SSH into App Runner instance (or run via deployment script)
  python manage.py migrate
  ```

- [ ] Create superuser account:
  ```bash
  python manage.py createsuperuser
  # Username: admin
  # Email: admin@tableicty.com
  # Password: <secure-password-stored-in-password-manager>
  ```

- [ ] Verify database connection:
  ```bash
  python manage.py dbshell
  # Should connect to RDS PostgreSQL successfully
  \dt  # List tables
  \q   # Quit
  ```

### 6. Load Initial Data (Optional)

- [ ] Seed sample data for testing (development/staging only):
  ```bash
  python manage.py seed_data
  ```
  
  **⚠️ DO NOT run seed_data in production with real customer data!**

- [ ] Alternative: Migrate data from existing system (if applicable)

### 7. Verify Backend Deployment

- [ ] Health check endpoint:
  ```bash
  curl https://api.tableicty.com/api/v1/health/
  # Expected: {"status": "healthy"}
  ```

- [ ] Admin panel accessible:
  - [ ] URL: `https://api.tableicty.com/admin/`
  - [ ] Login with superuser credentials
  - [ ] Verify models are visible

- [ ] API documentation accessible:
  - [ ] URL: `https://api.tableicty.com/api/schema/swagger-ui/`
  - [ ] Verify all endpoints are documented

- [ ] Test authentication:
  ```bash
  # Register a new test user
  curl -X POST https://api.tableicty.com/api/v1/shareholder/auth/register/ \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"TestPass123!","password_confirm":"TestPass123!"}'
  
  # Login
  curl -X POST https://api.tableicty.com/api/v1/shareholder/auth/login/ \
    -H "Content-Type: application/json" \
    -d '{"username":"test@example.com","password":"TestPass123!"}'
  
  # Verify httpOnly cookie is set in response headers
  ```

---

## Frontend Deployment (S3 + CloudFront)

### 1. Build Production Bundle

- [ ] Update frontend environment variables:
  
  Create `client/.env.production`:
  ```env
  VITE_API_BASE_URL=https://api.tableicty.com/api/v1
  ```

- [ ] Build production bundle:
  ```bash
  cd client
  npm run build
  ```

- [ ] Verify build output:
  - [ ] Build directory: `client/dist/`
  - [ ] Contains: `index.html`, `assets/` folder
  - [ ] File size: Optimized (<500 KB for main bundle)

- [ ] Test production build locally:
  ```bash
  npm run preview
  # Verify app works at http://localhost:4173
  ```

### 2. Create S3 Bucket for Static Hosting

- [ ] Create S3 bucket:
  - [ ] Bucket name: `tableicty-frontend-production` (must be globally unique)
  - [ ] Region: Same as other AWS resources (e.g., `us-east-1`)
  - [ ] Block all public access: **Yes** (CloudFront will serve content)
  - [ ] Versioning: **Enabled** (for rollback capability)
  - [ ] Encryption: **Enabled** (AES-256 or AWS KMS)

- [ ] Configure bucket for static website hosting:
  - [ ] Enable static website hosting
  - [ ] Index document: `index.html`
  - [ ] Error document: `index.html` (for SPA routing)

- [ ] Create bucket policy for CloudFront access:
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "AllowCloudFrontServicePrincipal",
        "Effect": "Allow",
        "Principal": {
          "Service": "cloudfront.amazonaws.com"
        },
        "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::tableicty-frontend-production/*",
        "Condition": {
          "StringEquals": {
            "AWS:SourceArn": "arn:aws:cloudfront::ACCOUNT_ID:distribution/DISTRIBUTION_ID"
          }
        }
      }
    ]
  }
  ```
  
  **Note**: Update `DISTRIBUTION_ID` after creating CloudFront distribution

### 3. Upload Build Files to S3

- [ ] Upload files via AWS CLI:
  ```bash
  aws s3 sync client/dist/ s3://tableicty-frontend-production/ \
    --delete \
    --cache-control "public,max-age=31536000" \
    --exclude "index.html"
  
  # Upload index.html separately with no-cache
  aws s3 cp client/dist/index.html s3://tableicty-frontend-production/index.html \
    --cache-control "no-cache,no-store,must-revalidate"
  ```

- [ ] Verify files uploaded:
  ```bash
  aws s3 ls s3://tableicty-frontend-production/ --recursive
  # Should list all files in dist/ directory
  ```

### 4. Create CloudFront Distribution

- [ ] Create CloudFront distribution:
  - [ ] Origin domain: `tableicty-frontend-production.s3.amazonaws.com`
  - [ ] Origin access: Origin access control (OAC)
  - [ ] Create new OAC:
    - [ ] Name: `tableicty-frontend-oac`
    - [ ] Signing behavior: Sign requests
  - [ ] Default root object: `index.html`
  - [ ] Viewer protocol policy: **Redirect HTTP to HTTPS**
  - [ ] Allowed HTTP methods: GET, HEAD, OPTIONS
  - [ ] Cache policy: CachingOptimized
  - [ ] Custom error responses:
    - [ ] 403 error → `/index.html` (status code 200) for SPA routing
    - [ ] 404 error → `/index.html` (status code 200) for SPA routing

- [ ] Configure alternate domain names (CNAMEs):
  - [ ] Add: `app.tableicty.com`
  - [ ] Add: `www.tableicty.com` (redirects to app.tableicty.com)

- [ ] Configure SSL/TLS certificate:
  - [ ] Select custom SSL certificate
  - [ ] Choose certificate from AWS Certificate Manager: `*.tableicty.com`
  - [ ] Security policy: TLSv1.2_2021 (minimum)

- [ ] Distribution settings:
  - [ ] Price class: Use all edge locations (for global performance)
  - [ ] Logging: **Enabled** (for analytics)
  - [ ] Log bucket: Create new S3 bucket `tableicty-cloudfront-logs`
  - [ ] Log prefix: `frontend/`

- [ ] Create distribution:
  - [ ] Click "Create Distribution"
  - [ ] Wait for deployment (typically 10-20 minutes)
  - [ ] Status: **Deployed** ✅

- [ ] Update S3 bucket policy with CloudFront distribution ID (see step 2)

### 5. DNS Configuration (Route 53)

- [ ] Create hosted zone (if not already exists):
  - [ ] Domain name: `tableicty.com`
  - [ ] Type: Public hosted zone
  - [ ] Record nameservers provided by Route 53

- [ ] Create DNS records:
  
  **Backend API:**
  - [ ] Record name: `api.tableicty.com`
  - [ ] Record type: CNAME (from App Runner custom domain setup)
  - [ ] Value: `<app-runner-url>.app-runner.amazonaws.com`
  - [ ] TTL: 300 seconds
  
  **Frontend (CloudFront):**
  - [ ] Record name: `app.tableicty.com`
  - [ ] Record type: A (Alias record)
  - [ ] Alias target: CloudFront distribution
  - [ ] Evaluate target health: No
  
  **Root domain redirect:**
  - [ ] Record name: `tableicty.com`
  - [ ] Record type: A (Alias record)
  - [ ] Alias target: Same CloudFront distribution
  - [ ] Or: Create S3 bucket redirect to `app.tableicty.com`
  
  **WWW subdomain:**
  - [ ] Record name: `www.tableicty.com`
  - [ ] Record type: CNAME
  - [ ] Value: `app.tableicty.com`

- [ ] Verify DNS propagation:
  ```bash
  # Check A record
  dig app.tableicty.com
  
  # Check CNAME record
  dig api.tableicty.com
  
  # Verify DNS resolution
  nslookup app.tableicty.com
  nslookup api.tableicty.com
  ```

### 6. Verify Frontend Deployment

- [ ] Frontend accessible via HTTPS:
  - [ ] URL: `https://app.tableicty.com`
  - [ ] SSL certificate valid (green padlock in browser)
  - [ ] No mixed content warnings

- [ ] SPA routing works:
  - [ ] Navigate to: `https://app.tableicty.com/dashboard`
  - [ ] Refresh page → Should load correctly (not 404)
  - [ ] Deep links work from external sources

- [ ] API connectivity:
  - [ ] Open browser developer tools → Network tab
  - [ ] Login with test account
  - [ ] Verify requests go to `https://api.tableicty.com`
  - [ ] Verify httpOnly cookies are set

- [ ] Static assets cached:
  - [ ] Check response headers for `cache-control`
  - [ ] JavaScript/CSS files: `max-age=31536000`
  - [ ] `index.html`: `no-cache,no-store,must-revalidate`

---

## Post-Deployment Testing

### Smoke Test Checklist

**Authentication Flow:**
- [ ] Navigate to `https://app.tableicty.com`
- [ ] Click "Login"
- [ ] Enter test credentials
- [ ] Successful login → Redirects to dashboard ✅
- [ ] Open browser DevTools → Application → Cookies
- [ ] Verify `refresh_token` cookie present:
  - [ ] httpOnly: ✅
  - [ ] Secure: ✅
  - [ ] SameSite: Strict ✅
- [ ] Logout
- [ ] Verify `refresh_token` cookie deleted ✅

**Portfolio Dashboard:**
- [ ] Login as test shareholder
- [ ] Dashboard loads with holdings data ✅
- [ ] Summary cards display correct totals ✅
- [ ] Pie chart renders (holdings by issuer) ✅
- [ ] Bar chart renders (holdings by security class) ✅
- [ ] Holdings table displays correctly ✅

**Transaction History:**
- [ ] Navigate to Transactions page
- [ ] Transactions load with pagination ✅
- [ ] Filter by transfer type → Results update ✅
- [ ] Filter by status → Results update ✅
- [ ] Filter by year → Results update ✅
- [ ] Click transaction → Modal opens with details ✅
- [ ] Export to CSV → File downloads ✅

**Tax Documents:**
- [ ] Navigate to Tax Documents page
- [ ] Documents load correctly ✅
- [ ] Filter by year → Results update ✅
- [ ] Filter by document type → Results update ✅
- [ ] Click download → File downloads or opens ✅

**Certificate Conversion:**
- [ ] Navigate to Certificates page
- [ ] Existing requests load ✅
- [ ] Click "New Request"
- [ ] Fill out form:
  - [ ] Select holding ✅
  - [ ] Select conversion type ✅
  - [ ] Enter share quantity ✅
  - [ ] Enter mailing address (if required) ✅
- [ ] Submit request → Success toast appears ✅
- [ ] Verify request appears in table ✅

**Profile Management:**
- [ ] Navigate to Profile page
- [ ] Shareholder information loads ✅
- [ ] Tax ID masked correctly (last 4 digits only) ✅
- [ ] Update email address
- [ ] Update phone number
- [ ] Update mailing address
- [ ] Click Save → Success toast appears ✅
- [ ] Refresh page → Changes persisted ✅

### CloudWatch Logs Monitoring

- [ ] Configure CloudWatch log groups:
  - [ ] App Runner logs: `/aws/apprunner/tableicty-backend-production`
  - [ ] Check for errors after deployment
  - [ ] Set up metric filters for:
    - [ ] HTTP 500 errors
    - [ ] Authentication failures
    - [ ] Database connection errors

- [ ] Create CloudWatch alarms:
  - [ ] High error rate (>10 errors in 5 minutes)
  - [ ] High latency (>2 seconds average response time)
  - [ ] Database connection failures
  - [ ] Memory utilization >80%

- [ ] Review logs for first 24 hours:
  - [ ] No critical errors ✅
  - [ ] Authentication working correctly ✅
  - [ ] Database queries optimized ✅

### Performance Verification

- [ ] Frontend load time:
  - [ ] Initial page load: <2 seconds ✅
  - [ ] Time to interactive (TTI): <3 seconds ✅
  - [ ] Lighthouse score: >90 (Performance) ✅

- [ ] Backend API response time:
  - [ ] Authentication endpoints: <500ms ✅
  - [ ] Data fetch endpoints: <1 second ✅
  - [ ] Complex queries (cap table): <2 seconds ✅

- [ ] CDN performance:
  - [ ] Test from multiple geographic locations
  - [ ] Use tools: WebPageTest, GTmetrix, Pingdom
  - [ ] Verify CloudFront edge caching working

---

## Rollback Plan

### Backend Rollback (App Runner)

**If deployment issues occur:**

1. [ ] Identify the issue:
   - Check CloudWatch logs for errors
   - Check RDS connectivity
   - Verify environment variables

2. [ ] Rollback to previous version:
   ```bash
   # Via AWS Console:
   # App Runner → Services → tableicty-backend-production → Deployments
   # Select previous successful deployment → Rollback
   
   # Via AWS CLI:
   aws apprunner start-deployment \
     --service-arn <service-arn> \
     --deployment-id <previous-deployment-id>
   ```

3. [ ] Verify rollback successful:
   - Check health endpoint
   - Test authentication
   - Review logs

### Frontend Rollback (S3 + CloudFront)

**If deployment issues occur:**

1. [ ] Restore previous S3 version:
   ```bash
   # List versions
   aws s3api list-object-versions \
     --bucket tableicty-frontend-production \
     --prefix index.html
   
   # Restore specific version
   aws s3api copy-object \
     --bucket tableicty-frontend-production \
     --copy-source tableicty-frontend-production/index.html?versionId=<version-id> \
     --key index.html
   ```

2. [ ] Invalidate CloudFront cache:
   ```bash
   aws cloudfront create-invalidation \
     --distribution-id <distribution-id> \
     --paths "/*"
   ```

3. [ ] Verify rollback:
   - Clear browser cache
   - Test application functionality
   - Verify assets loading correctly

### Database Rollback (RDS)

**If database migration issues occur:**

1. [ ] Restore from automated backup:
   ```bash
   # Via AWS Console:
   # RDS → Databases → tableicty-production → Restore to point in time
   # Select restore time (before migration)
   # Create new database instance
   
   # Update App Runner DATABASE_URL to point to restored instance
   ```

2. [ ] Alternative: Manual SQL rollback:
   ```bash
   # Connect to database
   psql -h <rds-endpoint> -U tableicty_admin -d tableicty_production
   
   # Rollback last migration
   # (Django does not support automatic migration rollback)
   # Manual SQL required - have SQL rollback script ready
   ```

### Emergency Contacts

- [ ] AWS Support: https://console.aws.amazon.com/support/
- [ ] DNS Provider Support: (if using external DNS)
- [ ] On-call engineer: [YOUR CONTACT INFO]
- [ ] Backup engineer: [BACKUP CONTACT INFO]

### Backup and Recovery Procedures

- [ ] RDS automated backups: Enabled (7-30 day retention)
- [ ] S3 versioning: Enabled (can restore previous frontend versions)
- [ ] CloudWatch log retention: 30 days minimum
- [ ] Database backup schedule:
  - [ ] Automated daily backups (RDS)
  - [ ] Manual snapshot before major changes
  - [ ] Test restore procedure quarterly

---

## Post-Deployment Tasks

### Immediate (Day 1)

- [ ] Monitor CloudWatch logs for errors
- [ ] Verify all smoke tests passing
- [ ] Check SSL certificate expiration date (auto-renews via ACM)
- [ ] Send test email to stakeholders with production URL
- [ ] Update documentation with final production URLs

### Short-term (Week 1)

- [ ] Monitor application performance metrics
- [ ] Gather user feedback from initial test users
- [ ] Optimize database queries if slow (check RDS Performance Insights)
- [ ] Review CloudWatch cost estimates
- [ ] Set up billing alerts (AWS Budget)

### Medium-term (Month 1)

- [ ] Analyze CloudWatch metrics for traffic patterns
- [ ] Optimize auto-scaling configuration based on usage
- [ ] Review and optimize CloudFront cache settings
- [ ] Plan for database scaling if needed (read replicas, instance size)
- [ ] Schedule first quarterly disaster recovery test

---

## Cost Estimates (AWS Pricing)

**Monthly estimates for initial deployment:**

| Service | Configuration | Estimated Cost |
|---------|--------------|----------------|
| App Runner | 1 vCPU, 2 GB RAM, 1-3 instances | $25-75/month |
| RDS PostgreSQL | db.t3.micro, 20 GB storage | $15-20/month |
| S3 | 1 GB storage, 10K requests/month | $0.50-1/month |
| CloudFront | 10 GB data transfer, 100K requests | $1-5/month |
| Route 53 | Hosted zone + DNS queries | $0.50-1/month |
| Secrets Manager | 1 secret | $0.40/month |
| CloudWatch | Logs + Metrics | $5-10/month |
| **Total Estimated** | | **$47-112/month** |

**Note**: Costs scale with usage. Monitor AWS Cost Explorer for actual costs.

---

## Success Criteria

**Deployment is considered successful when:**

- [ ] ✅ All smoke tests passing (100%)
- [ ] ✅ Frontend accessible via HTTPS at `app.tableicty.com`
- [ ] ✅ Backend API accessible via HTTPS at `api.tableicty.com`
- [ ] ✅ SSL certificates valid and auto-renewing
- [ ] ✅ httpOnly cookies working correctly
- [ ] ✅ Database migrations completed successfully
- [ ] ✅ CloudWatch logs showing no errors
- [ ] ✅ Performance metrics within acceptable ranges
- [ ] ✅ Rollback plan tested and documented
- [ ] ✅ Monitoring and alerting configured
- [ ] ✅ Team trained on production access and procedures

**Ready for Step 3 (Admin Console Development)** 🎉

---

## Additional Resources

**AWS Documentation:**
- App Runner: https://docs.aws.amazon.com/apprunner/
- RDS PostgreSQL: https://docs.aws.amazon.com/rds/
- CloudFront: https://docs.aws.amazon.com/cloudfront/
- Route 53: https://docs.aws.amazon.com/route53/
- Secrets Manager: https://docs.aws.amazon.com/secretsmanager/

**tableicty Documentation:**
- Technical Architecture: `replit.md`
- Setup Instructions: `README.md`
- Test Results: 86/86 tests passing (100%)

**Support:**
- GitHub Issues: https://github.com/yourusername/tableicty/issues
- AWS Support: https://console.aws.amazon.com/support/

---

**Last Updated**: November 20, 2025  
**Version**: 1.0  
**Status**: Ready for AWS Deployment ✅
