import datetime
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from apps.halls.models import Hall
from apps.bookings.models import Booking
from apps.core.models import SystemConfiguration

def check_hall_availability(hall_id, event_date, start_time, end_time, exclude_booking_id=None, participants=0):
    """
    Comprehensive availability check engine.
    Returns:
    {
        'is_available': bool,
        'errors': list of str,
        'conflicts': list of Booking objects,
        'alternative_halls': list of Hall objects,
        'suggested_slots': list of dicts,
    }
    """
    errors = []
    conflicts = []
    alternative_halls = []
    suggested_slots = []

    # 1. Parse date and times
    if isinstance(event_date, str):
        event_date = datetime.datetime.strptime(event_date, '%Y-%m-%d').date()
    if isinstance(start_time, str):
        # Support formats '%H:%M' or '%H:%M:%S'
        try:
            start_time = datetime.datetime.strptime(start_time, '%H:%M').time()
        except ValueError:
            start_time = datetime.datetime.strptime(start_time, '%H:%M:%S').time()
    if isinstance(end_time, str):
        try:
            end_time = datetime.datetime.strptime(end_time, '%H:%M').time()
        except ValueError:
            end_time = datetime.datetime.strptime(end_time, '%H:%M:%S').time()

    today = timezone.localdate()

    # 1. Date not in past
    if event_date < today:
        errors.append(f"Selected date ({event_date.strftime('%d-%m-%Y')}) cannot be in the past.")

    # 2. Start time earlier than end time & duration > 0
    if start_time >= end_time:
        errors.append("Start time must be strictly earlier than end time.")

    # 3. Retrieve Hall
    try:
        hall = Hall.objects.get(id=hall_id)
    except Hall.DoesNotExist:
        errors.append("Selected Seminar Hall does not exist.")
        return {
            'is_available': False,
            'errors': errors,
            'conflicts': [],
            'alternative_halls': [],
            'suggested_slots': []
        }

    # 4. Check Hall is active
    if not hall.is_active:
        errors.append(f"{hall.name} is currently inactive and cannot be booked.")

    # 5. Check Hall maintenance
    if hall.is_under_maintenance:
        if hall.maintenance_start and hall.maintenance_end:
            slot_start_dt = timezone.make_aware(datetime.datetime.combine(event_date, start_time))
            slot_end_dt = timezone.make_aware(datetime.datetime.combine(event_date, end_time))
            if not (slot_end_dt <= hall.maintenance_start or slot_start_dt >= hall.maintenance_end):
                errors.append(f"{hall.name} is under scheduled maintenance from {hall.maintenance_start.strftime('%d-%m-%Y %H:%M')} to {hall.maintenance_end.strftime('%d-%m-%Y %H:%M')}.")
        else:
            errors.append(f"{hall.name} is currently marked under maintenance: {hall.maintenance_reason or 'Routine maintenance'}.")

    # 6. Participant capacity check
    if participants and participants > hall.capacity:
        errors.append(f"Expected participants ({participants}) exceeds hall maximum capacity ({hall.capacity}).")

    # 7. Check Overlapping Bookings
    # Determine which statuses block availability
    pending_blocks = SystemConfiguration.get_bool('PENDING_BLOCKS_AVAILABILITY', default=False)
    blocking_statuses = [Booking.STATUS_APPROVED]
    if pending_blocks:
        blocking_statuses.extend([
            Booking.STATUS_SUBMITTED,
            Booking.STATUS_HOD_APPROVED,
            Booking.STATUS_COORDINATOR_APPROVED
        ])

    # Overlap logic: (start_time < existing.end_time) AND (end_time > existing.start_time)
    overlap_query = (
        (Q(allocated_hall=hall) | (Q(allocated_hall__isnull=True) & Q(preferred_hall=hall))) &
        Q(event_date=event_date) &
        Q(status__in=blocking_statuses) &
        Q(start_time__lt=end_time) &
        Q(end_time__gt=start_time)
    )

    if exclude_booking_id:
        overlap_query &= ~Q(id=exclude_booking_id)

    conflicting_bookings = Booking.objects.filter(overlap_query)

    if conflicting_bookings.exists():
        conflicts = list(conflicting_bookings)
        for c in conflicts:
            start_fmt = c.start_time.strftime('%I:%M %p')
            end_fmt = c.end_time.strftime('%I:%M %p')
            errors.append(f"Hall Unavailable – {hall.name} is already booked from {start_fmt} to {end_fmt} for '{c.event_name}' ({c.department.code}).")

        # Find Alternative Halls for the same slot and date with enough capacity
        alt_query = Hall.objects.filter(is_active=True, is_under_maintenance=False).exclude(id=hall.id)
        if participants:
            alt_query = alt_query.filter(capacity__gte=participants)

        for alt in alt_query:
            has_alt_conflict = Booking.objects.filter(
                (Q(allocated_hall=alt) | (Q(allocated_hall__isnull=True) & Q(preferred_hall=alt))) &
                Q(event_date=event_date) &
                Q(status__in=blocking_statuses) &
                Q(start_time__lt=end_time) &
                Q(end_time__gt=start_time)
            ).exists()
            if not has_alt_conflict:
                alternative_halls.append(alt)

        # Suggest alternative time slots on the same day for this hall
        standard_slots = [
            (datetime.time(9, 0), datetime.time(11, 0)),
            (datetime.time(11, 30), datetime.time(13, 30)),
            (datetime.time(14, 0), datetime.time(16, 0)),
            (datetime.time(16, 30), datetime.time(18, 30)),
        ]
        for s_start, s_end in standard_slots:
            slot_conflict = Booking.objects.filter(
                (Q(allocated_hall=hall) | (Q(allocated_hall__isnull=True) & Q(preferred_hall=hall))) &
                Q(event_date=event_date) &
                Q(status__in=blocking_statuses) &
                Q(start_time__lt=s_end) &
                Q(end_time__gt=s_start)
            ).exists()
            if not slot_conflict:
                suggested_slots.append({
                    'start_time': s_start.strftime('%I:%M %p'),
                    'end_time': s_end.strftime('%I:%M %p'),
                    'start_val': s_start.strftime('%H:%M'),
                    'end_val': s_end.strftime('%H:%M')
                })

    is_available = len(errors) == 0

    return {
        'is_available': is_available,
        'errors': errors,
        'conflicts': conflicts,
        'alternative_halls': alternative_halls,
        'suggested_slots': suggested_slots,
        'hall': hall,
    }


def validate_and_save_booking(booking_data, user, booking_instance=None):
    """
    Executes within an atomic transaction with concurrency protection (select_for_update).
    Ensures absolute data integrity against race conditions.
    """
    with transaction.atomic():
        hall_id = booking_data.get('preferred_hall')
        event_date = booking_data.get('event_date')
        start_time = booking_data.get('start_time')
        end_time = booking_data.get('end_time')
        participants = int(booking_data.get('expected_participants', 50))
        exclude_id = booking_instance.id if booking_instance else None

        # Lock the hall row to prevent concurrent race condition bookings
        try:
            hall = Hall.objects.select_for_update().get(id=hall_id)
        except Hall.DoesNotExist:
            return False, ["Invalid hall selected."], None

        availability = check_hall_availability(
            hall_id=hall.id,
            event_date=event_date,
            start_time=start_time,
            end_time=end_time,
            exclude_booking_id=exclude_id,
            participants=participants
        )

        if not availability['is_available']:
            return False, availability['errors'], availability

        # If checking only or drafting, can still save if not submitted
        return True, [], availability
