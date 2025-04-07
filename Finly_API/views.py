from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import TransactionSerializer, CategorySerializer, BudgetSerializer, RegisterSerializer, UserSerializer
from .models import Transaction, Budget, Category
from django.contrib.auth.models import User

# Create your views here.



class TransactionView(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

class CategoryView(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

class BudgetView(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]


    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

class RegisterView(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

class UserView(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer






