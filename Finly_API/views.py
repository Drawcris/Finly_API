import csv
from calendar import month
from collections import defaultdict
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from django.db.models import Sum, Q
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.timezone import now
from reportlab.pdfgen import canvas
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import date, timedelta
from unicodedata import category
from .serializers import TransactionSerializer, CategorySerializer, BudgetSerializer, RegisterSerializer, UserSerializer
from .models import Transaction, Budget, Category
from django.contrib.auth.models import User
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics



# Create your views here.
class TransactionView(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_param = self.request.query_params.get('user')
        if user_param:
            return Transaction.objects.filter(user__username=user_param)
        return Transaction.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

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

class StatisticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        category_name = request.query_params.get('category')
        month_param = request.query_params.get('month')
        type_param = request.query_params.get('type')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        transactions = Transaction.objects.filter(user=user).select_related('category')

        # Parse daty
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        # Filtry
        if start_date:
            transactions = transactions.filter(date__gte=start_date)
        if end_date:
            transactions = transactions.filter(date__lte=end_date)
        if category_name:
            transactions = transactions.filter(category__name=category_name)
        if month_param:
            try:
                year, month = map(int, month_param.split('-'))
                transactions = transactions.filter(date__year=year, date__month=month)
            except:
                return Response({'error': "Invalid month format. Use YYYY-MM"}, status=400)
        if type_param in ['income', 'expense']:
            transactions = transactions.filter(type=type_param)

        # Statystyki
        total_income = transactions.filter(type='income').aggregate(total=Sum('amount'))['total'] or 0
        total_expense = transactions.filter(type='expense').aggregate(total=Sum('amount'))['total'] or 0
        balance = total_income - total_expense

        # Ostatnie 30 dni (również na bazie filtrowanych danych)
        today = date.today()
        last_30_days = today - timedelta(days=30)
        recent_income = transactions.filter(type='income', date__gte=last_30_days).aggregate(total=Sum('amount'))['total'] or 0
        recent_expense = transactions.filter(type='expense', date__gte=last_30_days).aggregate(total=Sum('amount'))['total'] or 0

        # By category
        category_data = defaultdict(lambda: {'income': 0, 'expense': 0, 'icon': ''})
        for transaction in transactions:
            if transaction.category:
                category_data[transaction.category.name]['icon'] = transaction.category.icon
                category_data[transaction.category.name][transaction.type] += transaction.amount

        # Monthly
        monthly_data = defaultdict(lambda: {'income': 0, 'expense': 0})
        monthly_transactions = transactions.annotate(month=TruncMonth('date'))
        for transaction in monthly_transactions:
            key = transaction.date.strftime('%Y-%m')
            monthly_data[key][transaction.type] += transaction.amount

        # Most expense category
        most_expense_category = transactions.filter(type='expense').values('category__name').annotate(total=Sum('amount')).order_by('-total')[:1]
        most_expense_category = most_expense_category[0]['category__name'] if most_expense_category else None
        most_expense_category_amount = transactions.filter(type='expense', category__name=most_expense_category).aggregate(total=Sum('amount'))['total'] or 0
        most_expense_category_icon = Category.objects.filter(name=most_expense_category).first().icon if most_expense_category else None

        return Response({
            "balance": balance,
            "last_30_days": {
                "income": recent_income,
                "expense": recent_expense
            },
            "by_category": category_data,
            "most_expense_category": {
                "name": most_expense_category,
                "amount": most_expense_category_amount,
                "icon": most_expense_category_icon
            },
            "monthly": monthly_data
        })


class ExportCSVView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        transactions = Transaction.objects.filter(user=user).select_related('category')

        # Obliczanie podsumowania
        total_income = transactions.filter(type='income').aggregate(total=Sum('amount'))['total'] or 0
        total_expense = transactions.filter(type='expense').aggregate(total=Sum('amount'))['total'] or 0
        balance = total_income - total_expense

        # Obliczanie wydatków na kategorie
        category_expenses = transactions.filter(type='expense').values('category__name').annotate(total=Sum('amount'))

        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="finly_summary_{now().date()}.csv"'

        writer = csv.writer(response, delimiter=';')

        # Dodanie podsumowania
        writer.writerow(['Podsumowanie'])
        writer.writerow(['Przychody', f"{total_income:.2f}"])
        writer.writerow(['Wydatki', f"{total_expense:.2f}"])
        writer.writerow(['Bilans', f"{balance:.2f}"])
        writer.writerow([])

        # Dodanie wydatków na kategorie
        writer.writerow(['Wydatki na kategorie'])
        for category in category_expenses:
            writer.writerow([category['category__name'], f"{category['total']:.2f}"])
        writer.writerow([])

        # Dodanie nagłówków i transakcji
        writer.writerow(['Data', 'Typ', 'Kategoria', 'Kwota', 'Opis'])
        for t in transactions:
            writer.writerow([
                t.date,
                t.type,
                t.category.name if t.category else '',
                f"{t.amount:.2f}",
                t.description or ''
            ])

        return response

class ExportPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        transactions = Transaction.objects.filter(user=user).select_related('category')

        # Obliczanie podsumowania
        total_income = transactions.filter(type='income').aggregate(total=Sum('amount'))['total'] or 0
        total_expense = transactions.filter(type='expense').aggregate(total=Sum('amount'))['total'] or 0
        balance = total_income - total_expense

        # Obliczanie wydatków na kategorie
        category_expenses = transactions.filter(type='expense').values('category__name').annotate(total=Sum('amount'))

        # Rejestracja czcionek obsługujących polskie znaki
        pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
        pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))  # Pogrubiona wersja

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        y = height - 50

        # Ustawienie czcionki
        p.setFont("Arial-Bold", 16)
        p.drawString(50, y, f"Finly - Podsumowanie dla {user.username}")
        y -= 40

        p.setFont("Arial", 12)
        p.drawString(50, y, f"Przychody: {total_income:.2f} zł")
        y -= 20
        p.drawString(50, y, f"Wydatki: {total_expense:.2f} zł")
        y -= 20
        p.drawString(50, y, f"Bilans: {balance:.2f} zł")
        y -= 40

        # Dodanie wydatków na kategorie
        p.setFont("Arial-Bold", 14)
        p.drawString(50, y, "Wydatki na kategorie:")
        y -= 30

        p.setFont("Arial", 12)
        for category in category_expenses:
            p.drawString(50, y, f"{category['category__name']}: {category['total']:.2f} zł")
            y -= 20
            if y < 50:
                p.showPage()
                y = height - 50

        # Dodanie historii transakcji
        p.setFont("Arial-Bold", 14)
        p.drawString(50, y, "Historia transakcji:")
        y -= 30

        p.setFont("Arial", 12)
        for t in transactions:
            line = f"{t.date} | {t.amount} zł | {t.type} | {t.category.name if t.category else ''} | {t.description}"
            if y < 50:
                p.showPage()
                y = height - 50
            p.drawString(50, y, line)
            y -= 20

        p.showPage()
        p.save()

        buffer.seek(0)
        return HttpResponse(buffer, content_type='application/pdf', headers={
            'Content-Disposition': f'attachment; filename="finly_summary_{now().date()}.pdf"'
        })

class TransactionListView(APIView):
    def get(self, request):
        user = request.user
        type_param = request.query_params.get('type')
        category_param = request.query_params.get('category')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        order_by = request.query_params.get('order_by')


        transactions = Transaction.objects.filter(user=user).select_related('category')

        if type_param in ['income', 'expense']:
            transactions = transactions.filter(type=type_param)

        if category_param:
            try:
                category_id = int(category_param)
                transactions = transactions.filter(category__id=category_id)
            except ValueError:
                transactions = transactions.filter(category__name=category_param)

        if start_date_str:
            transactions = transactions.filter(date__gte=start_date_str)
        if end_date_str:
            transactions = transactions.filter(date__lte=end_date_str)


        if order_by == 'highest':
            transactions = transactions.order_by('-amount')
        elif order_by == 'lowest':
            transactions = transactions.order_by('amount')
        else:
            transactions = transactions.order_by("-date")


        serialized = TransactionSerializer(transactions, many=True)
        return Response(serialized.data)


class CategoryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        order_by = request.query_params.get('order_by', 'total_expense')
        order_direction = request.query_params.get('direction', 'desc')

        category_stats = (
            Transaction.objects.filter(user=user)
            .values('category__name', 'category__icon')
            .annotate(
                total_expense=Sum('amount', filter=Q(type='expense')),
                total_income=Sum('amount', filter=Q(type='income')),
            )
        )

        for stat in category_stats:
            stat['total_expense'] = stat.get('total_expense', 0) or 0
            stat['total_income'] = stat.get('total_income', 0) or 0

        if order_direction == 'desc':
            order_by = f"-{order_by}"
        try:
            category_stats = sorted(category_stats, key=lambda x: x.get(order_by.lstrip('-'), 0),
                                    reverse=order_by.startswith('-'))
        except KeyError:
            return Response({"error": f"Invalid sorting field: {order_by}"}, status=400)

        serialized_data = [
            {
                "category": stat['category__name'],
                "icon": stat['category__icon'],
                "total_expense": stat['total_expense'],
                "total_income": stat['total_income']
            }
            for stat in category_stats
        ]

        return Response(serialized_data)



class BudgetSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        budgets = Budget.objects.filter(user=user)

        summary = []
        for budget in budgets:
            start_date = budget.month
            end_month = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
            end_date = end_month - timedelta(days=1)

            spent = Transaction.objects.filter(
                user=user,
                type='expense',
                category=budget.category,
                date__range=(start_date, end_date)
            ).aggregate(total=Sum('amount'))['total'] or 0

            summary.append({
                "id": budget.id,
                "category": budget.category.name if budget.category else "Brak kategorii",
                "icon": budget.category.icon if budget.category else "",
                "month": budget.month.strftime('%Y-%m'),
                "budgeted": float(budget.amount),
                "spent": float(spent),
                "remaining": float(budget.amount - spent),
                "over_budget": spent > budget.amount
            })

        return Response(summary)












