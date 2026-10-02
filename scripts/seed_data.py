import os
import sys

# Standalone seed data script
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.core.management import call_command

if __name__ == '__main__':
    print("Running MCET Seminar Hall Booking System Data Seeder...")
    call_command('seed_data')
    print("Completed successfully!")
