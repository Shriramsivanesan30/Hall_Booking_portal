import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.test import Client
from django.contrib.auth.models import User

c = Client()
user = User.objects.get(username='admin@mcet.in')
c.force_login(user)

endpoints = [
    ('/', 200),
    ('/bookings/new/', 200),
    ('/bookings/my-bookings/', 200),
    ('/bookings/approved/', 200),
    ('/bookings/calendar/', 200),
    ('/bookings/availability/', 200),
    ('/approvals/pending/', 200),
    ('/halls/', 200),
    ('/departments/', 200),
    ('/auth/users/', 200),
    ('/reports/', 200),
    ('/reports/export/excel/', 200),
    ('/notifications/', 200),
    ('/audit/', 200),
    ('/settings/', 200),
]

all_passed = True
for url, expected in endpoints:
    resp = c.get(url)
    status = resp.status_code
    if status == expected:
        print(f"[OK] {url} -> {status}")
    else:
        print(f"[FAIL] {url} -> {status} (expected {expected})")
        all_passed = False

if all_passed:
    print("\nALL 15 ENDPOINTS VERIFIED AND RETURNING HTTP 200 OK!")
