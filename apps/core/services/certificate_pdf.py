"""
PDF Certificate Generation Service.

Generates professional stock certificates using ReportLab.
"""
import io
import logging
from datetime import date
from typing import Optional
from decimal import Decimal

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

logger = logging.getLogger(__name__)


class CertificatePDFService:
    """Service for generating PDF stock certificates."""
    
    BORDER_COLOR = HexColor('#1a365d')
    HEADER_COLOR = HexColor('#2563eb')
    TEXT_COLOR = HexColor('#1e293b')
    LIGHT_COLOR = HexColor('#64748b')
    
    @classmethod
    def generate_certificate(
        cls,
        certificate_number: str,
        shareholder_name: str,
        company_name: str,
        share_quantity: int,
        security_type: str = "Common Stock",
        issue_date: Optional[date] = None,
        tenant_name: Optional[str] = None,
    ) -> bytes:
        """
        Generate a PDF stock certificate.
        
        Args:
            certificate_number: Unique certificate number
            shareholder_name: Name of the shareholder
            company_name: Name of the issuing company
            share_quantity: Number of shares
            security_type: Type of security (e.g., "Common Stock")
            issue_date: Date of issuance
            tenant_name: Name of the transfer agent
            
        Returns:
            PDF file as bytes
        """
        buffer = io.BytesIO()
        
        page_size = landscape(letter)
        c = canvas.Canvas(buffer, pagesize=page_size)
        width, height = page_size
        
        cls._draw_border(c, width, height)
        
        cls._draw_header(c, width, height, company_name)
        
        cls._draw_certificate_body(
            c, width, height,
            certificate_number=certificate_number,
            shareholder_name=shareholder_name,
            share_quantity=share_quantity,
            security_type=security_type,
            issue_date=issue_date or date.today(),
        )
        
        cls._draw_footer(c, width, height, tenant_name or "Tableicty Transfer Agent")
        
        c.save()
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    @classmethod
    def _draw_border(cls, c: canvas.Canvas, width: float, height: float):
        """Draw decorative certificate border."""
        margin = 0.5 * inch
        inner_margin = 0.7 * inch
        
        c.setStrokeColor(cls.BORDER_COLOR)
        c.setLineWidth(3)
        c.rect(margin, margin, width - 2*margin, height - 2*margin)
        
        c.setLineWidth(1)
        c.rect(inner_margin, inner_margin, width - 2*inner_margin, height - 2*inner_margin)
        
        corner_size = 0.3 * inch
        corners = [
            (margin + corner_size, height - margin - corner_size),
            (width - margin - corner_size, height - margin - corner_size),
            (margin + corner_size, margin + corner_size),
            (width - margin - corner_size, margin + corner_size),
        ]
        
        for x, y in corners:
            c.setFillColor(cls.BORDER_COLOR)
            c.circle(x, y, 4, fill=1)
    
    @classmethod
    def _draw_header(cls, c: canvas.Canvas, width: float, height: float, company_name: str):
        """Draw certificate header with company name."""
        c.setFillColor(cls.HEADER_COLOR)
        c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(width/2, height - 1.5*inch, company_name.upper())
        
        c.setFont("Helvetica", 14)
        c.setFillColor(cls.LIGHT_COLOR)
        c.drawCentredString(width/2, height - 1.9*inch, "STOCK CERTIFICATE")
    
    @classmethod
    def _draw_certificate_body(
        cls,
        c: canvas.Canvas,
        width: float,
        height: float,
        certificate_number: str,
        shareholder_name: str,
        share_quantity: int,
        security_type: str,
        issue_date: date,
    ):
        """Draw main certificate content."""
        c.setFont("Helvetica", 12)
        c.setFillColor(cls.LIGHT_COLOR)
        c.drawString(1.2*inch, height - 2.5*inch, "Certificate No:")
        c.setFillColor(cls.TEXT_COLOR)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2.5*inch, height - 2.5*inch, certificate_number)
        
        c.setFont("Helvetica", 12)
        c.setFillColor(cls.LIGHT_COLOR)
        c.drawString(width - 3.5*inch, height - 2.5*inch, "Issue Date:")
        c.setFillColor(cls.TEXT_COLOR)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(width - 2.2*inch, height - 2.5*inch, issue_date.strftime("%B %d, %Y"))
        
        c.setFont("Helvetica", 14)
        c.setFillColor(cls.TEXT_COLOR)
        c.drawCentredString(width/2, height - 3.2*inch, "This certifies that")
        
        c.setFont("Helvetica-Bold", 22)
        c.setFillColor(cls.HEADER_COLOR)
        c.drawCentredString(width/2, height - 3.8*inch, shareholder_name)
        
        c.setStrokeColor(cls.LIGHT_COLOR)
        c.setLineWidth(0.5)
        c.line(2*inch, height - 4.0*inch, width - 2*inch, height - 4.0*inch)
        
        c.setFont("Helvetica", 14)
        c.setFillColor(cls.TEXT_COLOR)
        c.drawCentredString(width/2, height - 4.5*inch, "is the registered owner of")
        
        formatted_shares = f"{share_quantity:,}"
        c.setFont("Helvetica-Bold", 36)
        c.setFillColor(cls.HEADER_COLOR)
        c.drawCentredString(width/2, height - 5.3*inch, formatted_shares)
        
        c.setFont("Helvetica-Bold", 16)
        c.setFillColor(cls.TEXT_COLOR)
        c.drawCentredString(width/2, height - 5.8*inch, f"SHARES OF {security_type.upper()}")
        
        c.setFont("Helvetica", 11)
        c.setFillColor(cls.LIGHT_COLOR)
        legal_text = (
            "This certificate is transferable only on the books of the Corporation by the holder hereof in person "
            "or by duly authorized attorney upon surrender of this Certificate properly endorsed."
        )
        lines = simpleSplit(legal_text, "Helvetica", 11, width - 3*inch)
        y = height - 6.5*inch
        for line in lines:
            c.drawCentredString(width/2, y, line)
            y -= 14
    
    @classmethod
    def _draw_footer(cls, c: canvas.Canvas, width: float, height: float, tenant_name: str):
        """Draw certificate footer with transfer agent info."""
        sig_y = 1.8 * inch
        
        c.setStrokeColor(cls.LIGHT_COLOR)
        c.setLineWidth(0.5)
        c.line(1.5*inch, sig_y, 4*inch, sig_y)
        c.line(width - 4*inch, sig_y, width - 1.5*inch, sig_y)
        
        c.setFont("Helvetica", 10)
        c.setFillColor(cls.LIGHT_COLOR)
        c.drawCentredString(2.75*inch, sig_y - 0.2*inch, "Authorized Signature")
        c.drawCentredString(width - 2.75*inch, sig_y - 0.2*inch, "Corporate Secretary")
        
        c.setFont("Helvetica", 9)
        c.drawCentredString(width/2, 0.8*inch, f"Transfer Agent: {tenant_name}")
        c.drawCentredString(width/2, 0.6*inch, "This certificate is issued in book-entry form")


def generate_certificate_pdf(cert_request) -> bytes:
    """
    Convenience function to generate PDF from a CertificateRequest model instance.
    
    Args:
        cert_request: CertificateRequest model instance
        
    Returns:
        PDF file as bytes
    """
    shareholder = cert_request.shareholder
    if shareholder.account_type == 'ENTITY':
        shareholder_name = shareholder.entity_name or shareholder.email
    else:
        shareholder_name = f"{shareholder.first_name} {shareholder.last_name}".strip() or shareholder.email
    
    return CertificatePDFService.generate_certificate(
        certificate_number=cert_request.certificate_number or f"CERT-{str(cert_request.id)[:8].upper()}",
        shareholder_name=shareholder_name,
        company_name=cert_request.holding.issuer.company_name,
        share_quantity=int(cert_request.share_quantity),
        security_type=cert_request.holding.security_class.class_designation if cert_request.holding.security_class else "Common Stock",
        issue_date=cert_request.processed_at.date() if cert_request.processed_at else None,
        tenant_name=cert_request.tenant.name if cert_request.tenant else None,
    )
