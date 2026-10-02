from django.urls import path
from apps.departments import views

app_name = 'departments'

urlpatterns = [
    path('', views.department_list_view, name='list'),
    path('new/', views.department_create_view, name='create'),
    path('<int:dept_id>/edit/', views.department_edit_view, name='edit'),
]
