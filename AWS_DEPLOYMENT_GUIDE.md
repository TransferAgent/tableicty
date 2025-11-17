# 🚀 AWS DEPLOYMENT GUIDE - tableicty Transfer Agent Platform

**Your Domain:** otcsimplified.com  
**Deployment Target:** AWS (Staging Environment)  
**Estimated Time:** 3-5 hours

---

## 📋 PRE-DEPLOYMENT CHECKLIST

Before you begin, ensure you have:

- ✅ AWS Account with billing enabled
- ✅ AWS CLI installed locally (optional but recommended)
- ✅ GitHub repository for your code
- ✅ Domain registrar access (for DNS updates)
- ✅ This deployment guide
- ✅ The generated encryption keys (in `/tmp/aws_secrets_SECURE.txt`)

---

## 🎯 DEPLOYMENT OVERVIEW

We'll deploy in this order:
1. **VPC & Networking** (foundational infrastructure)
2. **RDS PostgreSQL Database** (your data layer)
3. **ElastiCache Redis** (caching layer - optional for MVP)
4. **S3 Bucket** (file storage)
5. **AWS Secrets Manager** (security layer)
6. **AWS App Runner** (your Django application)
7. **Route 53 DNS** (connect your domain)
8. **CloudWatch Monitoring** (observability)

---

## ⚠️ CRITICAL: ENCRYPTION KEYS

**SECURITY REQUIREMENT:** Use the NEW keys generated in `/tmp/aws_secrets_SECURE.txt`

**NEVER:**
- ❌ Reuse Replit keys in production
- ❌ Commit keys to GitHub
- ❌ Share keys in documents/chat
- ❌ Use same keys in staging and production

**ALWAYS:**
- ✅ Store keys ONLY in AWS Secrets Manager
- ✅ Use different keys for staging vs production
- ✅ Delete `/tmp/aws_secrets_SECURE.txt` after copying to AWS

---

## STEP 1: CREATE VPC & NETWORKING (15 minutes)

### 1.1 Create VPC

1. Go to **AWS Console** → **VPC** → **Create VPC**
2. Settings:
   ```
   Name: tableicty-vpc
   IPv4 CIDR: 10.0.0.0/16
   Tenancy: Default
   ```
3. Click **Create VPC**

### 1.2 Create Subnets

**Private Subnet 1 (for RDS/Redis):**
```
Name: tableicty-private-subnet-1a
VPC: tableicty-vpc
Availability Zone: us-east-1a
IPv4 CIDR: 10.0.1.0/24
```

**Private Subnet 2 (for RDS Multi-AZ):**
```
Name: tableicty-private-subnet-1b
VPC: tableicty-vpc
Availability Zone: us-east-1b
IPv4 CIDR: 10.0.2.0/24
```

**Public Subnet (for App Runner - managed by AWS):**
```
Name: tableicty-public-subnet-1a
VPC: tableicty-vpc
Availability Zone: us-east-1a
IPv4 CIDR: 10.0.3.0/24
```

### 1.3 Create Internet Gateway

1. **VPC** → **Internet Gateways** → **Create**
   ```
   Name: tableicty-igw
   ```
2. **Attach to VPC:** tableicty-vpc

### 1.4 Create Route Tables

**Public Route Table:**
1. Create route table: `tableicty-public-rt`
2. Add route: `0.0.0.0/0` → `tableicty-igw`
3. Associate with `tableicty-public-subnet-1a`

---

## STEP 2: CREATE RDS POSTGRESQL DATABASE (20 minutes)

### 2.1 Create DB Subnet Group

1. Go to **RDS** → **Subnet Groups** → **Create**
   ```
   Name: tableicty-db-subnet-group
   VPC: tableicty-vpc
   Subnets: Select both private subnets (1a and 1b)
   ```

### 2.2 Create Security Group for RDS

1. **EC2** → **Security Groups** → **Create**
   ```
   Name: tableicty-rds-sg
   Description: Allow PostgreSQL access from App Runner
   VPC: tableicty-vpc
   
   Inbound Rules:
   - Type: PostgreSQL
   - Protocol: TCP
   - Port: 5432
   - Source: Custom (we'll update this after creating App Runner)
   
   Outbound Rules:
   - Type: All traffic
   - Destination: 0.0.0.0/0
   ```

### 2.3 Create RDS Instance

1. **RDS** → **Databases** → **Create Database**
2. Settings:
   ```
   Engine: PostgreSQL
   Version: 15.4
   Template: Free tier (for staging)
   
   DB Instance Identifier: tableicty-staging-db
   Master Username: tableicty_admin
   Master Password: <Generate 32-char password - save to Secrets Manager>
   
   DB Instance Class: db.t3.micro (Free Tier)
   Storage Type: General Purpose SSD (gp2)
   Allocated Storage: 20 GB
   Storage Autoscaling: Enabled (max 100 GB)
   
   VPC: tableicty-vpc
   DB Subnet Group: tableicty-db-subnet-group
   Public Access: NO
   VPC Security Group: tableicty-rds-sg
   
   Initial Database Name: tableicty_staging
   
   Backup:
   - Automated backups: Enabled
   - Backup retention: 7 days
   - Backup window: 03:00-04:00 UTC
   
   Encryption: Enabled (AWS KMS - default key)
   
   Enhanced Monitoring: Enabled (60 seconds)
   Performance Insights: Enabled
   ```

3. Click **Create Database** (takes 10-15 minutes)
4. **SAVE THE ENDPOINT:** Will look like `tableicty-staging-db.abc123.us-east-1.rds.amazonaws.com`

---

## STEP 3: CREATE S3 BUCKET (10 minutes)

### 3.1 Create S3 Bucket

1. **S3** → **Create Bucket**
   ```
   Bucket Name: otcsimplified-documents-staging
   Region: us-east-1
   
   Block Public Access: Enable (all checkboxes)
   Bucket Versioning: Enabled
   
   Default Encryption: 
   - Encryption Type: SSE-S3 (AES-256)
   - Bucket Key: Enabled
   ```

### 3.2 Create Folder Structure

Create these folders in the bucket:
- `certificates/`
- `signatures/`
- `documents/`
- `audit-exports/`

### 3.3 Create IAM User for S3 Access

1. **IAM** → **Users** → **Create User**
   ```
   User Name: tableicty-s3-user
   Access Type: Programmatic access
   ```

2. **Attach Policy:** Create inline policy:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:PutObject",
           "s3:GetObject",
           "s3:DeleteObject",
           "s3:ListBucket"
         ],
         "Resource": [
           "arn:aws:s3:::otcsimplified-documents-staging",
           "arn:aws:s3:::otcsimplified-documents-staging/*"
         ]
       }
     ]
   }
   ```

3. **Save Credentials:**
   - Access Key ID: `AKIA...`
   - Secret Access Key: `...` (save to Secrets Manager)

---

## STEP 4: CREATE AWS SECRETS MANAGER SECRETS (15 minutes)

### 4.1 Database URL Secret

1. **Secrets Manager** → **Store a new secret**
   ```
   Secret Type: Other type of secret
   Key/Value:
   - Key: DATABASE_URL
   - Value: postgresql://tableicty_admin:<PASSWORD>@<RDS_ENDPOINT>:5432/tableicty_staging
   
   Example: postgresql://tableicty_admin:MySecurePass123!@tableicty-staging-db.abc123.us-east-1.rds.amazonaws.com:5432/tableicty_staging
   
   Secret Name: tableicty/staging/database-url
   ```

### 4.2 Django Secret Key

1. Create new secret:
   ```
   Key: SECRET_KEY
   Value: <Copy from /tmp/aws_secrets_SECURE.txt - STAGING SECRET_KEY>
   
   Secret Name: tableicty/staging/django-secret-key
   ```

### 4.3 PGCrypto Encryption Key

1. Create new secret:
   ```
   Key: PGCRYPTO_KEY
   Value: <Copy from /tmp/aws_secrets_SECURE.txt - STAGING PGCRYPTO_KEY>
   
   Secret Name: tableicty/staging/pgcrypto-key
   ```

### 4.4 AWS S3 Credentials

1. Create new secret:
   ```
   Key/Value pairs:
   - AWS_ACCESS_KEY_ID: <From IAM user creation>
   - AWS_SECRET_ACCESS_KEY: <From IAM user creation>
   - AWS_STORAGE_BUCKET_NAME: otcsimplified-documents-staging
   
   Secret Name: tableicty/staging/aws-s3-credentials
   ```

### 4.5 All Environment Variables (Combined)

For App Runner, create one secret with all env vars:

1. Create new secret:
   ```json
   {
     "DATABASE_URL": "postgresql://tableicty_admin:PASSWORD@RDS_ENDPOINT:5432/tableicty_staging",
     "SECRET_KEY": "<staging secret key>",
     "PGCRYPTO_KEY": "<staging pgcrypto key>",
     "AWS_ACCESS_KEY_ID": "<s3 access key>",
     "AWS_SECRET_ACCESS_KEY": "<s3 secret key>",
     "AWS_STORAGE_BUCKET_NAME": "otcsimplified-documents-staging",
     "AWS_S3_REGION_NAME": "us-east-1",
     "DEBUG": "False",
     "IS_PRODUCTION": "False",
     "USE_S3": "True",
     "ALLOWED_HOSTS": "staging.otcsimplified.com,.awsapprunner.com",
     "CORS_ALLOWED_ORIGINS": "https://staging.otcsimplified.com"
   }
   
   Secret Name: tableicty/staging/environment
   ```

---

## STEP 5: DEPLOY TO AWS APP RUNNER (30 minutes)

### 5.1 Push Code to GitHub

1. Create GitHub repository: `tableicty-backend`
2. Push your code:
   ```bash
   git init
   git add .
   git commit -m "Initial commit - AWS deployment ready"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/tableicty-backend.git
   git push -u origin main
   ```

### 5.2 Create App Runner Service

1. **App Runner** → **Create Service**

2. **Repository Settings:**
   ```
   Source: GitHub
   Connect to GitHub: <Authorize AWS to access your repo>
   Repository: YOUR_USERNAME/tableicty-backend
   Branch: main
   
   Deployment Trigger: Automatic (deploy on push)
   
   Configuration File: Use configuration file (apprunner.yaml)
   ```

3. **Service Settings:**
   ```
   Service Name: tableicty-staging
   
   Virtual CPU: 1 vCPU
   Virtual Memory: 2 GB
   
   Port: 8000
   ```

4. **Environment Variables:**
   - Click "Add environment variable"
   - Select "Reference to secret"
   - Secret: `tableicty/staging/environment`
   - Click "Import all keys from secret"

5. **Health Check:**
   ```
   Protocol: HTTP
   Path: /api/v1/health/
   Interval: 10 seconds
   Timeout: 5 seconds
   Healthy Threshold: 1
   Unhealthy Threshold: 5
   ```

6. **Auto Scaling:**
   ```
   Min Instances: 1
   Max Instances: 3
   Concurrency: 100
   ```

7. **Security:**
   ```
   VPC Connector: Create new
   - VPC: tableicty-vpc
   - Subnets: Select both private subnets
   ```

8. Click **Create & Deploy** (takes 10-15 minutes)

### 5.3 Get App Runner URL

After deployment completes:
1. Note your App Runner URL: `https://abc123xyz.us-east-1.awsapprunner.com`
2. Test the health endpoint: `https://YOUR_URL/api/v1/health/`
3. Should return `{"status": "healthy"}`

### 5.4 Update RDS Security Group

Now that App Runner is created:
1. **EC2** → **Security Groups** → `tableicty-rds-sg`
2. Edit inbound rules:
   - Change source from "Custom" to the App Runner security group
   - Or use App Runner's VPC CIDR: `10.0.0.0/16`

### 5.5 Run Database Migrations

1. **App Runner** → Your service → **Actions** → **Execute command** (if available)
   
   Or SSH into a running container and run:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py seed_data
   ```

   **Alternative:** Create a one-time deployment job or use AWS Systems Manager Session Manager

---

## STEP 6: CONFIGURE ROUTE 53 & DNS (15 minutes)

### 6.1 Create Hosted Zone (if not exists)

1. **Route 53** → **Hosted Zones** → **Create**
   ```
   Domain Name: otcsimplified.com
   Type: Public Hosted Zone
   ```

2. **Copy Nameservers:** You'll get 4 nameservers like:
   ```
   ns-123.awsdns-12.com
   ns-456.awsdns-45.net
   ns-789.awsdns-78.org
   ns-012.awsdns-01.co.uk
   ```

### 6.2 Update Domain Registrar

**⏰ THIS IS WHEN YOU UPDATE DNS**

Go to your domain registrar (GoDaddy, Namecheap, etc.) and:
1. Find DNS settings for `otcsimplified.com`
2. Update nameservers to the 4 AWS nameservers from above
3. Save changes (propagation takes 15 minutes - 48 hours)

### 6.3 Create SSL Certificate (AWS Certificate Manager)

1. **Certificate Manager** → **Request Certificate**
   ```
   Certificate Type: Public
   Domain Names:
   - otcsimplified.com
   - *.otcsimplified.com (wildcard for subdomains)
   
   Validation: DNS validation
   ```

2. Click **Create records in Route 53** (auto-validates)
3. Wait for certificate status: **Issued** (takes 5-30 minutes)

### 6.4 Create DNS Records for Staging

1. **Route 53** → **Hosted Zones** → `otcsimplified.com` → **Create Record**

**Staging Subdomain:**
```
Record Name: staging
Record Type: CNAME
Value: <Your App Runner URL without https://>
       Example: abc123xyz.us-east-1.awsapprunner.com
TTL: 300
```

### 6.5 Configure Custom Domain in App Runner

1. **App Runner** → Your service → **Custom Domains**
2. **Link Domain:**
   ```
   Domain: staging.otcsimplified.com
   Certificate: Select the ACM certificate created above
   ```
3. Click **Link Domain**
4. Wait for status: **Active** (takes 5-10 minutes)

### 6.6 Test Your Domain

After DNS propagation:
```bash
# Should return 200 OK
curl https://staging.otcsimplified.com/api/v1/health/

# Should redirect to HTTPS
curl http://staging.otcsimplified.com/api/v1/health/
```

**✅ Your platform is now live at `https://staging.otcsimplified.com`**

---

## STEP 7: CLOUDWATCH MONITORING (15 minutes)

### 7.1 Create CloudWatch Dashboard

1. **CloudWatch** → **Dashboards** → **Create**
   ```
   Dashboard Name: tableicty-staging-dashboard
   ```

2. Add widgets:
   - **App Runner:** Request count, response time, error rate
   - **RDS:** CPU utilization, database connections, storage
   - **S3:** Total storage, request count

### 7.2 Create Alarms

**High Error Rate Alarm:**
```
Metric: App Runner 5XX Errors
Threshold: > 10 errors in 5 minutes
Action: Send SNS email notification
```

**Database CPU Alarm:**
```
Metric: RDS CPU Utilization
Threshold: > 80% for 10 minutes
Action: Send SNS email notification
```

**Response Time Alarm:**
```
Metric: App Runner Response Time (P95)
Threshold: > 2000ms for 5 minutes
Action: Send SNS email notification
```

### 7.3 Configure SNS Email Notifications

1. **SNS** → **Topics** → **Create**
   ```
   Name: tableicty-staging-alerts
   ```
2. **Create Subscription:**
   ```
   Protocol: Email
   Endpoint: your-email@example.com
   ```
3. Confirm subscription email

### 7.4 Enable App Runner Logs

App Runner automatically sends logs to CloudWatch:
- Log Group: `/aws/apprunner/tableicty-staging/application`
- Retention: 30 days (adjust in CloudWatch Logs)

---

## STEP 8: VERIFY DEPLOYMENT (10 minutes)

### 8.1 Health Check

```bash
curl https://staging.otcsimplified.com/api/v1/health/
# Expected: {"status": "healthy"}
```

### 8.2 Admin Login

1. Visit: `https://staging.otcsimplified.com/admin/`
2. Login with superuser credentials
3. Verify all models visible
4. Check shareholders, transfers, holdings

### 8.3 API Documentation

1. Visit: `https://staging.otcsimplified.com/api/docs/`
2. Test API endpoints with Swagger UI
3. Verify authentication works

### 8.4 Test Transfer Workflow

1. Create shareholder via API
2. Create transfer via API
3. Approve transfer
4. Execute transfer
5. Verify holdings updated

### 8.5 Test Tax ID Encryption

1. Create shareholder with SSN in admin
2. Run Django shell:
   ```python
   from apps.core.models import Shareholder
   from django.db import connection
   
   s = Shareholder.objects.first()
   print(f"ORM: {s.tax_id}")  # Should show plaintext
   
   with connection.cursor() as cursor:
       cursor.execute("SELECT tax_id FROM core_shareholder LIMIT 1")
       print(f"DB: {cursor.fetchone()[0]}")  # Should show encrypted binary
   ```

### 8.6 Verify S3 File Upload

1. Upload document in admin
2. Check S3 bucket for file
3. Download and verify file integrity

---

## STEP 9: SECURITY HARDENING (15 minutes)

### 9.1 Enable CloudTrail

1. **CloudTrail** → **Create Trail**
   ```
   Trail Name: tableicty-audit-trail
   Storage Location: New S3 bucket
   Log Events: Management events + Data events
   ```

### 9.2 Enable AWS Config

1. **AWS Config** → **Get Started**
2. Enable resource recording
3. Create rules:
   - `encrypted-volumes` - Ensure EBS/RDS encrypted
   - `s3-bucket-public-read-prohibited`
   - `rds-storage-encrypted`

### 9.3 Enable GuardDuty

1. **GuardDuty** → **Get Started**
2. Enable for us-east-1
3. Configure email notifications for findings

### 9.4 IAM Best Practices

1. Enable MFA for root account
2. Create least-privilege IAM roles
3. Enable IAM Access Analyzer
4. Rotate access keys quarterly

---

## STEP 10: COST OPTIMIZATION (5 minutes)

### 10.1 Set Up Billing Alerts

1. **Billing** → **Budgets** → **Create Budget**
   ```
   Budget Name: tableicty-monthly-budget
   Amount: $50/month
   Alert at: 80% and 100%
   ```

### 10.2 Enable Cost Explorer

1. **Cost Explorer** → Enable
2. Create cost reports
3. Track spending by service

### 10.3 Free Tier Usage

Monitor free tier usage:
- RDS: 750 hours/month (db.t3.micro)
- ElastiCache: 750 hours/month (cache.t3.micro)
- App Runner: Minimal cost (~$5-10/month)

**Expected Monthly Cost (Staging):** $10-25/month

---

## 🎉 DEPLOYMENT COMPLETE!

### ✅ What You Now Have:

- ✅ Production-grade infrastructure on AWS
- ✅ Encrypted database (RDS PostgreSQL)
- ✅ Secure file storage (S3)
- ✅ Auto-scaling application (App Runner)
- ✅ Custom domain with SSL (staging.otcsimplified.com)
- ✅ Comprehensive monitoring (CloudWatch)
- ✅ Automated deployments (GitHub → App Runner)
- ✅ Security hardening enabled
- ✅ Cost tracking and budgets

### 📊 Access Your Platform:

- **Website:** https://staging.otcsimplified.com
- **Admin:** https://staging.otcsimplified.com/admin/
- **API Docs:** https://staging.otcsimplified.com/api/docs/
- **Health Check:** https://staging.otcsimplified.com/api/v1/health/

### 📁 Important Files:

- `apprunner.yaml` - App Runner configuration
- `config/settings.py` - Updated with production settings
- `requirements.txt` - Updated with AWS dependencies
- `/tmp/aws_secrets_SECURE.txt` - Encryption keys (DELETE AFTER USE)

---

## 🔄 NEXT STEPS (Production Deployment)

When ready for production:

1. **Create Production Environment:**
   - Use same steps but with production settings
   - Different encryption keys (from `/tmp/aws_secrets_SECURE.txt`)
   - Larger RDS instance (db.t3.small or db.m6g.large)
   - Multi-AZ RDS deployment
   - Production domain: `app.otcsimplified.com` or `www.otcsimplified.com`

2. **Additional Production Requirements:**
   - WAF (Web Application Firewall)
   - DDoS protection (AWS Shield)
   - Backup and disaster recovery plan
   - Load testing
   - Penetration testing

3. **Compliance:**
   - SOC 2 audit preparation
   - FINRA regulatory review
   - Data retention policies
   - Incident response plan

---

## 🆘 TROUBLESHOOTING

### App Runner Deployment Fails

**Issue:** Build or health check failing

**Solution:**
1. Check CloudWatch logs: `/aws/apprunner/tableicty-staging/application`
2. Verify all secrets are set correctly
3. Run `python manage.py check --deploy` locally
4. Check database connection string

### Database Connection Errors

**Issue:** Can't connect to RDS

**Solution:**
1. Verify RDS security group allows App Runner VPC
2. Check DATABASE_URL format
3. Ensure RDS is in same VPC as App Runner connector
4. Test connection from App Runner container

### Domain Not Working

**Issue:** staging.otcsimplified.com doesn't resolve

**Solution:**
1. Verify nameservers updated at registrar (takes 24-48 hours)
2. Check Route 53 CNAME record is correct
3. Ensure SSL certificate is validated
4. Wait for DNS propagation: `dig staging.otcsimplified.com`

### S3 Upload Failing

**Issue:** File uploads to S3 fail

**Solution:**
1. Verify IAM user has correct permissions
2. Check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in Secrets Manager
3. Ensure bucket name is correct
4. Verify boto3 and django-storages installed

---

## 📞 SUPPORT

If you encounter issues:

1. **Check CloudWatch Logs** first
2. **Review AWS Service Health Dashboard**
3. **Consult AWS documentation** for specific services
4. **Contact AWS Support** (if you have a support plan)

---

## 🔒 SECURITY REMINDER

**AFTER DEPLOYMENT:**

1. ✅ Delete `/tmp/aws_secrets_SECURE.txt`
2. ✅ Rotate Replit PGCRYPTO_KEY (it's exposed in docs)
3. ✅ Never commit secrets to GitHub
4. ✅ Enable MFA on AWS root account
5. ✅ Review IAM permissions quarterly
6. ✅ Monitor CloudWatch for anomalies

---

**Deployment Guide Version:** 1.0  
**Last Updated:** November 17, 2025  
**Platform:** tableicty Transfer Agent SaaS  
**Domain:** otcsimplified.com

**Status:** Ready for production deployment! 🚀
