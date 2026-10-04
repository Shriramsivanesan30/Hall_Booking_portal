import json
import logging
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from apps.accounts.models import UserProfile
from apps.departments.models import Department
from apps.audit.models import log_audit
from apps.accounts.services import (
    MicrosoftAuthService,
    MicrosoftAuthError,
    MicrosoftConfigError,
    MicrosoftGraphService,
    MicrosoftGraphError,
    MicrosoftUserSyncService,
    SyncResult,
)

logger = logging.getLogger(__name__)

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
    Initiates Microsoft Entra ID OAuth 2.0 authorization flow using MSAL.
    Saves flow state in user session and redirects to Microsoft authorization endpoint.
    """
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    # Preserve safe 'next' URL if provided
    next_url = request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        request.session['auth_next'] = next_url

    try:
        auth_service = MicrosoftAuthService()
        auth_flow = auth_service.initiate_auth_flow()
        request.session['auth_flow'] = auth_flow
        return redirect(auth_flow['auth_uri'])
    except MicrosoftConfigError as e:
        logger.error("Microsoft authentication configuration error: %s", str(e))
        messages.error(request, "Microsoft login is not properly configured. Please contact the system administrator.")
        return redirect('accounts:login')
    except Exception as e:
        logger.error("Failed to initiate Microsoft login flow: %s", str(e))
        messages.error(request, "Unable to connect to Microsoft login service. Please try again.")
        return redirect('accounts:login')

def microsoft_callback(request):
    """
    OAuth 2.0 callback handler for Microsoft Entra ID.
    Validates state, token, tenant, retrieves Graph profile, synchronizes user via
    Step 4 service, and establishes the Django session.
    """
    # 1. Handle error response from Microsoft (e.g. user cancellation)
    error = request.GET.get('error')
    error_description = request.GET.get('error_description')
    if error:
        logger.warning("Microsoft OAuth error in callback: error=%s, desc=%s", error, error_description)
        if error == 'access_denied':
            messages.info(request, "Microsoft sign-in was cancelled.")
        else:
            messages.error(request, "Microsoft authentication could not be completed. Please try again.")
        return redirect('accounts:login')

    # 2. Retrieve and validate stored auth_flow from session
    auth_flow = request.session.pop('auth_flow', None)
    if not auth_flow:
        logger.warning("Microsoft callback invoked without 'auth_flow' in session.")
        messages.error(request, "Authentication session expired or invalid state. Please try again.")
        return redirect('accounts:login')

    # 3. Exchange code for tokens using MSAL (validates state & PKCE)
    try:
        auth_service = MicrosoftAuthService()
        token_res = auth_service.acquire_token_by_auth_flow(auth_flow, request.GET.dict())
    except Exception as e:
        logger.error("Unexpected error acquiring token from Microsoft: %s", str(e))
        messages.error(request, "Microsoft authentication could not be completed. Please try again.")
        return redirect('accounts:login')

    if not token_res.get('success'):
        logger.warning("Microsoft token acquisition failed: %s", token_res.get('error'))
        messages.error(request, "Failed to authenticate with Microsoft credentials. Please try again.")
        return redirect('accounts:login')

    # 4. Validate tenant (single-tenant college restriction)
    id_token_claims = token_res.get('id_token_claims', {})
    if not auth_service.validate_tenant(id_token_claims):
        logger.warning("Tenant mismatch during Microsoft callback: tid=%s", id_token_claims.get('tid'))
        messages.error(
            request,
            "Access denied: You must sign in using an official institutional account from the college Microsoft tenant."
        )
        return redirect('accounts:login')

    # 5. Retrieve verified profile from Microsoft Graph
    access_token = token_res.get('access_token')
    try:
        graph_service = MicrosoftGraphService()
        profile_data = graph_service.get_user_profile(access_token)
    except MicrosoftGraphError as e:
        logger.error("Microsoft Graph profile retrieval failed in callback: %s", str(e))
        messages.error(request, "Could not retrieve your Microsoft profile details. Please try again.")
        return redirect('accounts:login')

    # 6. Synchronize with existing Django user (Step 4 service)
    sync_service = MicrosoftUserSyncService()
    sync_res = sync_service.sync_user(profile_data)

    # 7. Evaluate synchronization outcome
    if sync_res.is_success and sync_res.user:
        user = sync_res.user

        # Establish normal Django authenticated session
        login(request, user)

        # Safe audit log entry
        log_audit(
            request=request,
            action='LOGIN_SUCCESS',
            booking_id='',
            model_name='User',
            object_id=user.id,
            updated_value=f"Microsoft Entra ID Login ({sync_res.status})"
        )

        messages.success(request, f"Welcome, {user.get_full_name() or user.username}!")

        # Safe next redirect
        next_url = request.session.pop('auth_next', None)
        if next_url and isinstance(next_url, str) and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect('core:dashboard')

    elif sync_res.status == 'user_not_found':
        logger.warning("Microsoft login rejected: user not found in institution database (email=%s)", profile_data.get('email'))
        messages.error(
            request,
            "No institutional account was found for your Microsoft identity. Please contact the administrator."
        )
        return redirect('accounts:login')

    elif sync_res.status == 'identity_conflict':
        logger.warning(
            "Microsoft login rejected: identity conflict for email=%s, ms_uid=%s",
            profile_data.get('email'), profile_data.get('microsoft_user_id')
        )
        messages.error(
            request,
            "A Microsoft identity conflict was detected. Please contact the administrator."
        )
        return redirect('accounts:login')

    else:  # invalid_profile or unexpected status
        logger.error("User synchronization failed with status=%s: %s", sync_res.status, sync_res.message)
        messages.error(request, "Microsoft authentication could not be completed. Please try again.")
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
