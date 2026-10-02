from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from apps.audit.models import AuditLog

def is_admin(user):
    return user.is_authenticated and (user.is_superuser or (hasattr(user, 'profile') and user.profile.is_admin_user))

@login_required
@user_passes_test(is_admin)
def audit_logs_view(request):
    action_filter = request.GET.get('action')
    search = request.GET.get('search', '').strip()

    logs_qs = AuditLog.objects.select_related('user').order_by('-timestamp')

    if action_filter:
        logs_qs = logs_qs.filter(action=action_filter)
    if search:
        logs_qs = logs_qs.filter(
            Q(booking_id__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(updated_value__icontains=search) |
            Q(ip_address__icontains=search)
        )

    paginator = Paginator(logs_qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'audit/audit_logs.html', {
        'page_obj': page_obj,
        'action_choices': AuditLog.ACTION_CHOICES,
        'action_filter': action_filter,
        'search': search,
    })
