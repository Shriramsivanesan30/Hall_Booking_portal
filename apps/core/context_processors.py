from django.db.models import Q
from apps.bookings.models import Booking
from apps.notifications.models import Notification
from apps.core.models import SystemConfiguration

def global_context(request):
    if not request.user.is_authenticated:
        return {
            'pending_approvals_count': 0,
            'unread_notifications_count': 0,
            'recent_notifications': [],
            'app_name': 'MCET Seminar Hall Booking System',
            'institution_name': 'Dr. Mahalingam College of Engineering and Technology',
        }

    user = request.user
    profile = getattr(user, 'profile', None)

    # 1. Unread notifications
    unread_notifications_qs = Notification.objects.filter(recipient=user, is_read=False)
    unread_count = unread_notifications_qs.count()
    recent_notifications = unread_notifications_qs[:5]

    # 2. Pending approvals count according to user role
    pending_count = 0
    if profile:
        if profile.is_admin_user:
            pending_count = Booking.objects.filter(
                status__in=[Booking.STATUS_SUBMITTED, Booking.STATUS_HOD_APPROVED, Booking.STATUS_COORDINATOR_APPROVED]
            ).count()
        elif profile.is_principal:
            pending_count = Booking.objects.filter(
                status=Booking.STATUS_COORDINATOR_APPROVED,
                current_approval_stage=Booking.STAGE_PRINCIPAL
            ).count()
        elif profile.is_coordinator:
            pending_count = Booking.objects.filter(
                status=Booking.STATUS_HOD_APPROVED,
                current_approval_stage=Booking.STAGE_COORDINATOR
            ).count()
        elif profile.is_hod:
            if profile.department:
                pending_count = Booking.objects.filter(
                    department=profile.department,
                    status=Booking.STATUS_SUBMITTED,
                    current_approval_stage=Booking.STAGE_HOD
                ).count()

    return {
        'pending_approvals_count': pending_count,
        'unread_notifications_count': unread_count,
        'recent_notifications': recent_notifications,
        'app_name': 'MCET Seminar Hall Booking System',
        'institution_name': 'Dr. Mahalingam College of Engineering and Technology',
        'user_profile': profile,
    }
