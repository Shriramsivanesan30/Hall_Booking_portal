from django.urls import path
from apps.reports import views

app_name = 'reports'

urlpatterns = [
    path('', views.reports_dashboard_view, name='dashboard'),
    path('export/excel/', views.export_excel_report, name='export_excel'),
]
