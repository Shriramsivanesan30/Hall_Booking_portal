from django.urls import path
from apps.halls import views

app_name = 'halls'

urlpatterns = [
    path('', views.hall_list_view, name='list'),
    path('new/', views.hall_create_view, name='create'),
    path('<int:hall_id>/', views.hall_detail_view, name='detail'),
    path('<int:hall_id>/edit/', views.hall_edit_view, name='edit'),
    path('<int:hall_id>/maintenance/', views.hall_maintenance_toggle_view, name='maintenance_toggle'),
    path('<int:hall_id>/history/', views.hall_history_view, name='history'),
]
