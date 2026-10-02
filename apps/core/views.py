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
    today = timezone.localdate()
    now = timezone.localtime().time()

    # 1. Total Seminar Halls
    total_halls = Hall.objects.filter(is_active=True).count()

    # 2. Today's Bookings
    todays_bookings = Booking.objects.filter(
        event_date=today,
        status__in=[Booking.STATUS_APPROVED, Booking.STATUS_SUBMITTED, Booking.STATUS_HOD_APPROVED, Booking.STATUS_COORDINATOR_APPROVED]
    ).select_related('preferred_hall', 'allocated_hall', 'department', 'user').order_by('start_time')

    today_confirmed_bookings = todays_bookings.filter(status=Booking.STATUS_APPROVED)
    todays_bookings_count = today_confirmed_bookings.count()

    # 3. Available Halls Today (Halls that are active, not in maintenance, and not currently occupied or have open slots)
    booked_hall_ids_today = today_confirmed_bookings.values_list('allocated_hall_id', flat=True)
    available_halls_today = Hall.objects.filter(
        is_active=True,
        is_under_maintenance=False
    ).exclude(id__in=booked_hall_ids_today).count()

    # 4. Global Counts from database
    pending_requests_count = Booking.objects.filter(
        status__in=[Booking.STATUS_SUBMITTED, Booking.STATUS_HOD_APPROVED, Booking.STATUS_COORDINATOR_APPROVED]
    ).count()

    approved_bookings_count = Booking.objects.filter(status=Booking.STATUS_APPROVED).count()
    rejected_requests_count = Booking.objects.filter(status=Booking.STATUS_REJECTED).count()
    cancelled_bookings_count = Booking.objects.filter(status=Booking.STATUS_CANCELLED).count()

    # 5. Upcoming Events (Next 7 days, approved)
    upcoming_events = Booking.objects.filter(
        event_date__gte=today,
        status=Booking.STATUS_APPROVED
    ).select_related('preferred_hall', 'allocated_hall', 'department', 'user').order_by('event_date', 'start_time')[:8]

    # 6. User-specific counts if faculty/student
    user = request.user
    my_bookings_count = Booking.objects.filter(user=user).count()

    # 7. Hall utilization status for quick glance
    all_halls = Hall.objects.filter(is_active=True).order_by('name')
    hall_status_list = []
    for h in all_halls:
        current_event = today_confirmed_bookings.filter(
            allocated_hall=h,
            start_time__lte=now,
            end_time__gte=now
        ).first()

        upcoming_today = today_confirmed_bookings.filter(
            allocated_hall=h,
            start_time__gt=now
        ).first()

        hall_status_list.append({
            'hall': h,
            'current_event': current_event,
            'upcoming_today': upcoming_today,
            'is_busy': current_event is not None,
            'is_maintenance': h.is_under_maintenance
        })

    context = {
        'total_halls': total_halls,
        'available_halls_today': available_halls_today,
        'todays_bookings_count': todays_bookings_count,
        'pending_requests_count': pending_requests_count,
        'approved_bookings_count': approved_bookings_count,
        'rejected_requests_count': rejected_requests_count,
        'cancelled_bookings_count': cancelled_bookings_count,
        'todays_schedule': todays_bookings,
        'upcoming_events': upcoming_events,
        'my_bookings_count': my_bookings_count,
        'hall_status_list': hall_status_list,
        'today_date': today,
    }

    return render(request, 'dashboard/dashboard.html', context)

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
