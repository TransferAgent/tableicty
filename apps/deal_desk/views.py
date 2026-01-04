"""
Deal Desk API Views.

Provides ViewSet for term sheet analysis operations.
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.http import FileResponse

from apps.deal_desk.models import TermSheetAnalysis
from apps.deal_desk.serializers import (
    TermSheetAnalysisListSerializer,
    TermSheetAnalysisDetailSerializer,
    TermSheetAnalysisCreateSerializer,
)

logger = logging.getLogger(__name__)


class DealDeskViewSet(viewsets.ModelViewSet):
    """
    API endpoints for Deal Desk term sheet analysis.
    
    Endpoints:
    - POST /api/v1/deal-desk/analyses/ - Upload and analyze term sheet
    - GET /api/v1/deal-desk/analyses/ - List all analyses for tenant
    - GET /api/v1/deal-desk/analyses/{id}/ - Get detailed analysis
    - GET /api/v1/deal-desk/analyses/{id}/download/ - Download original PDF
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = 'id'
    
    def get_queryset(self):
        """Filter analyses to current tenant only."""
        user = self.request.user
        
        if not hasattr(user, 'tenant') or not user.tenant:
            return TermSheetAnalysis.objects.none()
        
        return TermSheetAnalysis.objects.filter(
            tenant=user.tenant
        ).select_related('created_by').prefetch_related('red_flags', 'scenarios').order_by('-created_at')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return TermSheetAnalysisCreateSerializer
        elif self.action == 'list':
            return TermSheetAnalysisListSerializer
        else:
            return TermSheetAnalysisDetailSerializer
    
    def get_serializer_context(self):
        """Add tenant to serializer context."""
        context = super().get_serializer_context()
        if hasattr(self.request.user, 'tenant'):
            context['tenant'] = self.request.user.tenant
        return context
    
    def create(self, request, *args, **kwargs):
        """
        Upload term sheet PDF and initiate analysis.
        
        POST /api/v1/deal-desk/analyses/
        
        Request: multipart/form-data
        - term_sheet_file: PDF file (required)
        - user_notes: string (optional)
        
        Response:
        - 201: Analysis created, processing started
        - 400: Validation error (not PDF, too large)
        - 403: Usage limit exceeded
        """
        if not self._check_usage_limit(request.user):
            return Response(
                {'error': 'Usage limit exceeded for your subscription plan.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        analysis = serializer.save()
        
        logger.info(
            f"Created analysis {analysis.id} for tenant {analysis.tenant_id} "
            f"by user {request.user.id}"
        )
        
        response_serializer = TermSheetAnalysisDetailSerializer(analysis)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    def _check_usage_limit(self, user):
        """
        Check if user/tenant has exceeded their analysis limit.
        
        Limits:
        - FREE: 1 total
        - STARTER: 3 per year
        - PROFESSIONAL: Unlimited
        """
        if not hasattr(user, 'tenant') or not user.tenant:
            return False
        
        tenant = user.tenant
        
        limits = {
            'FREE': 1,
            'STARTER': 3,
            'PROFESSIONAL': float('inf'),
        }
        
        plan = getattr(tenant, 'subscription_plan', 'FREE')
        if plan is None:
            plan = 'FREE'
        
        plan_limit = limits.get(plan.upper(), limits['FREE'])
        
        if plan_limit == float('inf'):
            return True
        
        if plan.upper() == 'FREE':
            current_count = TermSheetAnalysis.objects.filter(
                tenant=tenant
            ).count()
        else:
            current_year = timezone.now().year
            current_count = TermSheetAnalysis.objects.filter(
                tenant=tenant,
                created_at__year=current_year
            ).count()
        
        return current_count < plan_limit
    
    @action(detail=True, methods=['get'], url_path='pdf')
    def pdf(self, request, id=None):
        """
        Download the generated analysis report PDF.
        
        GET /api/v1/deal-desk/analyses/{id}/pdf/
        
        Note: Report PDF is generated after analysis completes.
        Returns 404 if analysis is not complete or report not available.
        """
        analysis = self.get_object()
        
        if analysis.status != 'COMPLETED':
            return Response(
                {'error': 'Analysis is not yet complete. Report PDF is only available after processing.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not hasattr(analysis, 'report_pdf') or not analysis.report_pdf:
            return Response(
                {'error': 'Report PDF not yet generated for this analysis.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            response = FileResponse(
                analysis.report_pdf.open('rb'),
                content_type='application/pdf'
            )
            report_filename = f"analysis_report_{analysis.id}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{report_filename}"'
            return response
        except Exception as e:
            logger.error(f"Error downloading report for analysis {analysis.id}: {e}")
            return Response(
                {'error': 'Failed to download report.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], url_path='original')
    def original(self, request, id=None):
        """
        Download the original uploaded term sheet PDF.
        
        GET /api/v1/deal-desk/analyses/{id}/original/
        """
        analysis = self.get_object()
        
        if not analysis.term_sheet_file:
            return Response(
                {'error': 'No file available for download.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            response = FileResponse(
                analysis.term_sheet_file.open('rb'),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="{analysis.file_name}"'
            return response
        except Exception as e:
            logger.error(f"Error downloading file for analysis {analysis.id}: {e}")
            return Response(
                {'error': 'Failed to download file.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def usage(self, request):
        """
        Get current usage stats for the tenant.
        
        GET /api/v1/deal-desk/analyses/usage/
        
        Response:
        - plan: Current subscription plan
        - limit: Maximum analyses allowed
        - used: Analyses used this period
        - remaining: Analyses remaining
        """
        user = request.user
        
        if not hasattr(user, 'tenant') or not user.tenant:
            return Response(
                {'error': 'No tenant associated with user.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tenant = user.tenant
        plan = getattr(tenant, 'subscription_plan', 'FREE') or 'FREE'
        plan = plan.upper()
        
        limits = {
            'FREE': 1,
            'STARTER': 3,
            'PROFESSIONAL': -1,  # -1 represents unlimited
        }
        
        limit = limits.get(plan, 1)
        
        if plan == 'FREE':
            used = TermSheetAnalysis.objects.filter(tenant=tenant).count()
        else:
            current_year = timezone.now().year
            used = TermSheetAnalysis.objects.filter(
                tenant=tenant,
                created_at__year=current_year
            ).count()
        
        if limit == -1:
            remaining = -1  # unlimited
        else:
            remaining = max(0, limit - used)
        
        return Response({
            'plan': plan,
            'limit': limit,
            'used': used,
            'remaining': remaining,
            'period': 'total' if plan == 'FREE' else 'year',
        })
