from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import viewsets

router = DefaultRouter()
router.register(r'users', viewsets.UserViewSet, basename='user')
router.register(r'wakeup-calls', viewsets.WakeUpCallViewSet, basename='wakeupcall')
router.register(r'call-logs', viewsets.CallLogViewSet, basename='calllog')

urlpatterns = [
    path('', include(router.urls)),
]
