from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from apps.notifications.models import Notification

@login_required
def notification_list_view(request):
    notifications_qs = Notification.objects.filter(recipient=request.user).order_by('-created_at')

    filter_type = request.GET.get('filter')
    if filter_type == 'unread':
        notifications_qs = notifications_qs.filter(is_read=False)

    paginator = Paginator(notifications_qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'notifications/list.html', {
        'page_obj': page_obj,
        'filter_type': filter_type,
    })

@login_required
def mark_notification_read(request, notif_id):
    notif = get_object_or_404(Notification, id=notif_id, recipient=request.user)
    notif.is_read = True
    notif.save()

    if notif.booking:
        return redirect('bookings:detail', booking_id=notif.booking.booking_id)
    return redirect('notifications:list')

@login_required
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect('notifications:list')
