"""
Custom middleware for tableicty Transfer Agent platform.
"""
from django.http import HttpResponse


class HealthCheckMiddleware:
    """
    Middleware to handle health check endpoints for App Runner.
    
    This middleware short-circuits health check requests and returns an
    immediate 200 OK response BEFORE SecurityMiddleware can redirect to HTTPS.
    
    App Runner's health checker uses plain HTTP and doesn't follow redirects,
    so we need to respond before any redirect logic runs.
    """
    
    HEALTH_CHECK_PATHS = (
        '/api/v1/shareholder/health',
        '/api/v1/shareholder/health/',
        '/api/v1/health',
        '/api/v1/health/',
    )
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.path in self.HEALTH_CHECK_PATHS and request.method == 'GET':
            return HttpResponse("OK", content_type="text/plain", status=200)
        
        return self.get_response(request)
