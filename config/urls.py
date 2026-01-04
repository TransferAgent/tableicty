from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.api.urls')),
    path('api/v1/shareholder/', include('apps.shareholder.urls')),
    path('api/v1/tenant/', include('apps.core.urls')),
    path('api/v1/deal-desk/', include('apps.deal_desk.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

admin.site.site_header = "tableicty Transfer Agent Admin"
admin.site.site_title = "Transfer Agent Portal"
admin.site.index_title = "Welcome to tableicty Transfer Agent Platform"
