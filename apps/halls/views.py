from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from apps.halls.models import Hall, HallFacility
from apps.bookings.models import Booking
from apps.audit.models import log_audit

FACILITIES_CATALOG = [
    'Projector',
    'Audio System',
    'Microphone',
    'Wi-Fi',
    'Video Conferencing',
    'Air Conditioning',
    'Stage',
    'Recording Facility',
]

def can_manage_halls(user):
    if not user.is_authenticated:
        return False
    profile = getattr(user, 'profile', None)
    return user.is_superuser or (profile and (profile.is_coordinator or profile.is_admin_user))

@login_required
def hall_list_view(request):
    halls = Hall.objects.prefetch_related('facilities').order_by('name')
    return render(request, 'halls/list.html', {
        'halls': halls,
        'can_manage': can_manage_halls(request.user)
    })

@login_required
def hall_detail_view(request, hall_id):
    hall = get_object_or_404(Hall.objects.prefetch_related('facilities'), id=hall_id)
    upcoming_bookings = Booking.objects.filter(
        allocated_hall=hall,
        event_date__gte=timezone.localdate(),
        status=Booking.STATUS_APPROVED
    ).order_by('event_date', 'start_time')[:10]

    return render(request, 'halls/detail.html', {
        'hall': hall,
        'upcoming_bookings': upcoming_bookings,
        'can_manage': can_manage_halls(request.user)
    })

@login_required
def hall_create_view(request):
    if not can_manage_halls(request.user):
        messages.error(request, "Access denied. Only Seminar Hall Coordinator or Administrators can add halls.")
        return redirect('halls:list')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().upper()
        building = request.POST.get('building', '').strip()
        floor = request.POST.get('floor', '').strip()
        capacity = int(request.POST.get('capacity', 100))
        location = request.POST.get('location', '').strip()
        responsible_person = request.POST.get('responsible_person', '').strip()
        responsible_contact = request.POST.get('responsible_contact', '').strip()

        if Hall.objects.filter(name=name).exists() or Hall.objects.filter(code=code).exists():
            messages.error(request, "Hall with this name or code already exists.")
            return render(request, 'halls/form.html', {'action': 'Add', 'facilities_catalog': FACILITIES_CATALOG})

        hall = Hall.objects.create(
            name=name,
            code=code,
            building=building,
            floor=floor,
            capacity=capacity,
            location=location,
            responsible_person=responsible_person,
            responsible_contact=responsible_contact,
            is_active=True
        )

        # Create facility records
        selected_facs = request.POST.getlist('facilities')
        for fac_name in FACILITIES_CATALOG:
            HallFacility.objects.create(
                hall=hall,
                name=fac_name,
                is_available=(fac_name in selected_facs)
            )

        log_audit(
            request=request,
            action='HALL_CREATE',
            model_name='Hall',
            object_id=hall.id,
            updated_value=f"Created {hall.name} ({hall.code})"
        )

        messages.success(request, f"Seminar Hall '{hall.name}' created successfully.")
        return redirect('halls:detail', hall_id=hall.id)

    return render(request, 'halls/form.html', {'action': 'Add', 'facilities_catalog': FACILITIES_CATALOG})

@login_required
def hall_edit_view(request, hall_id):
    if not can_manage_halls(request.user):
        messages.error(request, "Access denied.")
        return redirect('halls:list')

    hall = get_object_or_404(Hall, id=hall_id)

    if request.method == 'POST':
        hall.name = request.POST.get('name', '').strip()
        hall.code = request.POST.get('code', '').strip().upper()
        hall.building = request.POST.get('building', '').strip()
        hall.floor = request.POST.get('floor', '').strip()
        hall.capacity = int(request.POST.get('capacity', 100))
        hall.location = request.POST.get('location', '').strip()
        hall.responsible_person = request.POST.get('responsible_person', '').strip()
        hall.responsible_contact = request.POST.get('responsible_contact', '').strip()
        hall.is_active = 'is_active' in request.POST
        hall.save()

        # Update facilities
        selected_facs = request.POST.getlist('facilities')
        for fac_name in FACILITIES_CATALOG:
            facility, _ = HallFacility.objects.get_or_create(hall=hall, name=fac_name)
            facility.is_available = (fac_name in selected_facs)
            facility.save()

        log_audit(
            request=request,
            action='HALL_UPDATE',
            model_name='Hall',
            object_id=hall.id,
            updated_value=f"Updated {hall.name}"
        )

        messages.success(request, f"Seminar Hall '{hall.name}' updated successfully.")
        return redirect('halls:detail', hall_id=hall.id)

    current_facilities = hall.facilities.filter(is_available=True).values_list('name', flat=True)

    return render(request, 'halls/form.html', {
        'hall': hall,
        'action': 'Edit',
        'facilities_catalog': FACILITIES_CATALOG,
        'current_facilities': list(current_facilities)
    })

@login_required
def hall_maintenance_toggle_view(request, hall_id):
    if not can_manage_halls(request.user):
        messages.error(request, "Access denied.")
        return redirect('halls:list')

    hall = get_object_or_404(Hall, id=hall_id)

    if request.method == 'POST':
        is_maintenance = request.POST.get('is_under_maintenance') == '1'
        reason = request.POST.get('maintenance_reason', '').strip()

        hall.is_under_maintenance = is_maintenance
        hall.maintenance_reason = reason if is_maintenance else ''
        hall.save()

        log_audit(
            request=request,
            action='HALL_MAINTENANCE',
            model_name='Hall',
            object_id=hall.id,
            updated_value=f"Maintenance: {is_maintenance}, Reason: {reason}"
        )

        status_str = "marked under maintenance" if is_maintenance else "restored to active operation"
        messages.success(request, f"{hall.name} has been {status_str}.")
        return redirect('halls:detail', hall_id=hall.id)

    return redirect('halls:detail', hall_id=hall.id)

@login_required
def hall_history_view(request, hall_id):
    hall = get_object_or_404(Hall, id=hall_id)
    bookings = Booking.objects.filter(allocated_hall=hall).order_by('-event_date', '-start_time')

    return render(request, 'halls/history.html', {
        'hall': hall,
        'bookings': bookings
    })
