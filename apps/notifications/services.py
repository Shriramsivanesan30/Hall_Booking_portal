import logging
from django.conf import settings
from django.core.mail import send_mail
from apps.notifications.models import Notification

logger = logging.getLogger(__name__)

def send_booking_notification(booking, notification_type, title, recipient=None, remarks=''):
    """
    Creates an in-app notification and dispatches an institutional email
    following the MCET notification template.
    """
    target_user = recipient or booking.user
    date_str = booking.event_date.strftime('%d %B %Y')
    time_str = f"{booking.start_time.strftime('%I:%M %p')} – {booking.end_time.strftime('%I:%M %p')}"
    hall_name = booking.get_active_hall().name
    status_display = booking.get_status_display()
    recipient_name = target_user.get_full_name() or target_user.username

    # In-App Notification Message
    in_app_msg = f"{booking.event_name} at {hall_name} on {date_str} ({time_str}). Status: {status_display}."
    if remarks:
        in_app_msg += f" Remarks: {remarks}"

    notification = Notification.objects.create(
        recipient=target_user,
        title=title,
        message=in_app_msg,
        booking=booking,
        notification_type=notification_type
    )

    # Standard Institutional Email Template
    subject = f"MCET Seminar Hall Booking Update – {booking.booking_id}"

    body = f"""Dear {recipient_name},

Your seminar hall booking request has been updated.

Booking ID: {booking.booking_id}
Event: {booking.event_name}
Department: {booking.department.name}
Hall: {hall_name}
Date: {date_str}
Time: {time_str}
Status: {status_display}
"""
    if remarks:
        body += f"Remarks: {remarks}\n"

    body += """
Please log in to the MCET Seminar Hall Booking Portal to view the complete details.

Regards,
MCET College ERP
Dr. Mahalingam College of Engineering and Technology
https://booking.dexoshpuse.com
"""

    if target_user.email:
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[target_user.email],
                fail_silently=True
            )
        except Exception as e:
            logger.warning(f"Failed to send email to {target_user.email}: {e}")

    return notification
