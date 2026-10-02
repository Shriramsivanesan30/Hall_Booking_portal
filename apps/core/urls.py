from django.urls import path
from apps.core import views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/update/', views.update_settings_view, name='update_settings'),
]
