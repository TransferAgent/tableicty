from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.management import call_command
from apps.core.models import Issuer, Holding, Certificate
from django.utils import timezone
from .views import (
    IssuerViewSet, SecurityClassViewSet, ShareholderViewSet,
    HoldingViewSet, CertificateViewSet, TransferViewSet, AuditLogViewSet,
    CertificateRequestViewSet
)

router = DefaultRouter()
router.register(r'issuers', IssuerViewSet)
router.register(r'security-classes', SecurityClassViewSet)
router.register(r'shareholders', ShareholderViewSet)
router.register(r'holdings', HoldingViewSet)
router.register(r'certificates', CertificateViewSet)
router.register(r'transfers', TransferViewSet)
router.register(r'audit-logs', AuditLogViewSet)
router.register(r'certificate-requests', CertificateRequestViewSet)


@api_view(['GET'])
def health_check(request):
    """API health check endpoint"""
    return Response({
        'status': 'ok',
        'version': '1.0.0',
        'service': 'tableicty Transfer Agent API'
    })


@api_view(['POST'])
def tavs_report(request):
    """Generate TAVS report for an issuer"""
    issuer_id = request.data.get('issuer_id')
    
    if not issuer_id:
        return Response({'error': 'issuer_id required'}, status=400)
    
    try:
        issuer = Issuer.objects.get(id=issuer_id)
    except Issuer.DoesNotExist:
        return Response({'error': 'Issuer not found'}, status=404)
    
    holdings = Holding.objects.filter(issuer=issuer)
    certificates = Certificate.objects.filter(issuer=issuer)
    
    total_issued = sum(h.share_quantity for h in holdings)
    total_restricted = sum(h.share_quantity for h in holdings if h.is_restricted)
    total_unrestricted = total_issued - total_restricted
    
    shareholder_count = holdings.values('shareholder').distinct().count()
    certificate_count = certificates.filter(status='OUTSTANDING').count()
    drs_count = holdings.filter(holding_type='DRS').count()
    
    report = {
        'issuer': {
            'company_name': issuer.company_name,
            'ticker_symbol': issuer.ticker_symbol,
            'cusip': issuer.cusip,
            'cik': issuer.cik,
        },
        'report_date': timezone.now().date().isoformat(),
        'shares_authorized': float(issuer.total_authorized_shares),
        'shares_issued': float(total_issued),
        'shares_outstanding': float(total_issued),
        'shares_restricted': float(total_restricted),
        'shares_unrestricted': float(total_unrestricted),
        'shareholder_count': shareholder_count,
        'shareholders_of_record': shareholder_count,
        'certificate_count': certificate_count,
        'drs_count': drs_count,
        'tavs_enabled': issuer.tavs_enabled,
        'otc_tier': issuer.otc_tier,
    }
    
    return Response(report)


urlpatterns = [
    path('health/', health_check, name='health-check'),
    path('reports/tavs/', tavs_report, name='tavs-report'),
    path('', include(router.urls)),
]
