import os
import sys

# MilesWeb cPanel Passenger WSGI Entry Point
# Set up paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# If virtualenv python is used, set sys.executable if required by cPanel
# Example: sys.executable = '/home/username/virtualenv/booking.dexoshpuse.com/3.11/bin/python'

# Pure Python MySQL driver fallback for cPanel MySQL connection
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass

# Set environment variable for Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Import Django WSGI handler
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
