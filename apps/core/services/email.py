"""
Email service for sending transactional emails via AWS SES.
"""
import logging
from typing import Optional, Dict, Any
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
logger = logging.getLogger(__name__)
class EmailService:
    """Service for sending transactional emails."""
    
    @staticmethod
    def send_email(
        to_email: str,
        subject: str,
        template_name: str,
        context: Dict[str, Any],
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> bool:
        """
        Send an email using a template.
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            template_name: Name of the template file (without .html)
            context: Template context dictionary
            from_email: Optional sender email (defaults to settings.DEFAULT_FROM_EMAIL)
            reply_to: Optional reply-to address
            
        Returns:
            True if email sent successfully, False otherwise
        """
        # Check if email is globally disabled (useful when VPC blocks SES)
        if not getattr(settings, 'EMAIL_ENABLED', True):
            logger.info(f"Email disabled globally (EMAIL_ENABLED=false). Skipping email to {to_email}: {subject}")
            return False
        
        try:
            from_name = getattr(settings, 'EMAIL_FROM_NAME', 'Tableicty')
            sender = from_email or settings.DEFAULT_FROM_EMAIL
            formatted_from = f"{from_name} <{sender}>"
            
            context['frontend_url'] = getattr(settings, 'FRONTEND_URL', 'https://tableicty.com')
            context['support_email'] = 'support@tableicty.com'
            context['current_year'] = 2025
            
            html_content = render_to_string(f'emails/{template_name}.html', context)
            text_content = strip_tags(html_content)
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=formatted_from,
                to=[to_email],
                reply_to=[reply_to] if reply_to else None,
            )
            email.attach_alternative(html_content, 'text/html')
            
            email.send(fail_silently=False)
            
            logger.info(f"Email sent successfully to {to_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}", exc_info=True)
            raise
Key change is lines 40-43 (the EMAIL_E
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}", exc_info=True)
            raise
    
    @classmethod
    def send_shareholder_invitation(
        cls,
        email: str,
        shareholder_name: str,
        company_name: str,
        share_count: int,
        share_class: str,
        invite_token: str,
        tenant_name: Optional[str] = None,
    ) -> bool:
        """
        Send shareholder invitation email when shares are issued.
        
        Args:
            email: Shareholder's email address
            shareholder_name: Full name of the shareholder
            company_name: Name of the issuing company
            share_count: Number of shares issued
            share_class: Class of shares (e.g., "Common Stock Class A")
            invite_token: JWT token for registration
            tenant_name: Optional tenant/platform name for branding
            
        Returns:
            True if email sent successfully
        """
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://tableicty.com')
        registration_link = f"{frontend_url}/register?token={invite_token}"
        
        context = {
            'shareholder_name': shareholder_name,
            'company_name': company_name,
            'share_count': f"{share_count:,}",
            'share_class': share_class,
            'registration_link': registration_link,
            'tenant_name': tenant_name or 'Tableicty',
        }
        
        subject = f"You've been issued shares in {company_name}"
        
        return cls.send_email(
            to_email=email,
            subject=subject,
            template_name='shareholder_invitation',
            context=context,
        )
    
    @classmethod
    def send_test_email(cls, to_email: str) -> bool:
        """
        Send a test email to verify SES configuration.
        
        Args:
            to_email: Recipient email address
            
        Returns:
            True if email sent successfully
        """
        context = {
            'test_message': 'This is a test email from Tableicty to verify email delivery is working correctly.',
        }
        
        return cls.send_email(
            to_email=to_email,
            subject='Tableicty Email Test - Configuration Verified',
            template_name='test_email',
            context=context,
        )
    
    @classmethod
    def send_welcome_email(
        cls,
        email: str,
        first_name: str,
        company_name: Optional[str] = None,
    ) -> bool:
        """
        Send welcome email after successful registration.
        
        Args:
            email: User's email address
            first_name: User's first name
            company_name: Optional company name for context
            
        Returns:
            True if email sent successfully
        """
        context = {
            'first_name': first_name,
            'company_name': company_name,
        }
        
        return cls.send_email(
            to_email=email,
            subject='Welcome to Tableicty',
            template_name='welcome',
            context=context,
        )
    
    @classmethod
    def send_share_update_notification(
        cls,
        email: str,
        shareholder_name: str,
        company_name: str,
        additional_shares,
        total_shares,
        share_class: str,
        tenant_name: Optional[str] = None,
    ) -> bool:
        """
        Send notification to existing shareholder when additional shares are granted.
        
        Args:
            email: Shareholder's email address
            shareholder_name: Full name of the shareholder
            company_name: Name of the issuing company
            additional_shares: Number of new shares granted (Decimal, int, or float)
            total_shares: New total share count (Decimal, int, or float)
            share_class: Class of shares (e.g., "Common Stock Class A")
            tenant_name: Optional tenant/platform name for branding
            
        Returns:
            True if email sent successfully
        """
        from decimal import Decimal
        
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://tableicty.com')
        dashboard_link = f"{frontend_url}/dashboard/holdings"
        
        def format_shares(value):
            """Format share count, removing unnecessary decimals for whole numbers."""
            dec_val = Decimal(str(value))
            if dec_val == dec_val.to_integral_value():
                return f"{int(dec_val):,}"
            normalized = dec_val.normalize()
            return f"{normalized:,}"
        
        context = {
            'shareholder_name': shareholder_name,
            'company_name': company_name,
            'additional_shares': format_shares(additional_shares),
            'total_shares': format_shares(total_shares),
            'share_class': share_class,
            'dashboard_link': dashboard_link,
            'tenant_name': tenant_name or 'Tableicty',
        }
        
        subject = f"Share Update: You've received additional shares in {company_name}"
        
        return cls.send_email(
            to_email=email,
            subject=subject,
            template_name='share_update',
            context=context,
        )
    
    @classmethod
    def send_share_update_or_invitation(
        cls,
        shareholder,
        issuer,
        additional_shares: int,
        total_shares: int,
        tenant_name: Optional[str] = None,
    ) -> bool:
        """
        Smart email method: sends share update to existing users, or invitation to new users.
        
        Args:
            shareholder: Shareholder model instance
            issuer: Issuer model instance
            additional_shares: Number of new shares granted
            total_shares: New total share count
            tenant_name: Optional tenant/platform name for branding
            
        Returns:
            True if email sent successfully
        """
        if not shareholder.email:
            logger.warning(f"Cannot send email - shareholder {shareholder.id} has no email")
            return False
        
        shareholder_name = f"{shareholder.first_name} {shareholder.last_name}".strip() or "Shareholder"
        company_name = issuer.company_name
        share_class = "Common Stock"
        
        if hasattr(shareholder, 'security_class') and shareholder.security_class:
            share_class = shareholder.security_class.class_designation
        
        if shareholder.user_id:
            logger.info(f"Shareholder {shareholder.email} has account - sending share update notification")
            return cls.send_share_update_notification(
                email=shareholder.email,
                shareholder_name=shareholder_name,
                company_name=company_name,
                additional_shares=additional_shares,
                total_shares=total_shares,
                share_class=share_class,
                tenant_name=tenant_name,
            )
        else:
            logger.info(f"Shareholder {shareholder.email} has no account - sending invitation")
            from apps.core.services.invite_tokens import ShareholderInviteToken
            
            tenant_id = str(shareholder.tenant_id) if hasattr(shareholder, 'tenant_id') and shareholder.tenant_id else ''
            
            token = ShareholderInviteToken.for_shareholder(
                shareholder_id=str(shareholder.id),
                email=shareholder.email,
                tenant_id=tenant_id,
                company_id=str(issuer.id),
                company_name=company_name,
                share_count=additional_shares,
                share_class=share_class,
            )
            invite_token = str(token)
            
            return cls.send_shareholder_invitation(
                email=shareholder.email,
                shareholder_name=shareholder_name,
                company_name=company_name,
                share_count=additional_shares,
                share_class=share_class,
                invite_token=invite_token,
                tenant_name=tenant_name,
            )
    
    @classmethod
    def send_certificate_request_admin_alert(
        cls,
        to_emails: list,
        shareholder_name: str,
        shareholder_email: str,
        conversion_type: str,
        share_quantity,
        issuer_name: str,
        request_date: str,
        tenant_name: Optional[str] = None,
    ) -> int:
        """
        Send notification to admins when a certificate request is submitted.
        
        Args:
            to_emails: List of admin email addresses
            shareholder_name: Name of shareholder making request
            shareholder_email: Email of shareholder
            conversion_type: Type of conversion (DRS_TO_CERT or CERT_TO_DRS)
            share_quantity: Number of shares in request
            issuer_name: Name of the issuing company
            request_date: Date request was submitted
            tenant_name: Optional tenant/platform name
            
        Returns:
            Number of emails sent successfully
        """
        conversion_display = {
            'DRS_TO_CERT': 'DRS to Physical Certificate',
            'CERT_TO_DRS': 'Physical Certificate to DRS'
        }.get(conversion_type, conversion_type)
        
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://tableicty.com')
        admin_link = f"{frontend_url}/dashboard/shareholders"
        
        context = {
            'shareholder_name': shareholder_name,
            'shareholder_email': shareholder_email,
            'conversion_type': conversion_display,
            'share_quantity': f"{share_quantity:,}" if isinstance(share_quantity, int) else str(share_quantity),
            'issuer_name': issuer_name,
            'request_date': request_date,
            'admin_link': admin_link,
            'tenant_name': tenant_name or 'Tableicty',
        }
        
        subject = f"New Certificate Request from {shareholder_name}"
        sent_count = 0
        
        for email in to_emails:
            try:
                cls.send_email(
                    to_email=email,
                    subject=subject,
                    template_name='certificate_request_admin',
                    context=context,
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send admin alert to {email}: {e}")
        
        return sent_count
    
    @classmethod
    def send_certificate_approved(
        cls,
        to_email: str,
        shareholder_name: str,
        certificate_number: str,
        share_quantity,
        issuer_name: str,
        conversion_type: str,
        pdf_download_url: Optional[str] = None,
        tenant_name: Optional[str] = None,
    ) -> bool:
        """
        Send notification to shareholder when certificate request is approved.
        
        Args:
            to_email: Shareholder email address
            shareholder_name: Name of shareholder
            certificate_number: Assigned certificate number
            share_quantity: Number of shares
            issuer_name: Name of the issuing company
            conversion_type: Type of conversion
            pdf_download_url: Optional URL to download PDF certificate
            tenant_name: Optional tenant/platform name
            
        Returns:
            True if email sent successfully
        """
        conversion_display = {
            'DRS_TO_CERT': 'DRS to Physical Certificate',
            'CERT_TO_DRS': 'Physical Certificate to DRS'
        }.get(conversion_type, conversion_type)
        
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://tableicty.com')
        dashboard_link = f"{frontend_url}/dashboard/certificates"
        
        context = {
            'shareholder_name': shareholder_name,
            'certificate_number': certificate_number,
            'share_quantity': f"{share_quantity:,}" if isinstance(share_quantity, int) else str(share_quantity),
            'issuer_name': issuer_name,
            'conversion_type': conversion_display,
            'pdf_download_url': pdf_download_url,
            'dashboard_link': dashboard_link,
            'tenant_name': tenant_name or 'Tableicty',
        }
        
        subject = f"Your Stock Certificate Has Been Issued - {certificate_number}"
        
        return cls.send_email(
            to_email=to_email,
            subject=subject,
            template_name='certificate_approved',
            context=context,
        )
    
    @classmethod
    def send_certificate_rejected(
        cls,
        to_email: str,
        shareholder_name: str,
        share_quantity,
        issuer_name: str,
        conversion_type: str,
        rejection_reason: str,
        admin_notes: Optional[str] = None,
        tenant_name: Optional[str] = None,
    ) -> bool:
        """
        Send notification to shareholder when certificate request is rejected.
        
        Args:
            to_email: Shareholder email address
            shareholder_name: Name of shareholder
            share_quantity: Number of shares
            issuer_name: Name of the issuing company
            conversion_type: Type of conversion
            rejection_reason: Reason for rejection
            admin_notes: Optional notes from admin
            tenant_name: Optional tenant/platform name
            
        Returns:
            True if email sent successfully
        """
        conversion_display = {
            'DRS_TO_CERT': 'DRS to Physical Certificate',
            'CERT_TO_DRS': 'Physical Certificate to DRS'
        }.get(conversion_type, conversion_type)
        
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://tableicty.com')
        dashboard_link = f"{frontend_url}/dashboard/certificates"
        
        context = {
            'shareholder_name': shareholder_name,
            'share_quantity': f"{share_quantity:,}" if isinstance(share_quantity, int) else str(share_quantity),
            'issuer_name': issuer_name,
            'conversion_type': conversion_display,
            'rejection_reason': rejection_reason,
            'admin_notes': admin_notes,
            'dashboard_link': dashboard_link,
            'tenant_name': tenant_name or 'Tableicty',
        }
        
        subject = "Certificate Request Update - Action Required"
        
        return cls.send_email(
            to_email=to_email,
            subject=subject,
            template_name='certificate_rejected',
            context=context,
        )
