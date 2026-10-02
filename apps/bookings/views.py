import json
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from apps.halls.models import Hall
from apps.departments.models import Department
from apps.bookings.models import Booking, BookingAttachment
from apps.approvals.models import ApprovalHistory
from apps.bookings.services import check_hall_availability
from apps.notifications.services import send_booking_notification
from apps.audit.models import log_audit

@login_required
def new_booking_view(request):
    user = request.user
    profile = getattr(user, 'profile', None)

    if profile and profile.is_student:
        messages.error(request, "Students can view hall availability and events, but cannot create booking requests directly.")
        return redirect('bookings:calendar')

    halls = Hall.objects.filter(is_active=True).order_by('name')
    departments = Department.objects.filter(is_active=True).order_by('name')

    if request.method == 'POST':
        action_type = request.POST.get('action_type', 'SUBMIT') # 'DRAFT' or 'SUBMIT'
        dept_id = request.POST.get('department')
        event_name = request.POST.get('event_name', '').strip()
        event_type = request.POST.get('event_type', 'Seminar')
        participants = int(request.POST.get('expected_participants', 50))
        event_date_str = request.POST.get('event_date')
        start_time_str = request.POST.get('start_time')
        end_time_str = request.POST.get('end_time')
        preferred_hall_id = request.POST.get('preferred_hall')
        alt_hall_id = request.POST.get('alternative_hall') or None

        department = get_object_or_404(Department, id=dept_id)
        preferred_hall = get_object_or_404(Hall, id=preferred_hall_id)
        alt_hall = Hall.objects.filter(id=alt_hall_id).first() if alt_hall_id else None

        # Check availability
        availability = check_hall_availability(
            hall_id=preferred_hall.id,
            event_date=event_date_str,
            start_time=start_time_str,
            end_time=end_time_str,
            participants=participants
        )

        if action_type == 'SUBMIT' and not availability['is_available']:
            for err in availability['errors']:
                messages.error(request, err)
            return render(request, 'bookings/new_booking.html', {
                'halls': halls,
                'departments': departments,
                'event_types': Booking.EVENT_TYPES,
                'availability_result': availability,
                'form_data': request.POST,
            })

        # Determine initial stage
        if action_type == 'DRAFT':
            initial_status = Booking.STATUS_DRAFT
            initial_stage = Booking.STAGE_DRAFT
        else:
            if profile and profile.is_hod:
                # HOD created it -> moves to Coordinator review
                initial_status = Booking.STATUS_HOD_APPROVED
                initial_stage = Booking.STAGE_COORDINATOR
            elif profile and profile.is_admin_user:
                initial_status = Booking.STATUS_APPROVED
                initial_stage = Booking.STAGE_COMPLETED
            else:
                initial_status = Booking.STATUS_SUBMITTED
                initial_stage = Booking.STAGE_HOD

        booking = Booking(
            user=user,
            department=department,
            event_name=event_name,
            event_type=event_type,
            expected_participants=participants,
            event_date=datetime.datetime.strptime(event_date_str, '%Y-%m-%d').date(),
            start_time=datetime.datetime.strptime(start_time_str, '%H:%M').time(),
            end_time=datetime.datetime.strptime(end_time_str, '%H:%M').time(),
            preferred_hall=preferred_hall,
            alternative_hall=alt_hall,
            allocated_hall=preferred_hall,
            req_projector='req_projector' in request.POST,
            req_audio='req_audio' in request.POST,
            req_microphone='req_microphone' in request.POST,
            req_wifi='req_wifi' in request.POST,
            req_video_conferencing='req_video_conferencing' in request.POST,
            req_ac='req_ac' in request.POST,
            req_stage='req_stage' in request.POST,
            req_recording='req_recording' in request.POST,
            chief_guest=request.POST.get('chief_guest', '').strip(),
            event_description=request.POST.get('event_description', '').strip(),
            special_requirements=request.POST.get('special_requirements', '').strip(),
            status=initial_status,
            current_approval_stage=initial_stage
        )
        booking.save()

        # Handle file attachments
        if 'schedule_file' in request.FILES:
            BookingAttachment.objects.create(
                booking=booking,
                file=request.FILES['schedule_file'],
                title="Programme Schedule",
                file_type=BookingAttachment.TYPE_SCHEDULE
            )
        if 'approval_doc_file' in request.FILES:
            BookingAttachment.objects.create(
                booking=booking,
                file=request.FILES['approval_doc_file'],
                title="Department / Administrative Approval Document",
                file_type=BookingAttachment.TYPE_APPROVAL_DOC
            )

        # Record Initial Approval History
        ApprovalHistory.objects.create(
            booking=booking,
            stage="Draft Saved" if action_type == 'DRAFT' else "Booking Submitted",
            action=ApprovalHistory.ACTION_SUBMITTED,
            user=user,
            previous_status="",
            new_status=booking.status,
            remarks=f"Initial booking request created. Action: {action_type}"
        )

        # Audit Log
        log_audit(
            request=request,
            action='BOOKING_CREATE',
            booking_id=booking.booking_id,
            model_name='Booking',
            object_id=booking.id,
            updated_value=f"Created booking {booking.booking_id} for {booking.event_name}"
        )

        # Notifications
        if action_type == 'SUBMIT':
            send_booking_notification(
                booking=booking,
                notification_type='SUBMITTED',
                title=f"Booking Request Submitted – {booking.booking_id}",
                recipient=user
            )
            messages.success(request, f"Booking request {booking.booking_id} submitted successfully! It is now pending approval.")
        else:
            messages.info(request, f"Booking request {booking.booking_id} saved as draft.")

        return redirect('bookings:detail', booking_id=booking.booking_id)

    return render(request, 'bookings/new_booking.html', {
        'halls': halls,
        'departments': departments,
        'event_types': Booking.EVENT_TYPES,
        'user_department': profile.department if profile else None,
    })

@login_required
def api_check_availability(request):
    """
    AJAX endpoint for the live 'Check Availability' button on booking form.
    """
    hall_id = request.GET.get('hall_id')
    event_date = request.GET.get('event_date')
    start_time = request.GET.get('start_time')
    end_time = request.GET.get('end_time')
    participants = int(request.GET.get('participants', 0))
    exclude_id = request.GET.get('exclude_id')

    if not all([hall_id, event_date, start_time, end_time]):
        return JsonResponse({'is_available': False, 'errors': ['Please fill in Hall, Date, Start Time, and End Time.']})

    result = check_hall_availability(
        hall_id=hall_id,
        event_date=event_date,
        start_time=start_time,
        end_time=end_time,
        exclude_booking_id=exclude_id,
        participants=participants
    )

    conflicts_data = []
    for c in result['conflicts']:
        conflicts_data.append({
            'booking_id': c.booking_id,
            'event_name': c.event_name,
            'department': c.department.code,
            'start_time': c.start_time.strftime('%I:%M %p'),
            'end_time': c.end_time.strftime('%I:%M %p'),
            'status': c.get_status_display(),
        })

    alt_halls_data = []
    for h in result['alternative_halls']:
        alt_halls_data.append({
            'id': h.id,
            'name': h.name,
            'capacity': h.capacity,
            'building': h.building,
            'floor': h.floor,
        })

    return JsonResponse({
        'is_available': result['is_available'],
        'errors': result['errors'],
        'conflicts': conflicts_data,
        'alternative_halls': alt_halls_data,
        'suggested_slots': result['suggested_slots'],
    })

@login_required
def booking_detail_view(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related('user', 'department', 'preferred_hall', 'allocated_hall', 'rejected_by', 'cancelled_by'),
        booking_id=booking_id
    )

    history = booking.approval_history.select_related('user').order_by('created_at')
    attachments = booking.attachments.all()
    user = request.user
    profile = getattr(user, 'profile', None)

    # Permission checks
    can_edit = (booking.user == user and booking.is_editable) or (profile and profile.is_admin_user)
    can_cancel = (booking.user == user and booking.is_cancellable) or (profile and profile.is_admin_user)
    can_review = False

    if profile:
        if profile.is_admin_user:
            can_review = booking.status in [Booking.STATUS_SUBMITTED, Booking.STATUS_HOD_APPROVED, Booking.STATUS_COORDINATOR_APPROVED]
        elif profile.is_principal and booking.current_approval_stage == Booking.STAGE_PRINCIPAL:
            can_review = True
        elif profile.is_coordinator and booking.current_approval_stage == Booking.STAGE_COORDINATOR:
            can_review = True
        elif profile.is_hod and booking.current_approval_stage == Booking.STAGE_HOD and profile.department == booking.department:
            can_review = True

    return render(request, 'bookings/detail.html', {
        'booking': booking,
        'history': history,
        'attachments': attachments,
        'can_edit': can_edit,
        'can_cancel': can_cancel,
        'can_review': can_review,
        'halls': Hall.objects.filter(is_active=True) if can_review else [],
    })

@login_required
def edit_booking_view(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id)
    user = request.user
    profile = getattr(user, 'profile', None)

    if not (booking.user == user or (profile and profile.is_admin_user)):
        messages.error(request, "You do not have permission to edit this booking.")
        return redirect('bookings:detail', booking_id=booking.booking_id)

    if not booking.is_editable and not (profile and profile.is_admin_user):
        messages.error(request, "Approved, cancelled, or rejected bookings cannot be directly modified.")
        return redirect('bookings:detail', booking_id=booking.booking_id)

    halls = Hall.objects.filter(is_active=True).order_by('name')
    departments = Department.objects.filter(is_active=True).order_by('name')

    if request.method == 'POST':
        action_type = request.POST.get('action_type', 'SUBMIT')
        event_name = request.POST.get('event_name', '').strip()
        event_type = request.POST.get('event_type')
        participants = int(request.POST.get('expected_participants', 50))
        event_date_str = request.POST.get('event_date')
        start_time_str = request.POST.get('start_time')
        end_time_str = request.POST.get('end_time')
        preferred_hall_id = request.POST.get('preferred_hall')
        alt_hall_id = request.POST.get('alternative_hall') or None

        preferred_hall = get_object_or_404(Hall, id=preferred_hall_id)
        alt_hall = Hall.objects.filter(id=alt_hall_id).first() if alt_hall_id else None

        # Check availability
        availability = check_hall_availability(
            hall_id=preferred_hall.id,
            event_date=event_date_str,
            start_time=start_time_str,
            end_time=end_time_str,
            exclude_booking_id=booking.id,
            participants=participants
        )

        if action_type == 'SUBMIT' and not availability['is_available']:
            for err in availability['errors']:
                messages.error(request, err)
            return render(request, 'bookings/edit_booking.html', {
                'booking': booking,
                'halls': halls,
                'departments': departments,
                'event_types': Booking.EVENT_TYPES,
                'availability_result': availability,
            })

        booking.event_name = event_name
        booking.event_type = event_type
        booking.expected_participants = participants
        booking.event_date = datetime.datetime.strptime(event_date_str, '%Y-%m-%d').date()
        booking.start_time = datetime.datetime.strptime(start_time_str, '%H:%M').time()
        booking.end_time = datetime.datetime.strptime(end_time_str, '%H:%M').time()
        booking.preferred_hall = preferred_hall
        booking.alternative_hall = alt_hall
        booking.allocated_hall = preferred_hall
        booking.req_projector = 'req_projector' in request.POST
        booking.req_audio = 'req_audio' in request.POST
        booking.req_microphone = 'req_microphone' in request.POST
        booking.req_wifi = 'req_wifi' in request.POST
        booking.req_video_conferencing = 'req_video_conferencing' in request.POST
        booking.req_ac = 'req_ac' in request.POST
        booking.req_stage = 'req_stage' in request.POST
        booking.req_recording = 'req_recording' in request.POST
        booking.chief_guest = request.POST.get('chief_guest', '').strip()
        booking.event_description = request.POST.get('event_description', '').strip()
        booking.special_requirements = request.POST.get('special_requirements', '').strip()

        if action_type == 'SUBMIT':
            if booking.status == Booking.STATUS_DRAFT:
                booking.status = Booking.STATUS_SUBMITTED
                booking.current_approval_stage = Booking.STAGE_HOD

        booking.save()

        ApprovalHistory.objects.create(
            booking=booking,
            stage="Booking Modified",
            action=ApprovalHistory.ACTION_SUBMITTED,
            user=user,
            previous_status=booking.status,
            new_status=booking.status,
            remarks="User updated booking details."
        )

        log_audit(
            request=request,
            action='BOOKING_UPDATE',
            booking_id=booking.booking_id,
            model_name='Booking',
            object_id=booking.id,
            updated_value=f"Updated booking details for {booking.booking_id}"
        )

        messages.success(request, f"Booking {booking.booking_id} updated successfully.")
        return redirect('bookings:detail', booking_id=booking.booking_id)

    return render(request, 'bookings/edit_booking.html', {
        'booking': booking,
        'halls': halls,
        'departments': departments,
        'event_types': Booking.EVENT_TYPES,
    })

@login_required
def cancel_booking_view(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id)
    user = request.user
    profile = getattr(user, 'profile', None)

    if not (booking.user == user or (profile and profile.is_admin_user)):
        messages.error(request, "Permission denied.")
        return redirect('bookings:detail', booking_id=booking.booking_id)

    if request.method == 'POST':
        reason = request.POST.get('cancellation_reason', '').strip()
        if not reason:
            messages.error(request, "Cancellation requires a mandatory documented reason.")
            return redirect('bookings:detail', booking_id=booking.booking_id)

        prev_status = booking.status
        booking.status = Booking.STATUS_CANCELLED
        booking.current_approval_stage = Booking.STAGE_CANCELLED
        booking.cancellation_reason = reason
        booking.cancelled_by = user
        booking.cancelled_at = timezone.now()
        booking.save()

        ApprovalHistory.objects.create(
            booking=booking,
            stage="Cancelled",
            action=ApprovalHistory.ACTION_CANCELLED,
            user=user,
            previous_status=prev_status,
            new_status=Booking.STATUS_CANCELLED,
            remarks=reason
        )

        log_audit(
            request=request,
            action='BOOKING_CANCEL',
            booking_id=booking.booking_id,
            model_name='Booking',
            object_id=booking.id,
            previous_value=prev_status,
            updated_value=f"Cancelled: {reason}"
        )

        send_booking_notification(
            booking=booking,
            notification_type='CANCELLATION',
            title=f"Booking Cancelled – {booking.booking_id}",
            recipient=booking.user,
            remarks=reason
        )

        messages.success(request, f"Booking {booking.booking_id} has been cancelled.")
        return redirect('bookings:detail', booking_id=booking.booking_id)

    return redirect('bookings:detail', booking_id=booking.booking_id)

@login_required
def my_bookings_view(request):
    user = request.user
    status_filter = request.GET.get('status', '')
    search = request.GET.get('search', '').strip()

    bookings_qs = Booking.objects.filter(user=user).select_related('preferred_hall', 'allocated_hall', 'department')

    if status_filter:
        bookings_qs = bookings_qs.filter(status=status_filter)
    if search:
        bookings_qs = bookings_qs.filter(
            Q(booking_id__icontains=search) |
            Q(event_name__icontains=search) |
            Q(preferred_hall__name__icontains=search)
        )

    paginator = Paginator(bookings_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'bookings/my_bookings.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search': search,
        'status_choices': Booking.STATUS_CHOICES,
    })

@login_required
def approved_bookings_view(request):
    dept_id = request.GET.get('department')
    hall_id = request.GET.get('hall')
    date_filter = request.GET.get('date')
    search = request.GET.get('search', '').strip()

    bookings_qs = Booking.objects.filter(
        status=Booking.STATUS_APPROVED
    ).select_related('user', 'department', 'allocated_hall', 'preferred_hall').order_by('-event_date', '-start_time')

    if dept_id:
        bookings_qs = bookings_qs.filter(department_id=dept_id)
    if hall_id:
        bookings_qs = bookings_qs.filter(Q(allocated_hall_id=hall_id) | Q(preferred_hall_id=hall_id))
    if date_filter:
        bookings_qs = bookings_qs.filter(event_date=date_filter)
    if search:
        bookings_qs = bookings_qs.filter(
            Q(booking_id__icontains=search) |
            Q(event_name__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )

    paginator = Paginator(bookings_qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'bookings/approved_bookings.html', {
        'page_obj': page_obj,
        'departments': Department.objects.filter(is_active=True),
        'halls': Hall.objects.filter(is_active=True),
        'dept_id': dept_id,
        'hall_id': hall_id,
        'date_filter': date_filter,
        'search': search,
    })

@login_required
def calendar_view(request):
    """
    Microsoft Outlook inspired Calendar view with Day, Week, Month, and Agenda modes.
    """
    departments = Department.objects.filter(is_active=True).order_by('name')
    halls = Hall.objects.filter(is_active=True).order_by('name')

    return render(request, 'calendar/calendar.html', {
        'departments': departments,
        'halls': halls,
        'event_types': [t[0] for t in Booking.EVENT_TYPES],
    })

@login_required
def api_calendar_events(request):
    """
    Feeds calendar events in JSON format with status-based colors.
    """
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')
    dept_id = request.GET.get('department')
    hall_id = request.GET.get('hall')
    event_type = request.GET.get('event_type')
    search = request.GET.get('search', '').strip()

    bookings_qs = Booking.objects.select_related('preferred_hall', 'allocated_hall', 'department', 'user')

    # Status filter: show approved events, and show pending events (or user's own)
    user = request.user
    profile = getattr(user, 'profile', None)

    # By default, show approved events, plus pending requests for staff/admin, plus own requests
    if profile and (profile.is_coordinator or profile.is_admin_user or profile.is_principal):
        bookings_qs = bookings_qs.exclude(status__in=[Booking.STATUS_DRAFT])
    else:
        bookings_qs = bookings_qs.filter(
            Q(status=Booking.STATUS_APPROVED) |
            Q(user=user)
        )

    if start_str and end_str:
        try:
            start_date = datetime.datetime.fromisoformat(start_str[:10]).date()
            end_date = datetime.datetime.fromisoformat(end_str[:10]).date()
            bookings_qs = bookings_qs.filter(event_date__gte=start_date, event_date__lte=end_date)
        except Exception:
            pass

    if dept_id:
        bookings_qs = bookings_qs.filter(department_id=dept_id)
    if hall_id:
        bookings_qs = bookings_qs.filter(Q(allocated_hall_id=hall_id) | Q(preferred_hall_id=hall_id))
    if event_type:
        bookings_qs = bookings_qs.filter(event_type=event_type)
    if search:
        bookings_qs = bookings_qs.filter(
            Q(event_name__icontains=search) |
            Q(booking_id__icontains=search) |
            Q(department__code__icontains=search)
        )

    events = []
    for b in bookings_qs:
        hall = b.get_active_hall()
        start_dt = datetime.datetime.combine(b.event_date, b.start_time)
        end_dt = datetime.datetime.combine(b.event_date, b.end_time)

        # Status Colors
        # Blue: Approved/Booked (#1D5FA7)
        # Orange: Pending (#F59E0B)
        # Red: Rejected/Conflict (#DC2626)
        # Grey: Cancelled (#94A3B8)
        if b.status == Booking.STATUS_APPROVED:
            color = '#1D5FA7'
            border_color = '#123B72'
        elif b.status in [Booking.STATUS_SUBMITTED, Booking.STATUS_HOD_APPROVED, Booking.STATUS_COORDINATOR_APPROVED]:
            color = '#F59E0B'
            border_color = '#D97706'
        elif b.status == Booking.STATUS_REJECTED:
            color = '#DC2626'
            border_color = '#B91C1C'
        elif b.status == Booking.STATUS_CANCELLED:
            color = '#94A3B8'
            border_color = '#64748B'
        else:
            color = '#3B82F6'
            border_color = '#2563EB'

        events.append({
            'id': b.id,
            'booking_id': b.booking_id,
            'title': f"{b.event_name} ({hall.code})",
            'event_name': b.event_name,
            'hall_name': hall.name,
            'hall_code': hall.code,
            'department': b.department.code,
            'requested_by': b.user.get_full_name() or b.user.username,
            'event_type': b.event_type,
            'start': start_dt.isoformat(),
            'end': end_dt.isoformat(),
            'time_display': f"{b.start_time.strftime('%I:%M %p')} - {b.end_time.strftime('%I:%M %p')}",
            'status': b.get_status_display(),
            'status_raw': b.status,
            'backgroundColor': color,
            'borderColor': border_color,
            'detail_url': f"/bookings/{b.booking_id}/",
        })

    # Also show hall maintenance periods in grey
    maintenance_halls = Hall.objects.filter(is_under_maintenance=True)
    if hall_id:
        maintenance_halls = maintenance_halls.filter(id=hall_id)

    for mh in maintenance_halls:
        if mh.maintenance_start and mh.maintenance_end:
            events.append({
                'id': f"maint-{mh.id}",
                'booking_id': f"MAINT-{mh.code}",
                'title': f"[MAINTENANCE] {mh.name}",
                'event_name': f"Scheduled Maintenance: {mh.maintenance_reason or 'Inspection'}",
                'hall_name': mh.name,
                'hall_code': mh.code,
                'department': 'Estate Office',
                'requested_by': mh.responsible_person or 'Coordinator',
                'event_type': 'Maintenance',
                'start': mh.maintenance_start.isoformat(),
                'end': mh.maintenance_end.isoformat(),
                'time_display': f"{mh.maintenance_start.strftime('%I:%M %p')} - {mh.maintenance_end.strftime('%I:%M %p')}",
                'status': 'Maintenance Block',
                'status_raw': 'MAINTENANCE',
                'backgroundColor': '#64748B',
                'borderColor': '#475569',
                'detail_url': f"/halls/{mh.id}/",
            })

    return JsonResponse(events, safe=False)

@login_required
def hall_availability_view(request):
    """
    Interactive Hall Availability matrix for today or chosen date.
    """
    selected_date_str = request.GET.get('date', timezone.localdate().strftime('%Y-%m-%d'))
    try:
        selected_date = datetime.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        selected_date = timezone.localdate()

    halls = Hall.objects.prefetch_related('facilities').order_by('name')
    bookings_on_date = Booking.objects.filter(
        event_date=selected_date,
        status__in=[Booking.STATUS_APPROVED, Booking.STATUS_SUBMITTED, Booking.STATUS_HOD_APPROVED, Booking.STATUS_COORDINATOR_APPROVED]
    ).select_related('preferred_hall', 'allocated_hall', 'department')

    # Group bookings by hall
    hall_cards = []
    for hall in halls:
        hall_bookings = [b for b in bookings_on_date if b.get_active_hall().id == hall.id]
        hall_cards.append({
            'hall': hall,
            'bookings': hall_bookings,
            'is_busy': len(hall_bookings) > 0,
            'is_under_maintenance': hall.is_under_maintenance,
        })

    return render(request, 'halls/availability.html', {
        'selected_date': selected_date,
        'selected_date_str': selected_date.strftime('%Y-%m-%d'),
        'hall_cards': hall_cards,
    })
