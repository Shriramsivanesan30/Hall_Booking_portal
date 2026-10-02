from django.urls import path
from apps.approvals import views

app_name = 'approvals'

urlpatterns = [
    path('pending/', views.pending_approvals_list_view, name='pending_list'),
    path('<str:booking_id>/action/', views.approval_action_view, name='action'),
]
