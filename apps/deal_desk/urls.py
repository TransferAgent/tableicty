"""
Deal Desk URL Configuration.

Provides URL routing for term sheet analysis API endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.deal_desk.views import DealDeskViewSet

router = DefaultRouter()
router.register(r'analyses', DealDeskViewSet, basename='deal-desk-analyses')

app_name = 'deal_desk'

urlpatterns = [
    path('', include(router.urls)),
]
