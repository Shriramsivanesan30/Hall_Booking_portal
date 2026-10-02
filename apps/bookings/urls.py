from django.urls import path
from apps.bookings import views

app_name = 'bookings'

urlpatterns = [
    path('new/', views.new_booking_view, name='new_booking'),
    path('my-bookings/', views.my_bookings_view, name='my_bookings'),
    path('approved/', views.approved_bookings_view, name='approved_bookings'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('availability/', views.hall_availability_view, name='hall_availability'),
    path('api/check-availability/', views.api_check_availability, name='api_check_availability'),
    path('api/calendar-events/', views.api_calendar_events, name='api_calendar_events'),
    path('<str:booking_id>/', views.booking_detail_view, name='detail'),
    path('<str:booking_id>/edit/', views.edit_booking_view, name='edit'),
    path('<str:booking_id>/cancel/', views.cancel_booking_view, name='cancel'),
]
