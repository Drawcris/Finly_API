from django.urls import path, include
from rest_framework import routers
from .serializers import TransactionSerializer, CategorySerializer, BudgetSerializer
from .views import (
        TransactionView, CategoryView, BudgetView, RegisterView,
        UserView, StatisticsView, ExportCSVView, ExportPDFView, TransactionListView,CategoryListView)

router = routers.DefaultRouter()
router.register(r'transactions',TransactionView, basename='transaction')
router.register(r'categories', CategoryView, basename='category')
router.register(r'budgets', BudgetView, basename='budget')
router.register(r'register', RegisterView, basename='register')
router.register(r'users', UserView)

urlpatterns = [
        path('', include(router.urls)),
        path('statistics/', StatisticsView.as_view(), name='statistics'),
        path('export-csv/', ExportCSVView.as_view(), name='export-csv'),
        path('export-pdf/', ExportPDFView.as_view(), name='export-pdf'),
        path('transaction-list/', TransactionListView.as_view(), name='transaction-list'),
        path('category-list/', CategoryListView.as_view(), name='category-list'),

]
