from django.urls import path
from apps.accounts import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('demo-login/', views.demo_login_view, name='demo_login'),
    path('microsoft/login/', views.microsoft_login_redirect, name='microsoft_login'),
    path('microsoft/callback/', views.microsoft_callback, name='microsoft_callback'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('users/', views.user_management_view, name='user_management'),
    path('users/<int:user_id>/edit/', views.user_edit_view, name='user_edit'),
]
