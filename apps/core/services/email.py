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
        additional_shares: int,
        total_shares: int,
        share_class: str,
        tenant_name: Optional[str] = None,
    ) -> bool:
        """
        Send notification to existing shareholder when additional shares are granted.
        
        Args:
            email: Shareholder's email address
            shareholder_name: Full name of the shareholder
            company_name: Name of the issuing company
            additional_shares: Number of new shares granted
            total_shares: New total share count
            share_class: Class of shares (e.g., "Common Stock Class A")
            tenant_name: Optional tenant/platform name for branding
            
        Returns:
            True if email sent successfully
        """
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://tableicty.com')
        dashboard_link = f"{frontend_url}/dashboard/holdings"
        
        context = {
            'shareholder_name': shareholder_name,
            'company_name': company_name,
            'additional_shares': f"{additional_shares:,}",
            'total_shares': f"{total_shares:,}",
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
