import os
import sys
import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from apps.accounts.models import UserProfile
from apps.departments.models import Department
from apps.halls.models import Hall, HallFacility
from apps.bookings.models import Booking
from apps.approvals.models import ApprovalHistory
from apps.notifications.models import Notification
from apps.core.models import SystemConfiguration

class Command(BaseCommand):
    help = 'Seeds realistic sample data for MCET Seminar Hall Booking System'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding MCET Seminar Hall Booking System data..."))

        # 1. System Configurations
        SystemConfiguration.set_value('PENDING_BLOCKS_AVAILABILITY', 'False', 'Whether pending requests reserve hall availability', 'boolean')
        SystemConfiguration.set_value('ALLOW_WEEKEND_BOOKINGS', 'True', 'Allow booking seminar halls on Saturdays and Sundays', 'boolean')
        SystemConfiguration.set_value('MAX_ADVANCE_BOOKING_DAYS', '90', 'Maximum advance booking window in days', 'integer')

        # 2. Departments
        departments_data = [
            {'code': 'IT', 'name': 'Information Technology', 'hod_name': 'Dr. K. Ramasamy', 'contact_email': 'hod.it@mcet.in', 'phone': '04259-236030'},
            {'code': 'CSE', 'name': 'Computer Science and Engineering', 'hod_name': 'Dr. S. Sivakumar', 'contact_email': 'hod.cse@mcet.in', 'phone': '04259-236031'},
            {'code': 'ECE', 'name': 'Electronics and Communication Engineering', 'hod_name': 'Dr. R. Sudhakar', 'contact_email': 'hod.ece@mcet.in', 'phone': '04259-236032'},
            {'code': 'EEE', 'name': 'Electrical and Electronics Engineering', 'hod_name': 'Dr. A. Senthilkumar', 'contact_email': 'hod.eee@mcet.in', 'phone': '04259-236033'},
            {'code': 'MECH', 'name': 'Mechanical Engineering', 'hod_name': 'Dr. I. Rajendran', 'contact_email': 'hod.mech@mcet.in', 'phone': '04259-236034'},
            {'code': 'CIVIL', 'name': 'Civil Engineering', 'hod_name': 'Dr. G. Jaisankar', 'contact_email': 'hod.civil@mcet.in', 'phone': '04259-236035'},
            {'code': 'AIDS', 'name': 'Artificial Intelligence and Data Science', 'hod_name': 'Dr. M. Balakrishnan', 'contact_email': 'hod.aids@mcet.in', 'phone': '04259-236036'},
            {'code': 'CSBS', 'name': 'Computer Science and Business Systems', 'hod_name': 'Dr. P. Sathiyamurthi', 'contact_email': 'hod.csbs@mcet.in', 'phone': '04259-236037'},
            {'code': 'S&H', 'name': 'Science and Humanities', 'hod_name': 'Dr. V. Lakshmanan', 'contact_email': 'hod.sh@mcet.in', 'phone': '04259-236038'},
            {'code': 'MS', 'name': 'Management Studies', 'hod_name': 'Dr. N. Senthilvel', 'contact_email': 'hod.ms@mcet.in', 'phone': '04259-236039'},
        ]

        depts_dict = {}
        for d in departments_data:
            dept, _ = Department.objects.update_or_create(
                code=d['code'],
                defaults=d
            )
            depts_dict[d['code']] = dept
        self.stdout.write(self.style.SUCCESS(f"Created/Updated {len(depts_dict)} Departments."))

        # 3. Seminar Halls & Facilities
        halls_data = [
            {
                'name': 'Seminar Hall 1',
                'code': 'SH-01',
                'building': 'Mechanical Block',
                'floor': '1st Floor',
                'capacity': 200,
                'location': 'Near Central Library & CAD Lab',
                'responsible_person': 'Prof. M. Selvakumar',
                'responsible_contact': '+91 94433 12345',
            },
            {
                'name': 'Seminar Hall 2',
                'code': 'SH-02',
                'building': 'Centenary Block',
                'floor': 'Ground Floor',
                'capacity': 100,
                'location': 'Opposite Dean Academic Office',
                'responsible_person': 'Prof. K. Venkatesh',
                'responsible_contact': '+91 94433 23456',
            },
            {
                'name': 'Conference Hall',
                'code': 'CH-01',
                'building': 'Admin Block',
                'floor': '2nd Floor',
                'capacity': 60,
                'location': 'Adjacent to Principal Board Room',
                'responsible_person': 'Dr. P. Govindasamy',
                'responsible_contact': '+91 94433 34567',
            },
            {
                'name': 'Seminar Hall 3',
                'code': 'SH-03',
                'building': 'Electrical Block',
                'floor': '1st Floor',
                'capacity': 150,
                'location': 'Near Power Electronics Lab',
                'responsible_person': 'Prof. T. Arunkumar',
                'responsible_contact': '+91 94433 45678',
            },
            {
                'name': 'Seminar Hall 4',
                'code': 'SH-04',
                'building': 'Computer Science Block',
                'floor': '2nd Floor',
                'capacity': 120,
                'location': 'Near IoT Center of Excellence',
                'responsible_person': 'Prof. S. Karthikeyan',
                'responsible_contact': '+91 94433 56789',
            },
        ]

        halls_dict = {}
        for h in halls_data:
            hall, _ = Hall.objects.update_or_create(code=h['code'], defaults=h)
            halls_dict[h['code']] = hall

            # Add Facilities
            facilities_list = [
                ('Projector', True, 'Full HD Laser Projector with Motorized Screen'),
                ('Audio System', True, 'JBL Surround Sound System with Mixer'),
                ('Microphone', True, '2 Cordless Handheld Mics + 1 Collar Mic'),
                ('Wi-Fi', True, 'High-Speed Campus Wi-Fi 300 Mbps'),
                ('Video Conferencing', True, 'Logitech Rally 4K PTZ Camera Setup'),
                ('Air Conditioning', True, 'Centralized Inverter AC Units'),
                ('Stage', True, 'Podium + Dais for 6 Dignitaries'),
                ('Recording Facility', True if h['code'] in ['SH-01', 'CH-01'] else False, 'HD Video Recording setup'),
            ]
            for fac_name, is_avail, details in facilities_list:
                HallFacility.objects.update_or_create(
                    hall=hall,
                    name=fac_name,
                    defaults={'is_available': is_avail, 'details': details}
                )

        self.stdout.write(self.style.SUCCESS(f"Created/Updated {len(halls_dict)} Seminar Halls with Facilities."))

        # 4. User Accounts & Roles
        users_data = [
            {
                'username': 'admin@mcet.in',
                'email': 'admin@mcet.in',
                'first_name': 'System',
                'last_name': 'Administrator',
                'password': 'mcet@admin2026',
                'role': UserProfile.ROLE_ADMIN,
                'department': None,
                'emp_id': 'EMP-ADM-001',
                'designation': 'ERP System Administrator',
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'username': 'principal@mcet.in',
                'email': 'principal@mcet.in',
                'first_name': 'Dr. P.',
                'last_name': 'Govindasamy',
                'password': 'mcet@principal2026',
                'role': UserProfile.ROLE_PRINCIPAL,
                'department': None,
                'emp_id': 'EMP-PRI-001',
                'designation': 'Principal',
                'is_staff': True,
                'is_superuser': False,
            },
            {
                'username': 'coordinator@mcet.in',
                'email': 'coordinator@mcet.in',
                'first_name': 'Prof. M.',
                'last_name': 'Selvakumar',
                'password': 'mcet@coord2026',
                'role': UserProfile.ROLE_COORDINATOR,
                'department': depts_dict['MECH'],
                'emp_id': 'EMP-COR-001',
                'designation': 'Estate & Hall Coordinator',
                'is_staff': True,
                'is_superuser': False,
            },
            {
                'username': 'hod.it@mcet.in',
                'email': 'hod.it@mcet.in',
                'first_name': 'Dr. K.',
                'last_name': 'Ramasamy',
                'password': 'mcet@hod2026',
                'role': UserProfile.ROLE_HOD,
                'department': depts_dict['IT'],
                'emp_id': 'EMP-HOD-IT01',
                'designation': 'Professor & Head (IT)',
                'is_staff': False,
                'is_superuser': False,
            },
            {
                'username': 'faculty.it@mcet.in',
                'email': 'faculty.it@mcet.in',
                'first_name': 'Dr. R.',
                'last_name': 'Menaka',
                'password': 'mcet@faculty2026',
                'role': UserProfile.ROLE_FACULTY,
                'department': depts_dict['IT'],
                'emp_id': 'EMP-FAC-IT12',
                'designation': 'Associate Professor (IT)',
                'is_staff': False,
                'is_superuser': False,
            },
            {
                'username': 'faculty.cse@mcet.in',
                'email': 'faculty.cse@mcet.in',
                'first_name': 'Dr. G.',
                'last_name': 'Anitha',
                'password': 'mcet@faculty2026',
                'role': UserProfile.ROLE_FACULTY,
                'department': depts_dict['CSE'],
                'emp_id': 'EMP-FAC-CS08',
                'designation': 'Assistant Professor (CSE)',
                'is_staff': False,
                'is_superuser': False,
            },
            {
                'username': '727624P80@mcet.in',
                'email': '727624P80@mcet.in',
                'first_name': 'Sri',
                'last_name': 'Ram',
                'password': 'mcet@student2026',
                'role': UserProfile.ROLE_STUDENT,
                'department': depts_dict['IT'],
                'emp_id': '727624P80',
                'designation': 'Student Representative (IT)',
                'is_staff': False,
                'is_superuser': False,
            },
        ]

        users_dict = {}
        for u in users_data:
            user, created = User.objects.get_or_create(username=u['username'], defaults={
                'email': u['email'],
                'first_name': u['first_name'],
                'last_name': u['last_name'],
                'is_staff': u['is_staff'],
                'is_superuser': u['is_superuser']
            })
            user.set_password(u['password'])
            user.save()

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = u['role']
            profile.department = u['department']
            profile.employee_roll_no = u['emp_id']
            profile.designation = u['designation']
            profile.save()

            users_dict[u['username']] = user

        self.stdout.write(self.style.SUCCESS(f"Created/Updated {len(users_dict)} Sample User Accounts."))

        # 5. Bookings: 20+ realistic bookings (10 approved, 5 pending, 3 rejected, 2 cancelled)
        today = timezone.localdate()
        year = today.year

        # Clear existing sample bookings to ensure clean fresh seed
        Booking.objects.all().delete()

        bookings_spec = [
            # --- 10 APPROVED / CONFIRMED BOOKINGS ---
            # 1. Today morning - SH-01 (Approved)
            {
                'id': f'BK-{year}-001',
                'user': users_dict['faculty.it@mcet.in'],
                'dept': depts_dict['IT'],
                'name': 'Hands-on Workshop on Generative AI & LLMs',
                'type': 'Workshop',
                'participants': 120,
                'date': today,
                'start': datetime.time(9, 30),
                'end': datetime.time(12, 30),
                'hall': halls_dict['SH-01'],
                'status': Booking.STATUS_APPROVED,
                'stage': Booking.STAGE_COMPLETED,
                'chief': 'Mr. Rajesh Kannan, Staff Engineer, Google India',
                'desc': 'Interactive practical lab session on fine-tuning foundational models.',
            },
            # 2. Today afternoon - SH-02 (Approved)
            {
                'id': f'BK-{year}-002',
                'user': users_dict['faculty.cse@mcet.in'],
                'dept': depts_dict['CSE'],
                'name': 'Cloud Computing & DevOps Masterclass',
                'type': 'Guest Lecture',
                'participants': 80,
                'date': today,
                'start': datetime.time(14, 0),
                'end': datetime.time(16, 30),
                'hall': halls_dict['SH-02'],
                'status': Booking.STATUS_APPROVED,
                'stage': Booking.STAGE_COMPLETED,
                'chief': 'Ms. Priyadarshini, AWS Certified Solutions Architect',
                'desc': 'Architecting modern microservices on AWS and Kubernetes CI/CD.',
            },
            # 3. Tomorrow - SH-01 (Approved)
            {
                'id': f'BK-{year}-003',
                'user': users_dict['faculty.it@mcet.in'],
                'dept': depts_dict['AIDS'],
                'name': 'National Symposium on Data Intelligence & Edge AI',
                'type': 'Seminar',
                'participants': 180,
                'date': today + datetime.timedelta(days=1),
                'start': datetime.time(9, 0),
                'end': datetime.time(13, 0),
                'hall': halls_dict['SH-01'],
                'status': Booking.STATUS_APPROVED,
                'stage': Booking.STAGE_COMPLETED,
                'chief': 'Dr. Venkatesh Babu, Professor, IISc Bangalore',
                'desc': 'Keynote talks and technical paper presentation track.',
            },
            # 4. In 2 days - CH-01 (Approved)
            {
                'id': f'BK-{year}-004',
                'user': users_dict['hod.it@mcet.in'],
                'dept': depts_dict['IT'],
                'name': 'Academic Council & Board of Studies Curriculum Review',
                'type': 'Meeting',
                'participants': 35,
                'date': today + datetime.timedelta(days=2),
                'start': datetime.time(10, 0),
                'end': datetime.time(13, 0),
                'hall': halls_dict['CH-01'],
                'status': Booking.STATUS_APPROVED,
                'stage': Booking.STAGE_COMPLETED,
                'chief': 'Anna University Nominee & Industry Experts',
                'desc': 'Annual regulation and elective course revision meeting.',
            },
            # 5. In 3 days - SH-04 (Approved)
            {
                'id': f'BK-{year}-005',
                'user': users_dict['faculty.cse@mcet.in'],
                'dept': depts_dict['CSE'],
                'name': 'Full-Stack Web Development Bootcamp using Django',
                'type': 'Workshop',
                'participants': 100,
                'date': today + datetime.timedelta(days=3),
                'start': datetime.time(10, 0),
                'end': datetime.time(16, 0),
                'hall': halls_dict['SH-04'],
                'status': Booking.STATUS_APPROVED,
                'stage': Booking.STAGE_COMPLETED,
                'chief': 'Alumni Industry Mentors',
                'desc': 'Hands-on practical development for 3rd year students.',
            },
            # 6. In 4 days - SH-03 (Approved)
            {
                'id': f'BK-{year}-006',
                'user': users_dict['coordinator@mcet.in'],
                'dept': depts_dict['ECE'],
                'name': 'VLSI Architecture & Embedded Systems Seminar',
                'type': 'Seminar',
                'participants': 110,
                'date': today + datetime.timedelta(days=4),
                'start': datetime.time(10, 0),
                'end': datetime.time(12, 30),
                'hall': halls_dict['SH-03'],
                'status': Booking.STATUS_APPROVED,
                'stage': Booking.STAGE_COMPLETED,
                'chief': 'Er. S. Chandrasekar, Senior Director, Qualcomm',
                'desc': 'Recent trends in RISC-V SoC tape-out and hardware accelerator design.',
            },
            # 7. In 5 days - SH-01 (Approved)
            {
                'id': f'BK-{year}-007',
                'user': users_dict['faculty.it@mcet.in'],
                'dept': depts_dict['CSBS'],
                'name': 'FinTech Innovations & Enterprise Blockchain',
                'type': 'Guest Lecture',
                'participants': 140,
                'date': today + datetime.timedelta(days=5),
                'start': datetime.time(14, 0),
                'end': datetime.time(16, 30),
                'hall': halls_dict['SH-01'],
                'status': Booking.STATUS_APPROVED,
                'stage': Booking.STAGE_COMPLETED,
                'chief': 'Mr. Karthik Narayanan, VP, Barclays Technology',
                'desc': 'Distributed ledger implementations in modern banking.',
            },
            # 8. In 7 days - SH-02 (Approved)
            {
                'id': f'BK-{year}-008',
                'user': users_dict['faculty.cse@mcet.in'],
                'dept': depts_dict['MS'],
                'name': 'Leadership Conclave & Corporate Strategy',
                'type': 'Seminar',
                'participants': 90,
                'date': today + datetime.timedelta(days=7),
                'start': datetime.time(9, 30),
                'end': datetime.time(13, 0),
                'hall': halls_dict['SH-02'],
                'status': Booking.STATUS_APPROVED,
                'stage': Booking.STAGE_COMPLETED,
                'chief': 'Dr. Meenakshi Sundaram, HR Director',
                'desc': 'Interactive managerial debate and corporate case presentations.',
            },
            # 9. Past booking (3 days ago) - SH-01 (Approved)
            {
                'id': f'BK-{year}-009',
                'user': users_dict['faculty.it@mcet.in'],
                'dept': depts_dict['MECH'],
                'name': 'Smart Manufacturing & Industrial IoT Conclave',
                'type': 'Faculty Development Programme',
                'participants': 75,
                'date': today - datetime.timedelta(days=3),
                'start': datetime.time(10, 0),
                'end': datetime.time(16, 0),
                'hall': halls_dict['SH-01'],
                'status': Booking.STATUS_APPROVED,
                'stage': Booking.STAGE_COMPLETED,
                'chief': 'Siemens Industry Training Experts',
                'desc': 'FDP covering PLC automation and digital twins.',
            },
            # 10. Past booking (5 days ago) - SH-03 (Approved)
            {
                'id': f'BK-{year}-010',
                'user': users_dict['faculty.cse@mcet.in'],
                'dept': depts_dict['CIVIL'],
                'name': 'Sustainable Infrastructure & Green Buildings Seminar',
                'type': 'Seminar',
                'participants': 95,
                'date': today - datetime.timedelta(days=5),
                'start': datetime.time(11, 0),
                'end': datetime.time(13, 30),
                'hall': halls_dict['SH-03'],
                'status': Booking.STATUS_APPROVED,
                'stage': Booking.STAGE_COMPLETED,
                'chief': 'Chief Engineer, L&T Infrastructure',
                'desc': 'LEED rated campus design methodologies.',
            },

            # --- 5 PENDING REQUESTS (Different workflow stages) ---
            # 11. Pending HOD Verification (IT Department)
            {
                'id': f'BK-{year}-011',
                'user': users_dict['faculty.it@mcet.in'],
                'dept': depts_dict['IT'],
                'name': 'Cybersecurity Threats & Ethical Hacking Workshop',
                'type': 'Workshop',
                'participants': 110,
                'date': today + datetime.timedelta(days=6),
                'start': datetime.time(10, 0),
                'end': datetime.time(13, 0),
                'hall': halls_dict['SH-01'],
                'status': Booking.STATUS_SUBMITTED,
                'stage': Booking.STAGE_HOD,
                'chief': 'Mr. Arvind Swaminathan, Red Team Lead, Cognizant',
                'desc': 'Penetration testing demonstrations and defense measures.',
            },
            # 12. Pending HOD Verification (CSE Department)
            {
                'id': f'BK-{year}-012',
                'user': users_dict['faculty.cse@mcet.in'],
                'dept': depts_dict['CSE'],
                'name': 'Quantum Computing Fundamentals & Qiskit Coding',
                'type': 'Guest Lecture',
                'participants': 85,
                'date': today + datetime.timedelta(days=8),
                'start': datetime.time(14, 0),
                'end': datetime.time(16, 30),
                'hall': halls_dict['SH-02'],
                'status': Booking.STATUS_SUBMITTED,
                'stage': Booking.STAGE_HOD,
                'chief': 'IBM Quantum Research Ambassador',
                'desc': 'Superposition and entanglement algorithms simulation.',
            },
            # 13. Pending Coordinator Verification (HOD Approved)
            {
                'id': f'BK-{year}-013',
                'user': users_dict['faculty.it@mcet.in'],
                'dept': depts_dict['IT'],
                'name': '5-Day FDP on Modern Web Architectures & Microservices',
                'type': 'Faculty Development Programme',
                'participants': 60,
                'date': today + datetime.timedelta(days=9),
                'start': datetime.time(9, 30),
                'end': datetime.time(16, 30),
                'hall': halls_dict['SH-04'],
                'status': Booking.STATUS_HOD_APPROVED,
                'stage': Booking.STAGE_COORDINATOR,
                'chief': 'Senior Technical Architects from Zoho & Freshworks',
                'desc': 'Hands-on faculty skill upgradation programme.',
            },
            # 14. Pending Coordinator Verification
            {
                'id': f'BK-{year}-014',
                'user': users_dict['faculty.cse@mcet.in'],
                'dept': depts_dict['AIDS'],
                'name': 'Deep Learning for Medical Image Diagnostics',
                'type': 'Seminar',
                'participants': 100,
                'date': today + datetime.timedelta(days=10),
                'start': datetime.time(10, 0),
                'end': datetime.time(12, 30),
                'hall': halls_dict['SH-01'],
                'status': Booking.STATUS_HOD_APPROVED,
                'stage': Booking.STAGE_COORDINATOR,
                'chief': 'Dr. K. Sridhar, AIIMS Biomedical Research',
                'desc': 'MRI/CT scan segmentation with Vision Transformers.',
            },
            # 15. Pending Principal Approval (Coordinator Approved)
            {
                'id': f'BK-{year}-015',
                'user': users_dict['hod.it@mcet.in'],
                'dept': depts_dict['IT'],
                'name': 'Annual College Innovation & Startup Showcase (MCET Pitch)',
                'type': 'Cultural Event',
                'participants': 190,
                'date': today + datetime.timedelta(days=12),
                'start': datetime.time(9, 30),
                'end': datetime.time(16, 0),
                'hall': halls_dict['SH-01'],
                'status': Booking.STATUS_COORDINATOR_APPROVED,
                'stage': Booking.STAGE_PRINCIPAL,
                'chief': 'Angel Investors & Startup Ecosystem Mentors',
                'desc': 'Student entrepreneurs pitching to venture capitalists.',
            },

            # --- 3 REJECTED REQUESTS ---
            # 16. Rejected due to scheduling conflict / capacity
            {
                'id': f'BK-{year}-016',
                'user': users_dict['faculty.it@mcet.in'],
                'dept': depts_dict['IT'],
                'name': 'Orientation Session for Freshmen Batch',
                'type': 'Seminar',
                'participants': 250,
                'date': today + datetime.timedelta(days=4),
                'start': datetime.time(10, 0),
                'end': datetime.time(13, 0),
                'hall': halls_dict['SH-02'],
                'status': Booking.STATUS_REJECTED,
                'stage': Booking.STAGE_REJECTED,
                'chief': 'Dean Academics',
                'desc': 'Introduction to college ERP and credit system.',
                'reject_reason': 'Participant count (250) exceeds Seminar Hall 2 capacity (100). Please book College Auditorium or Seminar Hall 1.',
                'rejected_by': users_dict['coordinator@mcet.in'],
            },
            # 17. Rejected by HOD due to conflicting departmental internal exam
            {
                'id': f'BK-{year}-017',
                'user': users_dict['faculty.cse@mcet.in'],
                'dept': depts_dict['CSE'],
                'name': 'Student Club Hackathon Orientation',
                'type': 'Workshop',
                'participants': 70,
                'date': today + datetime.timedelta(days=7),
                'start': datetime.time(14, 0),
                'end': datetime.time(17, 0),
                'hall': halls_dict['SH-04'],
                'status': Booking.STATUS_REJECTED,
                'stage': Booking.STAGE_REJECTED,
                'chief': 'Alumni Hackathon Winner',
                'desc': 'Briefing session for 24-hour hackathon participants.',
                'reject_reason': 'Continuous Internal Assessment (CIA-2) is scheduled on this afternoon. Reschedule to next weekend.',
                'rejected_by': users_dict['hod.it@mcet.in'],
            },
            # 18. Rejected by Principal
            {
                'id': f'BK-{year}-018',
                'user': users_dict['faculty.it@mcet.in'],
                'dept': depts_dict['MS'],
                'name': 'External Commercial Agency Product Showcase',
                'type': 'Other',
                'participants': 50,
                'date': today + datetime.timedelta(days=14),
                'start': datetime.time(10, 0),
                'end': datetime.time(12, 0),
                'hall': halls_dict['CH-01'],
                'status': Booking.STATUS_REJECTED,
                'stage': Booking.STAGE_REJECTED,
                'chief': 'Agency Representative',
                'desc': 'Commercial software demo.',
                'reject_reason': 'Purely commercial promotional events are not permitted inside academic seminar halls without Management Trustee approval.',
                'rejected_by': users_dict['principal@mcet.in'],
            },

            # --- 2 CANCELLED REQUESTS ---
            # 19. Cancelled by requester because guest cancelled travel
            {
                'id': f'BK-{year}-019',
                'user': users_dict['faculty.it@mcet.in'],
                'dept': depts_dict['IT'],
                'name': 'International Webinar on Autonomous Robotic Vehicles',
                'type': 'Seminar',
                'participants': 90,
                'date': today + datetime.timedelta(days=11),
                'start': datetime.time(10, 0),
                'end': datetime.time(12, 30),
                'hall': halls_dict['SH-03'],
                'status': Booking.STATUS_CANCELLED,
                'stage': Booking.STAGE_CANCELLED,
                'chief': 'Dr. Hans Mueller, TU Munich Germany',
                'desc': 'ROS2 and LiDAR slam navigation.',
                'cancel_reason': 'Keynote speaker unable to travel due to flight cancellation. Will re-schedule next month.',
                'cancelled_by': users_dict['faculty.it@mcet.in'],
            },
            # 20. Cancelled by Coordinator due to emergency electrical rewiring
            {
                'id': f'BK-{year}-020',
                'user': users_dict['faculty.cse@mcet.in'],
                'dept': depts_dict['EEE'],
                'name': 'Renewable Energy Integration in Smart Grids',
                'type': 'Workshop',
                'participants': 60,
                'date': today + datetime.timedelta(days=15),
                'start': datetime.time(14, 0),
                'end': datetime.time(16, 30),
                'hall': halls_dict['SH-02'],
                'status': Booking.STATUS_CANCELLED,
                'stage': Booking.STAGE_CANCELLED,
                'chief': 'TNEB Superintending Engineer',
                'desc': 'Solar PV grid synchronizing inverter study.',
                'cancel_reason': 'Seminar Hall 2 scheduled for UPS battery bank replacement on this date. Event postponed.',
                'cancelled_by': users_dict['coordinator@mcet.in'],
            },
        ]

        count = 0
        for b_data in bookings_spec:
            booking = Booking(
                booking_id=b_data['id'],
                user=b_data['user'],
                department=b_data['dept'],
                event_name=b_data['name'],
                event_type=b_data['type'],
                expected_participants=b_data['participants'],
                event_date=b_data['date'],
                start_time=b_data['start'],
                end_time=b_data['end'],
                preferred_hall=b_data['hall'],
                allocated_hall=b_data['hall'],
                req_projector=True,
                req_audio=True,
                req_microphone=True,
                req_wifi=True,
                req_ac=True,
                chief_guest=b_data.get('chief', ''),
                event_description=b_data.get('desc', ''),
                status=b_data['status'],
                current_approval_stage=b_data['stage'],
                rejection_reason=b_data.get('reject_reason', ''),
                rejected_by=b_data.get('rejected_by'),
                cancellation_reason=b_data.get('cancel_reason', ''),
                cancelled_by=b_data.get('cancelled_by'),
                cancelled_at=timezone.now() if b_data.get('cancelled_by') else None
            )
            booking.save()
            count += 1

            # Seed realistic Approval History trail for each booking
            ApprovalHistory.objects.create(
                booking=booking,
                stage="Submission",
                action=ApprovalHistory.ACTION_SUBMITTED,
                user=b_data['user'],
                previous_status="DRAFT",
                new_status=Booking.STATUS_SUBMITTED,
                remarks="Initial submission by faculty coordinator."
            )

            if b_data['status'] in [Booking.STATUS_HOD_APPROVED, Booking.STATUS_COORDINATOR_APPROVED, Booking.STATUS_APPROVED]:
                ApprovalHistory.objects.create(
                    booking=booking,
                    stage="HOD Verification",
                    action=ApprovalHistory.ACTION_HOD_APPROVED,
                    user=users_dict['hod.it@mcet.in'],
                    previous_status=Booking.STATUS_SUBMITTED,
                    new_status=Booking.STATUS_HOD_APPROVED,
                    remarks="Department verified. Event aligns with academic calendar."
                )

            if b_data['status'] in [Booking.STATUS_COORDINATOR_APPROVED, Booking.STATUS_APPROVED]:
                ApprovalHistory.objects.create(
                    booking=booking,
                    stage="Coordinator Verification",
                    action=ApprovalHistory.ACTION_COORDINATOR_APPROVED,
                    user=users_dict['coordinator@mcet.in'],
                    previous_status=Booking.STATUS_HOD_APPROVED,
                    new_status=Booking.STATUS_COORDINATOR_APPROVED,
                    remarks="Hall availability and requested audiovisual facilities verified."
                )

            if b_data['status'] == Booking.STATUS_APPROVED:
                ApprovalHistory.objects.create(
                    booking=booking,
                    stage="Principal Final Approval",
                    action=ApprovalHistory.ACTION_PRINCIPAL_APPROVED,
                    user=users_dict['principal@mcet.in'],
                    previous_status=Booking.STATUS_COORDINATOR_APPROVED,
                    new_status=Booking.STATUS_APPROVED,
                    remarks="Approved. Best wishes for a successful event."
                )

            if b_data['status'] == Booking.STATUS_REJECTED:
                ApprovalHistory.objects.create(
                    booking=booking,
                    stage=b_data['stage'],
                    action=ApprovalHistory.ACTION_PRINCIPAL_REJECTED if b_data.get('rejected_by') == users_dict['principal@mcet.in'] else ApprovalHistory.ACTION_COORDINATOR_REJECTED,
                    user=b_data.get('rejected_by', users_dict['coordinator@mcet.in']),
                    previous_status=Booking.STATUS_SUBMITTED,
                    new_status=Booking.STATUS_REJECTED,
                    remarks=b_data.get('reject_reason', 'Rejected')
                )

            if b_data['status'] == Booking.STATUS_CANCELLED:
                ApprovalHistory.objects.create(
                    booking=booking,
                    stage="Cancellation",
                    action=ApprovalHistory.ACTION_CANCELLED,
                    user=b_data.get('cancelled_by', b_data['user']),
                    previous_status=Booking.STATUS_APPROVED,
                    new_status=Booking.STATUS_CANCELLED,
                    remarks=b_data.get('cancel_reason', 'Cancelled')
                )

            # Notifications for user
            Notification.objects.create(
                recipient=b_data['user'],
                title=f"Booking Update – {booking.booking_id}",
                message=f"Event '{booking.event_name}' status is {booking.get_status_display()}.",
                booking=booking,
                notification_type='SYSTEM',
                is_read=False if b_data['status'] in [Booking.STATUS_SUBMITTED, Booking.STATUS_APPROVED] else True
            )

        self.stdout.write(self.style.SUCCESS(f"Created {count} realistic Bookings with complete workflow history and notifications!"))
        self.stdout.write(self.style.SUCCESS("All seed data generated successfully."))
