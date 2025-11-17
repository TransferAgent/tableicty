#!/usr/bin/env python
"""
Quick test script to verify shareholder API endpoints are accessible.
This doesn't test authentication, just verifies the URLs are configured correctly.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.urls import resolve
from django.urls.exceptions import Resolver404

endpoints = [
    '/api/v1/shareholder/auth/register/',
    '/api/v1/shareholder/auth/login/',
    '/api/v1/shareholder/auth/logout/',
    '/api/v1/shareholder/auth/refresh/',
    '/api/v1/shareholder/auth/me/',
    '/api/v1/shareholder/holdings/',
    '/api/v1/shareholder/summary/',
    '/api/v1/shareholder/transactions/',
    '/api/v1/shareholder/tax-documents/',
    '/api/v1/shareholder/certificate-conversion/',
    '/api/v1/shareholder/profile/',
]

print("\n✅ Testing Shareholder Portal API Endpoints\n")
print("=" * 60)

all_passed = True
for endpoint in endpoints:
    try:
        match = resolve(endpoint)
        print(f"✅ {endpoint}")
        print(f"   → View: {match.func.__name__ if hasattr(match.func, '__name__') else match.func}")
    except Resolver404:
        print(f"❌ {endpoint} - NOT FOUND")
        all_passed = False

print("=" * 60)
if all_passed:
    print("\n✅ All endpoints configured correctly!\n")
    sys.exit(0)
else:
    print("\n❌ Some endpoints are missing!\n")
    sys.exit(1)
