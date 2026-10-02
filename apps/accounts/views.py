import json
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from apps.accounts.models import UserProfile
from apps.departments.models import Department
from apps.audit.models import log_audit

def is_admin(user):
    return user.is_authenticated and (user.is_superuser or (hasattr(user, 'profile') and user.profile.is_admin_user))

def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    context = {
        'enable_demo_login': settings.ENABLE_DEMO_LOGIN,
        'client_id': settings.MICROSOFT_CLIENT_ID,
    }
    return render(request, 'authentication/login.html', context)

def demo_login_view(request):
    """
    Clearly marked local demo-login mode with sample institutional accounts.
    Disabled in production.
    """
    if not settings.ENABLE_DEMO_LOGIN:
        messages.error(request, "Demo login is strictly disabled in production.")
        return redirect('accounts:login')

    role = request.GET.get('role', 'FACULTY').upper()
    role_map = {
        'ADMIN': 'admin@mcet.in',
        'PRINCIPAL': 'principal@mcet.in',
        'COORDINATOR': 'coordinator@mcet.in',
        'HOD': 'hod.it@mcet.in',
        'FACULTY': 'faculty.it@mcet.in',
        'STUDENT': '727624P80@mcet.in',
    }

    username = role_map.get(role, 'faculty.it@mcet.in')
    user = User.objects.filter(username=username).first()
    if not user:
        # Fallback to any user with that role
        profile = UserProfile.objects.filter(role=role).first()
        if profile:
            user = profile.user

    if user:
        login(request, user)
        log_audit(request, 'USER_ROLE_CHANGE', booking_id='', model_name='User', object_id=user.id, updated_value=f"Demo Login as {role}")
        messages.success(request, f"Logged in successfully as {user.get_full_name()} ({role})")
        return redirect('core:dashboard')

    messages.error(request, f"Demo account for {role} not found. Please run seed data command.")
    return redirect('accounts:login')

def microsoft_login_redirect(request):
    """
    Redirects user to Microsoft's official Entra ID OAuth 2.0 authorization endpoint.
    """
    client_id = settings.MICROSOFT_CLIENT_ID
    tenant_id = settings.MICROSOFT_TENANT_ID or 'common'
    redirect_uri = settings.MICROSOFT_REDIRECT_URI
    scope = 'openid profile email User.Read'

    auth_url = (
        f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize?"
        f"client_id={client_id}&response_type=code&redirect_uri={redirect_uri}"
        f"&response_mode=query&scope={scope}&state=mcet_auth_state"
    )
    return redirect(auth_url)

def microsoft_callback(request):
    """
    OAuth 2.0 Callback handler for Microsoft Entra ID.
    Validates token, checks institutional domain, maps role and signs in.
    """
    code = request.GET.get('code')
    if not code:
        messages.error(request, "Authorization code missing from Microsoft authentication response.")
        return redirect('accounts:login')

    tenant_id = settings.MICROSOFT_TENANT_ID or 'common'
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

    token_data = {
        'client_id': settings.MICROSOFT_CLIENT_ID,
        'client_secret': settings.MICROSOFT_CLIENT_SECRET,
        'code': code,
        'redirect_uri': settings.MICROSOFT_REDIRECT_URI,
        'grant_type': 'authorization_code'
    }

    try:
        token_resp = requests.post(token_url, data=token_data, timeout=10)
        token_json = token_resp.json()
        access_token = token_json.get('access_token')

        if not access_token:
            messages.error(request, "Failed to retrieve access token from Microsoft Entra ID.")
            return redirect('accounts:login')

        # Retrieve user profile from Microsoft Graph
        headers = {'Authorization': f'Bearer {access_token}'}
        graph_resp = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers, timeout=10)
        graph_data = graph_resp.json()

        email = (graph_data.get('mail') or graph_data.get('userPrincipalName') or '').lower().strip()
        first_name = graph_data.get('givenName') or ''
        last_name = graph_data.get('surname') or ''

        if not email:
            messages.error(request, "Could not retrieve verified institutional email from Microsoft account.")
            return redirect('accounts:login')

        # Domain Validation
        email_domain = email.split('@')[-1]
        allowed_domains = settings.ALLOWED_EMAIL_DOMAINS
        if email_domain not in allowed_domains:
            messages.error(request, f"Unauthorized domain '@{email_domain}'. Only official institutional accounts ({', '.join(allowed_domains)}) are permitted.")
            return redirect('accounts:login')

        # Find or create user
        user, created = User.objects.get_or_create(
            username=email,
            defaults={
                'email': email,
                'first_name': first_name,
                'last_name': last_name
            }
        )

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.auth_provider = 'microsoft'

        # Auto-detect student role based on roll number format (e.g., 727624P80@mcet.in)
        if any(char.isdigit() for char in email.split('@')[0]) and not user.is_staff and created:
            profile.role = UserProfile.ROLE_STUDENT
            profile.employee_roll_no = email.split('@')[0].upper()
            profile.save()

        login(request, user)
        log_audit(request, 'USER_ROLE_CHANGE', booking_id='', model_name='User', object_id=user.id, updated_value="Microsoft OAuth Login")
        messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
        return redirect('core:dashboard')

    except Exception as e:
        messages.error(request, f"Error communicating with Microsoft Authentication Service: {str(e)}")
        return redirect('accounts:login')

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out securely.")
    return redirect('accounts:login')

@login_required
def profile_view(request):
    profile = request.user.profile
    if request.method == 'POST':
        request.user.first_name = request.POST.get('first_name', '').strip()
        request.user.last_name = request.POST.get('last_name', '').strip()
        request.user.save()

        profile.phone = request.POST.get('phone', '').strip()
        profile.designation = request.POST.get('designation', '').strip()
        profile.employee_roll_no = request.POST.get('employee_roll_no', '').strip()
        profile.save()

        messages.success(request, "Profile updated successfully.")
        return redirect('accounts:profile')

    return render(request, 'accounts/profile.html', {'profile': profile})

@login_required
@user_passes_test(is_admin)
def user_management_view(request):
    users = User.objects.select_related('profile', 'profile__department').order_by('username')
    departments = Department.objects.filter(is_active=True)
    roles = UserProfile.ROLE_CHOICES
    return render(request, 'accounts/users_list.html', {
        'users': users,
        'departments': departments,
        'roles': roles,
    })

@login_required
@user_passes_test(is_admin)
def user_edit_view(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    profile = target_user.profile
    departments = Department.objects.filter(is_active=True)

    if request.method == 'POST':
        prev_role = profile.role
        new_role = request.POST.get('role')
        dept_id = request.POST.get('department')

        profile.role = new_role
        if dept_id:
            profile.department = Department.objects.filter(id=dept_id).first()
        else:
            profile.department = None
        profile.designation = request.POST.get('designation', '').strip()
        profile.employee_roll_no = request.POST.get('employee_roll_no', '').strip()
        profile.is_approved = 'is_approved' in request.POST
        profile.save()

        log_audit(
            request=request,
            action='USER_ROLE_CHANGE',
            model_name='UserProfile',
            object_id=profile.id,
            previous_value=f"Role: {prev_role}",
            updated_value=f"Role: {new_role}, Dept: {profile.department}"
        )

        messages.success(request, f"Updated user profile for {target_user.username}.")
        return redirect('accounts:user_management')

    return render(request, 'accounts/user_form.html', {
        'target_user': target_user,
        'profile': profile,
        'departments': departments,
        'roles': UserProfile.ROLE_CHOICES,
    })
