"""
Custom middleware for tableicty Transfer Agent platform.
"""


class HealthCheckBypassSSLRedirectMiddleware:
    """
    Middleware to bypass SSL redirect for health check endpoints.
    
    App Runner's health checker uses plain HTTP and doesn't follow redirects.
    This middleware prevents SecurityMiddleware from redirecting the health
    check to HTTPS, allowing the probe to receive a 200 response.
    """
    
    HEALTH_CHECK_PATHS = [
        '/api/v1/shareholder/health',
        '/api/v1/shareholder/health/',
        '/api/v1/health',
        '/api/v1/health/',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.path in self.HEALTH_CHECK_PATHS:
            request._dont_enforce_ssl_redirect = True
        
        response = self.get_response(request)
        return response
