# MCET College ERP – Seminar Hall Booking System

**Application Name:** MCET Seminar Hall Booking System  
**Institution:** Dr. Mahalingam College of Engineering and Technology (MCET), Pollachi, Tamil Nadu  
**Target Domain:** [https://booking.dexoshpuse.com](https://booking.dexoshpuse.com)  
**Theme:** Navy Blue (`#123B72`), Royal Blue (`#1D5FA7`), Light Blue (`#EAF3FF`), Clean Modern ERP  
**Backend:** Python Django (Modular App Architecture)  
**Frontend:** HTML5, CSS3 Vanilla Design System, Vanilla JavaScript, Lucide-style SVG Icons, Microsoft Outlook-inspired Calendar  
**Database:** MySQL (Production) / SQLite (Dev fallback)  
**Authentication:** Microsoft Outlook / Microsoft Entra ID OAuth 2.0 + Local Demo Login Mode  
**Deployment Platform:** MilesWeb cPanel Python Application / Phusion Passenger (`passenger_wsgi.py`)  

---

## 1. Project Architecture

The application is structured into specialized, decoupled Django apps:

```
hall_booking/
├── manage.py                     # Django administrative utility
├── passenger_wsgi.py             # MilesWeb Passenger entry point
├── requirements.txt              # Production Python package manifest
├── .env.example                  # Environment configuration template
├── .env                          # Local environment variables
│
├── config/                       # Project configuration
│   ├── __init__.py               # PyMySQL installation hook
│   ├── settings.py               # Production & development settings
│   ├── urls.py                   # Master routing table
│   └── wsgi.py                   # WSGI application callable
│
├── apps/                         # Modular applications
│   ├── accounts/                 # User profiles, Microsoft OAuth, RBAC, Demo login
│   ├── departments/              # Department master & affiliations
│   ├── halls/                    # Seminar Hall master, capacities & facilities
│   ├── bookings/                 # Smart availability engine, reservations, calendar
│   ├── approvals/                # Multi-level approval workflow engine
│   ├── notifications/            # In-app notifications & institutional email alerts
│   ├── reports/                  # Analytics dashboard & Excel (.xlsx) export
│   ├── audit/                    # Immutable audit logging
│   └── core/                     # System configs, global context processors, dashboard
│
├── templates/                    # Modular Django templates
│   ├── base.html                 # Institutional sidebar & topbar layout
│   ├── authentication/           # Microsoft Outlook login & demo selector
│   ├── dashboard/                # Live statistics, schedule & hall statuses
│   ├── bookings/                 # Multi-section booking form, details, edit, queues
│   ├── calendar/                 # Outlook-style Day/Week/Month/Agenda calendar
│   ├── halls/                    # Availability matrix, hall master, maintenance
│   ├── departments/              # Department list & management forms
│   ├── accounts/                 # User directory, profile & role assignments
│   ├── reports/                  # Analytics & Excel export interface
│   ├── notifications/            # Notification center & read status
│   ├── audit/                    # Immutable audit trail table
│   └── settings/                 # Administrative booking policy controls
│
├── static/
│   ├── css/                      # Custom institutional design system & calendar CSS
│   ├── js/                       # Interactivity, smart booking form AJAX, calendar engine
│   └── images/                   # MCET institutional emblem and logo SVG
│
├── media/                        # User-uploaded programme schedules & approval docs
└── scripts/
    └── seed_data.py              # Standalone data seeding runner
```

---

## 2. User Roles & Permission Matrix

The system enforces strict role-based authorization at the view and service layer:

| Role | Hall Availability | Create Bookings | HOD Approval | Coordinator Review | Principal Approval | Hall Master | Audit Logs & Settings |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Student** | Yes (View) | No | No | No | No | No | No |
| **Faculty / Staff** | Yes | Yes (Draft/Submit) | No | No | No | No | No |
| **HOD** | Yes | Yes | **Yes (Own Dept)** | No | No | No | No |
| **Hall Coordinator**| Yes | Yes | No | **Yes (All Halls)** | No | **Yes (Full)** | No |
| **Principal** | Yes | Yes | No | No | **Yes (Final Sanction)** | View | View |
| **Administrator** | Yes | Yes | Expedite | Expedite | Expedite | **Yes** | **Yes (Full)** |

---

## 3. Microsoft Outlook & Demo Authentication

### Microsoft Entra ID OAuth 2.0 Setup
1. Register an application in the [Microsoft Entra Admin Center](https://entra.microsoft.com/).
2. Add a Web platform with the Redirect URI:  
   `https://booking.dexoshpuse.com/auth/microsoft/callback/`
3. Generate a Client Secret and copy the Application (Client) ID and Directory (Tenant) ID.
4. Set the following in your `.env` file:
   ```ini
   MICROSOFT_CLIENT_ID=your-client-id
   MICROSOFT_CLIENT_SECRET=your-client-secret
   MICROSOFT_TENANT_ID=your-tenant-id-or-common
   MICROSOFT_REDIRECT_URI=https://booking.dexoshpuse.com/auth/microsoft/callback/
   ALLOWED_EMAIL_DOMAINS=mcet.in,drmcet.ac.in
   ```

### Local Demo Login Mode (Development Only)
When `ENABLE_DEMO_LOGIN=True` in `.env`, the login page renders a quick one-click role selector with realistic pre-seeded accounts:
- **System Administrator:** `admin@mcet.in` (password: `mcet@admin2026`)
- **Principal:** `principal@mcet.in` (password: `mcet@principal2026`)
- **Seminar Hall Coordinator:** `coordinator@mcet.in` (password: `mcet@coord2026`)
- **HOD (Information Technology):** `hod.it@mcet.in` (password: `mcet@hod2026`)
- **Faculty Coordinator:** `faculty.it@mcet.in` (password: `mcet@faculty2026`)
- **Student Representative:** `727624P80@mcet.in` (password: `mcet@student2026`)

*Note: For production on MilesWeb, set `ENABLE_DEMO_LOGIN=False`.*

---

## 4. Smart Availability Validation Engine

Before any booking request can be saved or confirmed, the engine enforces:
1. **Date Validation:** Booking dates in the past are strictly rejected.
2. **Chronological Time Ordering:** `start_time` must be earlier than `end_time`.
3. **Capacity Constraints:** Participant count cannot exceed the hall's maximum capacity.
4. **Maintenance Checks:** Halls currently under maintenance or with scheduled downtime are blocked.
5. **Conflict Detection:** Strict overlap checking (`start_time < existing.end_time AND end_time > existing.start_time`).
6. **Smart Suggestions:**
   - In case of a conflict, the system displays the conflicting event details.
   - It automatically lists **alternative available halls** with sufficient capacity.
   - It suggests **open available time slots** on the same day for that hall.
7. **Concurrency Protection:** Database transactions use `transaction.atomic()` and `select_for_update()` to prevent race conditions during simultaneous booking attempts.

---

## 5. Multi-Level Approval Workflow

```
Faculty / Staff Submits Request
             │
             ▼
[Availability Engine Check]
             │
             ▼
    HOD Verification
(Department Head reviews & verifies academic schedule)
             │
             ▼
Seminar Hall Coordinator Approval
(Checks facilities, AV technician allocation, hall maintenance)
             │
             ▼
Principal / Authorized Approval
(Final institutional sanction)
             │
             ▼
Booking Confirmed & Locked
(Calendar updated, email alerts dispatched to faculty & department)
```
- Rejections require a mandatory documented reason recorded in the immutable audit trail.
- Changes can be requested via "Request Modification", returning the request to draft state.

---

## 6. Local Quick-Start Guide

### Step 1: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 2: Run Database Migrations
```powershell
python manage.py migrate
```

### Step 3: Seed Realistic Institutional Data
```powershell
python manage.py seed_data
```
*This populates 10 departments, 5 seminar halls with equipment, 7 sample user roles, and 20 realistic bookings across all workflow stages.*

### Step 4: Run the Development Server
```powershell
python manage.py runserver 127.0.0.1:8000
```
Visit [http://127.0.0.1:8000](http://127.0.0.1:8000) and select any demo account to test.

---

## 7. MilesWeb cPanel Deployment Guide

### Target Domain: `https://booking.dexoshpuse.com`

### Step 1: Create the Subdomain / Domain in cPanel
1. Log in to your MilesWeb cPanel.
2. Go to **Domains** or **Subdomains**.
3. Create the subdomain `booking.dexoshpuse.com`.
4. Note the Document Root (e.g. `/home/username/booking.dexoshpuse.com` or `/home/username/public_html/booking`).

### Step 2: Create MySQL Database & User
1. In cPanel, open **MySQL Database Wizard**.
2. Create database: `username_mcethall`.
3. Create database user: `username_mcetusr` with a strong password.
4. Grant **ALL PRIVILEGES** to the user for this database.

### Step 3: Set up Python Application in cPanel
1. In cPanel, navigate to **Software** &rarr; **Setup Python App**.
2. Click **Create Application**.
3. Configure the following:
   - **Python version:** Select `3.10`, `3.11`, or `3.12`.
   - **Application root:** `booking.dexoshpuse.com` (relative to your cPanel home directory).
   - **Application URL:** `booking.dexoshpuse.com`.
   - **Application startup file:** `passenger_wsgi.py`.
   - **Application Entry point:** `application`.
4. Click **Create**.

### Step 4: Upload Project Files
Upload the project files to the application root folder (e.g. via cPanel File Manager, Git, or SFTP):
- Do **not** overwrite the virtual environment created by cPanel.
- Ensure `manage.py`, `passenger_wsgi.py`, `requirements.txt`, `config/`, `apps/`, `templates/`, and `static/` are uploaded.

### Step 5: Configure Production Environment Variables (`.env`)
Create or edit `.env` in the project root:
```ini
SECRET_KEY=generate-a-strong-random-50-character-secret-key!
DEBUG=False
ALLOWED_HOSTS=booking.dexoshpuse.com,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://booking.dexoshpuse.com

# MySQL Database Configuration
DB_ENGINE=mysql
DB_NAME=username_mcethall
DB_USER=username_mcetusr
DB_PASSWORD=your_secure_mysql_password
DB_HOST=localhost
DB_PORT=3306

# Microsoft Entra ID Authentication
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret
MICROSOFT_TENANT_ID=common
MICROSOFT_REDIRECT_URI=https://booking.dexoshpuse.com/auth/microsoft/callback/
ALLOWED_EMAIL_DOMAINS=mcet.in,drmcet.ac.in

# Production Security Mode
ENABLE_DEMO_LOGIN=False

# SMTP Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=mail.booking.dexoshpuse.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=notifications@booking.dexoshpuse.com
EMAIL_HOST_PASSWORD=your-email-account-password
DEFAULT_FROM_EMAIL=MCET College ERP <notifications@booking.dexoshpuse.com>
```

### Step 6: Install Requirements inside cPanel Python App
1. In cPanel **Setup Python App**, copy the virtualenv activation command shown at the top of the page (e.g. `source /home/username/virtualenv/booking.dexoshpuse.com/3.11/bin/activate`).
2. Open cPanel **Terminal** or SSH, paste the activation command, and run:
   ```bash
   cd /home/username/booking.dexoshpuse.com
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

### Step 7: Run Migrations and Collect Static Files
In the terminal with virtualenv active:
```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed_data # (Optional: seeds initial departments and halls)
```

### Step 8: Create Admin Superuser (if not seeded)
```bash
python manage.py createsuperuser
```

### Step 9: Restart the Application
In cPanel **Setup Python App**, click **Restart** on your application.

Your MCET Seminar Hall Booking System is now live at:  
👉 **https://booking.dexoshpuse.com**
#   H a l l _ B o o k i n g _ p o r t a l  
 