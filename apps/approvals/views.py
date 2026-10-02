from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from apps.bookings.models import Booking
from apps.departments.models import Department
from apps.approvals.services import process_approval_action

@login_required
def pending_approvals_list_view(request):
    user = request.user
    profile = getattr(user, 'profile', None)

    if not (profile and profile.can_view_approvals):
        messages.error(request, "Access restricted. You do not have permission to view pending approvals.")
        return redirect('core:dashboard')

    stage_filter = request.GET.get('stage', '')
    dept_id = request.GET.get('department', '')
    search = request.GET.get('search', '').strip()

    bookings_qs = Booking.objects.select_related('user', 'department', 'preferred_hall', 'allocated_hall')

    if profile.is_admin_user:
        # Admin can view all pending stages
        bookings_qs = bookings_qs.filter(
            status__in=[Booking.STATUS_SUBMITTED, Booking.STATUS_HOD_APPROVED, Booking.STATUS_COORDINATOR_APPROVED]
        )
    elif profile.is_principal:
        bookings_qs = bookings_qs.filter(
            status=Booking.STATUS_COORDINATOR_APPROVED,
            current_approval_stage=Booking.STAGE_PRINCIPAL
        )
    elif profile.is_coordinator:
        bookings_qs = bookings_qs.filter(
            status=Booking.STATUS_HOD_APPROVED,
            current_approval_stage=Booking.STAGE_COORDINATOR
        )
    elif profile.is_hod:
        if profile.department:
            bookings_qs = bookings_qs.filter(
                department=profile.department,
                status=Booking.STATUS_SUBMITTED,
                current_approval_stage=Booking.STAGE_HOD
            )
        else:
            bookings_qs = bookings_qs.none()
    else:
        bookings_qs = bookings_qs.none()

    if stage_filter:
        bookings_qs = bookings_qs.filter(current_approval_stage=stage_filter)
    if dept_id:
        bookings_qs = bookings_qs.filter(department_id=dept_id)
    if search:
        bookings_qs = bookings_qs.filter(
            Q(booking_id__icontains=search) |
            Q(event_name__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )

    bookings_qs = bookings_qs.order_by('event_date', 'start_time')

    paginator = Paginator(bookings_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    departments = Department.objects.filter(is_active=True).order_by('name')

    return render(request, 'approvals/pending_list.html', {
        'page_obj': page_obj,
        'departments': departments,
        'stage_filter': stage_filter,
        'dept_id': dept_id,
        'search': search,
        'stage_choices': Booking.STAGE_CHOICES,
    })

@login_required
def approval_action_view(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id)
    profile = getattr(request.user, 'profile', None)

    if not (profile and profile.can_view_approvals):
        messages.error(request, "Access restricted.")
        return redirect('core:dashboard')

    if request.method == 'POST':
        action = request.POST.get('action') # 'APPROVE', 'REJECT', 'REQUEST_MODIFICATION'
        remarks = request.POST.get('remarks', '').strip()
        new_hall_id = request.POST.get('allocated_hall_id') or None

        success, msg = process_approval_action(
            request=request,
            booking=booking,
            action=action,
            remarks=remarks,
            new_allocated_hall_id=new_hall_id
        )

        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)

        return redirect('bookings:detail', booking_id=booking.booking_id)

    return redirect('bookings:detail', booking_id=booking.booking_id)
