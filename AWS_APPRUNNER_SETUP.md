# AWS App Runner Setup Guide for tableicty

## Pre-requisites (Already Complete)
- [x] RDS PostgreSQL 17.6 provisioned
- [x] ElastiCache Redis 7.1 provisioned
- [x] Parameter Store secrets configured
- [x] VPC and Security Groups configured
- [x] IAM Policy created

## Infrastructure Details

### AWS Account
- **Account ID:** 783790254091
- **Region:** us-east-1

### Database (RDS)
- **Endpoint:** tableicty-production-db.c25aymqygnka.us-east-1.rds.amazonaws.com
- **Port:** 5432
- **Database:** tableicty

### Cache (ElastiCache Redis)
- **Endpoint:** master.tableicty-production-redis.tzrmpe.use1.cache.amazonaws.com
- **Port:** 6379

### VPC Configuration
- **VPC ID:** vpc-01ec31a7b467863b4
- **Security Group:** tableicty-rds-sg (sg-002355381775a914c)

### Parameter Store Paths
| Environment Variable | Parameter Store Path |
|---------------------|---------------------|
| PGCRYPTO_KEY | /tableicty/production/PGCRYPTO_KEY |
| SECRET_KEY | /tableicty/production/SECRET_KEY |
| DATABASE_URL | /tableicty/production/DATABASE_URL |
| REDIS_URL | /tableicty/production/REDIS_URL |

---

## Step 1: Create VPC Connector

1. Go to **AWS App Runner** → **VPC connectors** → **Create VPC connector**
2. Configure:
   - **Name:** tableicty-vpc-connector
   - **VPC:** vpc-01ec31a7b467863b4
   - **Subnets:** Select at least 2:
     - us-east-1a: subnet-09abfb909c9cd564f
     - us-east-1b: subnet-0ad1fcba35f11a552c
   - **Security Group:** tableicty-rds-sg (sg-002355381775a914c)

---

## Step 2: Create App Runner Service

### Source Configuration
1. **Repository type:** Source code repository
2. **Connect to GitHub:** TransferAgent/tableicty
3. **Branch:** main
4. **Build settings:** Use configuration file (apprunner.yaml)

### Service Settings
1. **Service name:** tableicty-backend
2. **CPU:** 1 vCPU
3. **Memory:** 2 GB
4. **Port:** 8000

### Networking
1. **Custom VPC:** Yes
2. **VPC connector:** tableicty-vpc-connector (created in Step 1)

### Environment Variables from Parameter Store
Configure these in App Runner console → Service settings → Environment variables:

| Key | Value Source |
|-----|-------------|
| PGCRYPTO_KEY | arn:aws:ssm:us-east-1:783790254091:parameter/tableicty/production/PGCRYPTO_KEY |
| SECRET_KEY | arn:aws:ssm:us-east-1:783790254091:parameter/tableicty/production/SECRET_KEY |
| DATABASE_URL | arn:aws:ssm:us-east-1:783790254091:parameter/tableicty/production/DATABASE_URL |
| REDIS_URL | arn:aws:ssm:us-east-1:783790254091:parameter/tableicty/production/REDIS_URL |

### IAM Role
Attach policy: **Tableicty-ParameterStore-ReadAccess**
- ARN: arn:aws:iam::783790254091:policy/Tableicty-ParameterStore-ReadAccess

---

## Step 3: Run Migrations (After Deployment)

Once App Runner is running, use AWS CloudShell or connect to run migrations:

```bash
# The pgcrypto extension will be enabled automatically via migration 0002
python manage.py migrate
```

**Note:** Migration `apps/core/migrations/0002_enable_pgcrypto.py` handles:
```python
CreateExtension('pgcrypto')
```

---

## Step 4: Deploy Frontend to S3/CloudFront

### Create S3 Bucket
1. **Bucket name:** tableicty-frontend
2. **Region:** us-east-1
3. **Block public access:** OFF (for static hosting)
4. **Static website hosting:** Enable
   - Index document: index.html
   - Error document: index.html (for SPA routing)

### Upload Frontend Build
```bash
# From client/dist directory
aws s3 sync . s3://tableicty-frontend --delete
```

### Create CloudFront Distribution
1. **Origin:** tableicty-frontend.s3.us-east-1.amazonaws.com
2. **Viewer Protocol Policy:** Redirect HTTP to HTTPS
3. **Allowed HTTP Methods:** GET, HEAD
4. **Alternate Domain Names:** tableicty.com, www.tableicty.com
5. **SSL Certificate:** Select from ACM (already provisioned)
6. **Default Root Object:** index.html
7. **Custom Error Pages:**
   - 403 → /index.html (200)
   - 404 → /index.html (200)

---

## Step 5: Configure Route 53 DNS

### A Records
| Record Name | Type | Alias Target |
|-------------|------|--------------|
| tableicty.com | A | CloudFront distribution |
| www.tableicty.com | A | CloudFront distribution |
| api.tableicty.com | A | App Runner service URL |

---

## Step 6: Verify Deployment

### Backend Health Check
```bash
curl https://api.tableicty.com/api/v1/health/
```

### Frontend Access
- https://tableicty.com
- https://www.tableicty.com

### API Documentation
- https://api.tableicty.com/api/schema/swagger-ui/

---

## Troubleshooting

### VPC Connectivity Issues
- Verify security group allows inbound from App Runner
- Check VPC connector subnets have NAT gateway access

### Database Connection Errors
- Verify DATABASE_URL parameter is correct
- Check RDS security group allows App Runner security group

### Parameter Store Access Denied
- Verify IAM policy is attached to App Runner service role
- Check parameter paths match exactly

---

## Monthly Cost Estimate
| Service | Estimated Cost |
|---------|---------------|
| App Runner (1 vCPU, 2GB) | ~$25-50/month |
| RDS PostgreSQL (db.t3.micro) | ~$15-20/month |
| ElastiCache Redis (cache.t3.micro) | ~$15/month |
| S3 + CloudFront | ~$5-10/month |
| Route 53 | ~$1/month |
| **Total** | **~$60-100/month** |
