import datetime
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.utils import timezone
from apps.departments.models import Department
from apps.halls.models import Hall
from apps.bookings.models import Booking
from apps.accounts.models import UserProfile
from apps.bookings.services import check_hall_availability
from apps.approvals.services import process_approval_action

class SmartAvailabilityValidationTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(code='IT', name='Information Technology')
        self.hall = Hall.objects.create(
            name='Seminar Hall 1',
            code='SH-01',
            building='Mechanical Block',
            floor='1st Floor',
            capacity=100,
            is_active=True,
            is_under_maintenance=False
        )
        self.user = User.objects.create_user(
            username='faculty.it@mcet.in',
            email='faculty.it@mcet.in',
            password='testpassword'
        )
        self.profile = self.user.profile
        self.profile.role = UserProfile.ROLE_FACULTY
        self.profile.department = self.dept
        self.profile.save()

        # Seed an existing confirmed booking tomorrow 10:00 AM to 12:00 PM
        self.tomorrow = timezone.localdate() + datetime.timedelta(days=1)
        self.confirmed_booking = Booking.objects.create(
            booking_id='BK-2026-TEST',
            user=self.user,
            department=self.dept,
            event_name='AI Conference',
            event_type='Seminar',
            expected_participants=80,
            event_date=self.tomorrow,
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
            preferred_hall=self.hall,
            allocated_hall=self.hall,
            status=Booking.STATUS_APPROVED,
            current_approval_stage=Booking.STAGE_COMPLETED
        )

    def test_overlapping_slot_rejected(self):
        """Verifies that an overlapping booking on the same hall is detected and rejected."""
        res = check_hall_availability(
            hall_id=self.hall.id,
            event_date=self.tomorrow,
            start_time='11:00',
            end_time='13:00',
            participants=50
        )
        self.assertFalse(res['is_available'])
        self.assertTrue(any('already booked' in e for e in res['errors']))
        self.assertEqual(len(res['conflicts']), 1)

    def test_non_overlapping_slot_accepted(self):
        """Verifies that an afternoon slot with no overlap is accepted."""
        res = check_hall_availability(
            hall_id=self.hall.id,
            event_date=self.tomorrow,
            start_time='14:00',
            end_time='16:00',
            participants=50
        )
        self.assertTrue(res['is_available'])
        self.assertEqual(len(res['errors']), 0)

    def test_capacity_exceeded_rejected(self):
        """Verifies that exceeding hall seating capacity returns validation error."""
        res = check_hall_availability(
            hall_id=self.hall.id,
            event_date=self.tomorrow,
            start_time='14:00',
            end_time='16:00',
            participants=150 # Hall capacity is 100
        )
        self.assertFalse(res['is_available'])
        self.assertTrue(any('exceeds hall maximum capacity' in e for e in res['errors']))

    def test_past_date_rejected(self):
        """Verifies that selecting past date returns error."""
        past_date = timezone.localdate() - datetime.timedelta(days=2)
        res = check_hall_availability(
            hall_id=self.hall.id,
            event_date=past_date,
            start_time='10:00',
            end_time='12:00',
            participants=50
        )
        self.assertFalse(res['is_available'])
        self.assertTrue(any('cannot be in the past' in e for e in res['errors']))

    def test_maintenance_hall_rejected(self):
        """Verifies that an active hall under maintenance is blocked."""
        self.hall.is_under_maintenance = True
        self.hall.maintenance_reason = "AV System Overhaul"
        self.hall.save()

        res = check_hall_availability(
            hall_id=self.hall.id,
            event_date=self.tomorrow,
            start_time='14:00',
            end_time='16:00',
            participants=50
        )
        self.assertFalse(res['is_available'])
        self.assertTrue(any('maintenance' in e.lower() for e in res['errors']))


class ApprovalWorkflowPipelineTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.dept = Department.objects.create(code='IT', name='Information Technology')
        self.hall = Hall.objects.create(name='Seminar Hall 1', code='SH-01', building='Mech', floor='1', capacity=100)

        # Create Users
        self.faculty = User.objects.create_user(username='fac', password='p')
        self.faculty.profile.role = UserProfile.ROLE_FACULTY
        self.faculty.profile.department = self.dept
        self.faculty.profile.save()

        self.hod = User.objects.create_user(username='hod', password='p')
        self.hod.profile.role = UserProfile.ROLE_HOD
        self.hod.profile.department = self.dept
        self.hod.profile.save()

        self.coord = User.objects.create_user(username='coord', password='p')
        self.coord.profile.role = UserProfile.ROLE_COORDINATOR
        self.coord.profile.save()

        self.principal = User.objects.create_user(username='prin', password='p')
        self.principal.profile.role = UserProfile.ROLE_PRINCIPAL
        self.principal.profile.save()

        self.booking = Booking.objects.create(
            booking_id='BK-WF-001',
            user=self.faculty,
            department=self.dept,
            event_name='Workflow Test Event',
            expected_participants=50,
            event_date=timezone.localdate() + datetime.timedelta(days=5),
            start_time=datetime.time(9, 0),
            end_time=datetime.time(11, 0),
            preferred_hall=self.hall,
            allocated_hall=self.hall,
            status=Booking.STATUS_SUBMITTED,
            current_approval_stage=Booking.STAGE_HOD
        )

    def test_complete_approval_chain(self):
        """Tests complete pipeline: HOD -> Coordinator -> Principal -> Approved"""
        # 1. HOD Approves
        req_hod = self.factory.post('/approvals/action/')
        req_hod.user = self.hod
        success, msg = process_approval_action(req_hod, self.booking, 'APPROVE', remarks='HOD Approved')
        self.assertTrue(success)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.STATUS_HOD_APPROVED)
        self.assertEqual(self.booking.current_approval_stage, Booking.STAGE_COORDINATOR)

        # 2. Coordinator Approves
        req_coord = self.factory.post('/approvals/action/')
        req_coord.user = self.coord
        success, msg = process_approval_action(req_coord, self.booking, 'APPROVE', remarks='Coordinator Checked AV')
        self.assertTrue(success)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.STATUS_COORDINATOR_APPROVED)
        self.assertEqual(self.booking.current_approval_stage, Booking.STAGE_PRINCIPAL)

        # 3. Principal Approves
        req_prin = self.factory.post('/approvals/action/')
        req_prin.user = self.principal
        success, msg = process_approval_action(req_prin, self.booking, 'APPROVE', remarks='Final Approval Sanctioned')
        self.assertTrue(success)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.STATUS_APPROVED)
        self.assertEqual(self.booking.current_approval_stage, Booking.STAGE_COMPLETED)

    def test_rejection_requires_reason(self):
        """Verifies rejection is rejected if remarks are empty."""
        req_hod = self.factory.post('/approvals/action/')
        req_hod.user = self.hod
        success, msg = process_approval_action(req_hod, self.booking, 'REJECT', remarks='')
        self.assertFalse(success)
        self.assertIn("reason", msg.lower())
