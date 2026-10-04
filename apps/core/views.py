from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from apps.halls.models import Hall
from apps.bookings.models import Booking
from apps.departments.models import Department
from apps.core.models import SystemConfiguration
from apps.audit.models import log_audit

def is_admin(user):
    return user.is_authenticated and (user.is_superuser or (hasattr(user, 'profile') and user.profile.is_admin_user))

@login_required
def dashboard_view(request):
    import datetime as _dt
    today = timezone.localdate()
    now   = timezone.localtime().time()
    user  = request.user
    profile = getattr(user, 'profile', None)

    # ── Common base data ──────────────────────────────────────────
    total_halls   = Hall.objects.filter(is_active=True).count()
    all_halls     = Hall.objects.filter(is_active=True).prefetch_related('facilities').order_by('name')

    todays_all_bookings = Booking.objects.filter(
        event_date=today,
        status__in=[Booking.STATUS_APPROVED, Booking.STATUS_SUBMITTED,
                    Booking.STATUS_HOD_APPROVED, Booking.STATUS_COORDINATOR_APPROVED]
    ).select_related('preferred_hall', 'allocated_hall', 'department', 'user').order_by('start_time')
    today_confirmed = todays_all_bookings.filter(status=Booking.STATUS_APPROVED)

    booked_ids_today = today_confirmed.values_list('allocated_hall_id', flat=True)
    available_halls_today = Hall.objects.filter(
        is_active=True, is_under_maintenance=False
    ).exclude(id__in=booked_ids_today).count()

    first_of_month = today.replace(day=1)

    # Hall status mini list (shared)
    hall_status_list = []
    for h in all_halls:
        cur  = today_confirmed.filter(allocated_hall=h, start_time__lte=now, end_time__gte=now).first()
        next_ = today_confirmed.filter(allocated_hall=h, start_time__gt=now).first()
        hall_status_list.append({
            'hall': h, 'current_event': cur, 'upcoming_today': next_,
            'is_busy': cur is not None, 'is_maintenance': h.is_under_maintenance,
        })

    # Today's schedule panel (shared right-panel)
    schedule_windows = [
        {'label': '09:00 AM\n– 11:00 AM', 'start_h': 9,  'end_h': 11},
        {'label': '02:00 PM\n– 04:00 PM', 'start_h': 14, 'end_h': 16},
        {'label': '04:00 PM\n– 06:00 PM', 'start_h': 16, 'end_h': 18},
    ]
    todays_schedule_panel = []
    for tw in schedule_windows:
        match = today_confirmed.filter(
            start_time__hour__gte=tw['start_h'] - 1,
            start_time__hour__lt=tw['end_h']
        ).first()
        todays_schedule_panel.append({'time_label': tw['label'], 'booking': match})

    # ── ROLE: FACULTY ─────────────────────────────────────────────
    if not profile or profile.role in ['FACULTY', 'STUDENT']:
        my_all = Booking.objects.filter(user=user).select_related(
            'preferred_hall', 'allocated_hall', 'department'
        ).order_by('event_date', 'start_time')
        my_upcoming  = list(my_all.filter(
            event_date__gte=today,
            status__in=[Booking.STATUS_APPROVED, Booking.STATUS_SUBMITTED,
                        Booking.STATUS_HOD_APPROVED, Booking.STATUS_COORDINATOR_APPROVED]
        ))
        my_pending   = list(my_all.filter(
            status__in=[Booking.STATUS_SUBMITTED, Booking.STATUS_HOD_APPROVED,
                        Booking.STATUS_COORDINATOR_APPROVED]
        ))
        my_approved  = list(my_all.filter(status=Booking.STATUS_APPROVED))
        my_cancelled = list(my_all.filter(
            status__in=[Booking.STATUS_CANCELLED, Booking.STATUS_REJECTED]
        ))
        approved_this_month = Booking.objects.filter(
            user=user, status=Booking.STATUS_APPROVED, event_date__gte=first_of_month
        ).count()

        context = {
            'today_date': today, 'available_halls_today': available_halls_today,
            'my_upcoming': my_upcoming, 'my_pending': my_pending,
            'my_approved': my_approved, 'my_cancelled': my_cancelled,
            'approved_this_month': approved_this_month,
            'tab_data': [
                ('upcoming', my_upcoming), ('pending', my_pending),
                ('approved', my_approved), ('cancelled', my_cancelled),
            ],
            'todays_schedule_panel': todays_schedule_panel,
            'hall_avail_mini': hall_status_list[:4],
        }
        return render(request, 'dashboard/faculty_dashboard.html', context)

    # ── ROLE: HOD ─────────────────────────────────────────────────
    if profile.is_hod:
        dept = profile.department
        # Pending approvals for this dept
        pending_qs = Booking.objects.filter(
            department=dept,
            status=Booking.STATUS_SUBMITTED,
            current_approval_stage=Booking.STAGE_HOD
        ).select_related('user', 'preferred_hall', 'allocated_hall', 'department').order_by('created_at')

        dept_bookings = Booking.objects.filter(
            department=dept,
            status__in=[Booking.STATUS_APPROVED, Booking.STATUS_HOD_APPROVED,
                        Booking.STATUS_COORDINATOR_APPROVED]
        ).select_related('preferred_hall', 'allocated_hall').order_by('-event_date')[:10]

        dept_events_count = Booking.objects.filter(
            department=dept, event_date__gte=first_of_month
        ).count()
        approved_count = Booking.objects.filter(
            department=dept, status=Booking.STATUS_APPROVED, event_date__gte=first_of_month
        ).count()
        rejected_count = Booking.objects.filter(
            department=dept, status=Booking.STATUS_REJECTED, event_date__gte=first_of_month
        ).count()

        # Filter pending by event type for tabs
        pending_list = list(pending_qs)
        event_types_pending = {}
        for b in pending_list:
            et = b.event_type
            event_types_pending.setdefault(et, []).append(b)

        context = {
            'today_date': today,
            'pending_approvals': pending_list,
            'event_types_pending': event_types_pending,
            'dept_bookings': dept_bookings,
            'dept_events_count': dept_events_count,
            'approved_count': approved_count,
            'rejected_count': rejected_count,
            'todays_schedule_panel': todays_schedule_panel,
            'hall_avail_mini': hall_status_list[:4],
            'dept': dept,
        }
        return render(request, 'dashboard/hod_dashboard.html', context)

    # ── ROLE: COORDINATOR ─────────────────────────────────────────
    if profile.is_coordinator:
        pending_coord = Booking.objects.filter(
            status=Booking.STATUS_HOD_APPROVED,
            current_approval_stage=Booking.STAGE_COORDINATOR
        ).select_related('user', 'preferred_hall', 'allocated_hall', 'department').order_by('created_at')

        all_approved = Booking.objects.filter(
            status=Booking.STATUS_APPROVED
        ).select_related('preferred_hall', 'allocated_hall', 'department').order_by('-event_date')[:8]

        pending_count    = pending_coord.count()
        approved_month   = Booking.objects.filter(status=Booking.STATUS_APPROVED, event_date__gte=first_of_month).count()
        rejected_month   = Booking.objects.filter(status=Booking.STATUS_REJECTED, event_date__gte=first_of_month).count()
        halls_available  = available_halls_today

        context = {
            'today_date': today,
            'pending_coord': list(pending_coord),
            'all_approved': all_approved,
            'pending_count': pending_count,
            'approved_month': approved_month,
            'rejected_month': rejected_month,
            'halls_available': halls_available,
            'total_halls': total_halls,
            'hall_status_list': hall_status_list,
            'todays_schedule_panel': todays_schedule_panel,
            'hall_avail_mini': hall_status_list[:4],
        }
        return render(request, 'dashboard/coordinator_dashboard.html', context)

    # ── ROLE: PRINCIPAL ───────────────────────────────────────────
    if profile.is_principal:
        pending_principal = Booking.objects.filter(
            status=Booking.STATUS_COORDINATOR_APPROVED,
            current_approval_stage=Booking.STAGE_PRINCIPAL
        ).select_related('user', 'preferred_hall', 'allocated_hall', 'department').order_by('created_at')

        upcoming_approved = Booking.objects.filter(
            event_date__gte=today, status=Booking.STATUS_APPROVED
        ).select_related('preferred_hall', 'allocated_hall', 'department').order_by('event_date')[:8]

        context = {
            'today_date': today,
            'pending_principal': list(pending_principal),
            'upcoming_approved': upcoming_approved,
            'pending_count': pending_principal.count(),
            'approved_month': Booking.objects.filter(status=Booking.STATUS_APPROVED, event_date__gte=first_of_month).count(),
            'todays_schedule_panel': todays_schedule_panel,
            'hall_avail_mini': hall_status_list[:4],
        }
        return render(request, 'dashboard/principal_dashboard.html', context)

    # ── ROLE: ADMIN ───────────────────────────────────────────────
    pending_all = Booking.objects.filter(
        status__in=[Booking.STATUS_SUBMITTED, Booking.STATUS_HOD_APPROVED,
                    Booking.STATUS_COORDINATOR_APPROVED]
    ).count()
    approved_month = Booking.objects.filter(status=Booking.STATUS_APPROVED, event_date__gte=first_of_month).count()
    rejected_month = Booking.objects.filter(status=Booking.STATUS_REJECTED, event_date__gte=first_of_month).count()
    total_bookings = Booking.objects.count()
    recent_bookings = Booking.objects.select_related(
        'user', 'preferred_hall', 'allocated_hall', 'department'
    ).order_by('-created_at')[:10]

    context = {
        'today_date': today,
        'total_halls': total_halls,
        'available_halls_today': available_halls_today,
        'pending_all': pending_all,
        'approved_month': approved_month,
        'rejected_month': rejected_month,
        'total_bookings': total_bookings,
        'recent_bookings': recent_bookings,
        'todays_schedule': todays_all_bookings,
        'hall_status_list': hall_status_list,
        'todays_schedule_panel': todays_schedule_panel,
        'hall_avail_mini': hall_status_list[:4],
    }
    return render(request, 'dashboard/admin_dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def settings_view(request):
    configs = SystemConfiguration.objects.all().order_by('key')
    pending_blocks = SystemConfiguration.get_bool('PENDING_BLOCKS_AVAILABILITY', default=False)
    allow_weekend = SystemConfiguration.get_bool('ALLOW_WEEKEND_BOOKINGS', default=True)
    max_advance_days = SystemConfiguration.get_str('MAX_ADVANCE_BOOKING_DAYS', default='90')

    return render(request, 'settings/settings.html', {
        'configs': configs,
        'pending_blocks': pending_blocks,
        'allow_weekend': allow_weekend,
        'max_advance_days': max_advance_days,
    })

@login_required
@user_passes_test(is_admin)
def update_settings_view(request):
    if request.method == 'POST':
        pending_blocks = 'pending_blocks' in request.POST
        allow_weekend = 'allow_weekend' in request.POST
        max_advance_days = request.POST.get('max_advance_days', '90').strip()

        SystemConfiguration.set_value(
            'PENDING_BLOCKS_AVAILABILITY',
            'True' if pending_blocks else 'False',
            description="Whether pending requests reserve/block hall availability",
            data_type='boolean'
        )

        SystemConfiguration.set_value(
            'ALLOW_WEEKEND_BOOKINGS',
            'True' if allow_weekend else 'False',
            description="Allow booking seminar halls on Saturdays and Sundays",
            data_type='boolean'
        )

        SystemConfiguration.set_value(
            'MAX_ADVANCE_BOOKING_DAYS',
            max_advance_days,
            description="Maximum days in advance a seminar hall can be booked",
            data_type='integer'
        )

        log_audit(
            request=request,
            action='SETTINGS_UPDATE',
            updated_value=f"Pending Blocks: {pending_blocks}, Advance Days: {max_advance_days}"
        )

        messages.success(request, "System settings updated successfully.")
        return redirect('core:settings')

    return redirect('core:settings')
