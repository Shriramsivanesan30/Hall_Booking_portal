# 🏛️ MCET Seminar Hall Booking System

A College ERP module for **Dr. Mahalingam College of Engineering and Technology (MCET), Pollachi** that lets faculty book seminar halls online, with automatic clash detection and a three-level approval workflow.

🌐 **Live:** https://booking.dexoshpuse.com

| | |
| :--- | :--- |
| **Backend** | Python Django (modular apps) |
| **Frontend** | HTML5, CSS3, Vanilla JS, Outlook-style calendar |
| **Database** | MySQL (production) / SQLite (development) |
| **Login** | Microsoft Entra ID (Outlook) OAuth 2.0 + demo login for dev |
| **Hosting** | MilesWeb cPanel, Python App (Phusion Passenger) |
| **Theme** | Navy `#123B72` · Royal Blue `#1D5FA7` · Light Blue `#EAF3FF` |

---

## 📑 Table of Contents

1. [How it works (big picture)](#1-how-it-works-big-picture)
2. [Project structure](#2-project-structure)
3. [User roles](#3-user-roles)
4. [Login flow](#4-login-flow)
5. [Booking flow and availability engine](#5-booking-flow-and-availability-engine)
6. [Approval workflow](#6-approval-workflow)
7. [Database model](#7-database-model)
8. [Local setup](#8-local-setup)
9. [Deployment on MilesWeb cPanel](#9-deployment-on-milesweb-cpanel)

---

## 1. How it works (big picture)

```mermaid
flowchart LR
    U["👤 User<br/>Faculty / HOD / Principal / Admin"] -->|Microsoft Login| A["🔐 accounts"]
    A --> D["📊 core<br/>Dashboard"]
    D --> B["📅 bookings<br/>Availability engine + Calendar"]
    B --> H["🏫 halls<br/>Hall master"]
    B --> AP["✅ approvals<br/>HOD → Coordinator → Principal"]
    AP --> N["🔔 notifications<br/>In-app + Email"]
    AP --> AU["🧾 audit<br/>Immutable log"]
    D --> R["📈 reports<br/>Analytics + Excel"]
    H --> DP["🏢 departments"]

    style U fill:#EAF3FF,stroke:#123B72,color:#123B72
    style B fill:#1D5FA7,stroke:#123B72,color:#fff
    style AP fill:#1D5FA7,stroke:#123B72,color:#fff
```

**In one line:** a user logs in with their college Outlook account, picks a hall and time, the system checks for clashes, and the request travels through HOD, Hall Coordinator and Principal before it is confirmed on the calendar.

---

## 2. Project structure

```mermaid
flowchart TD
    ROOT["📁 hall_booking/"] --> CFG["config/<br/>settings, urls, wsgi"]
    ROOT --> APPS["apps/"]
    ROOT --> TPL["templates/"]
    ROOT --> STA["static/<br/>css, js, images"]
    ROOT --> MED["media/<br/>uploaded documents"]
    ROOT --> SCR["scripts/<br/>seed_data.py"]
    ROOT --> FILES["manage.py · passenger_wsgi.py<br/>requirements.txt · .env"]

    APPS --> a1["accounts"]
    APPS --> a2["departments"]
    APPS --> a3["halls"]
    APPS --> a4["bookings"]
    APPS --> a5["approvals"]
    APPS --> a6["notifications"]
    APPS --> a7["reports"]
    APPS --> a8["audit"]
    APPS --> a9["core"]
```

| App | What it does |
| :--- | :--- |
| `accounts` | User profiles, Microsoft OAuth, role-based access, demo login |
| `departments` | Department master data |
| `halls` | Seminar hall master, capacity, facilities, maintenance |
| `bookings` | Availability engine, reservations, Outlook-style calendar |
| `approvals` | Multi-level approval workflow |
| `notifications` | In-app notifications and email alerts |
| `reports` | Analytics dashboard and Excel (.xlsx) export |
| `audit` | Immutable audit trail |
| `core` | System settings, context processors, dashboard |

<details>
<summary>📂 Full folder tree</summary>

```
hall_booking/
├── manage.py
├── passenger_wsgi.py          # MilesWeb Passenger entry point
├── requirements.txt
├── .env.example
├── config/                    # settings, urls, wsgi
├── apps/
│   ├── accounts/  departments/  halls/  bookings/
│   ├── approvals/ notifications/ reports/ audit/ core/
├── templates/                 # base, authentication, dashboard, bookings,
│                              # calendar, halls, departments, accounts,
│                              # reports, notifications, audit, settings
├── static/                    # css, js, images
├── media/                     # uploaded schedules & approval docs
└── scripts/seed_data.py
```
</details>

---

## 3. User roles

```mermaid
flowchart TB
    ADMIN["🛡️ Administrator<br/>Full control, can expedite any step"]
    PRINCIPAL["🎓 Principal<br/>Final sanction"]
    COORD["🏫 Hall Coordinator<br/>Reviews facilities, manages halls"]
    HOD["👨‍🏫 HOD<br/>Approves own department"]
    FAC["🧑‍💼 Faculty / Staff<br/>Creates and submits bookings"]
    STU["🎒 Student<br/>View availability only"]

    ADMIN --> PRINCIPAL --> COORD --> HOD --> FAC --> STU

    style ADMIN fill:#123B72,color:#fff
    style PRINCIPAL fill:#1D5FA7,color:#fff
    style COORD fill:#1D5FA7,color:#fff
    style HOD fill:#EAF3FF,stroke:#1D5FA7,color:#123B72
    style FAC fill:#EAF3FF,stroke:#1D5FA7,color:#123B72
    style STU fill:#fff,stroke:#1D5FA7,color:#123B72
```

### Permission matrix

| Role | View availability | Create bookings | HOD approval | Coordinator review | Principal approval | Hall master | Audit logs and settings |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Student** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Faculty / Staff** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **HOD** | ✅ | ✅ | ✅ own dept | ❌ | ❌ | ❌ | ❌ |
| **Hall Coordinator** | ✅ | ✅ | ❌ | ✅ all halls | ❌ | ✅ full | ❌ |
| **Principal** | ✅ | ✅ | ❌ | ❌ | ✅ final | 👁️ view | 👁️ view |
| **Administrator** | ✅ | ✅ | ⚡ expedite | ⚡ expedite | ⚡ expedite | ✅ | ✅ full |

---

## 4. Login flow

```mermaid
sequenceDiagram
    actor User
    participant App as Django App
    participant MS as Microsoft Entra ID

    User->>App: Open booking.dexoshpuse.com
    App->>User: Show login page
    User->>App: Click "Sign in with Microsoft"
    App->>MS: Redirect to Microsoft login
    MS->>User: Ask for college credentials
    User->>MS: Enter mcet.in / drmcet.ac.in account
    MS->>App: Callback with auth code (/auth/microsoft/callback/)
    App->>MS: Exchange code for token
    MS-->>App: User profile (email, name)
    App->>App: Check email domain is allowed
    App->>App: Create or update user + assign role
    App->>User: Redirect to Dashboard
```

> 🧪 **Demo mode:** when `ENABLE_DEMO_LOGIN=True` (development only), the login page shows one-click role accounts. **Always set it to `False` in production.**

---

## 5. Booking flow and availability engine

Every booking request goes through these checks **before** it is saved.

```mermaid
flowchart TD
    START(["📝 User fills booking form"]) --> C1{"Date in the past?"}
    C1 -- Yes --> X1["❌ Reject: past date"]
    C1 -- No --> C2{"Start time before end time?"}
    C2 -- No --> X2["❌ Reject: invalid time order"]
    C2 -- Yes --> C3{"Participants within hall capacity?"}
    C3 -- No --> X3["❌ Reject: over capacity"]
    C3 -- Yes --> C4{"Hall under maintenance?"}
    C4 -- Yes --> X4["❌ Reject: hall unavailable"]
    C4 -- No --> C5{"Time overlaps another booking?"}
    C5 -- Yes --> SUG["⚠️ Show conflicting event<br/>+ alternative halls<br/>+ free time slots"]
    C5 -- No --> LOCK["🔒 Save inside transaction.atomic<br/>with select_for_update"]
    LOCK --> OK(["✅ Request created → goes to approval"])

    style OK fill:#1D5FA7,color:#fff
    style SUG fill:#EAF3FF,stroke:#1D5FA7,color:#123B72
```

**Clash rule:**

```
new.start_time < existing.end_time  AND  new.end_time > existing.start_time
```

**Concurrency protection:** two people booking the same slot at the same moment cannot both succeed, because the database row is locked during the save (`select_for_update()`).

---

## 6. Approval workflow

### Step by step

```mermaid
flowchart TD
    F["🧑‍💼 Faculty submits request"] --> E{"Availability engine<br/>passes?"}
    E -- No --> F
    E -- Yes --> H["👨‍🏫 HOD verification<br/>Academic schedule check"]
    H --> CO["🏫 Hall Coordinator approval<br/>Facilities, AV technician, maintenance"]
    CO --> P["🎓 Principal approval<br/>Final sanction"]
    P --> OK["✅ Booking confirmed and locked<br/>Calendar updated · Emails sent"]

    H -. Reject + reason .-> REJ["❌ Rejected"]
    CO -. Reject + reason .-> REJ
    P -. Reject + reason .-> REJ
    H -. Request modification .-> F
    CO -. Request modification .-> F
    P -. Request modification .-> F

    style OK fill:#1D5FA7,color:#fff
    style REJ fill:#fff,stroke:#c0392b,color:#c0392b
```

### Booking status lifecycle

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Submitted: Faculty submits
    Submitted --> HODReview: Availability check passed
    HODReview --> CoordinatorReview: HOD verifies
    CoordinatorReview --> PrincipalReview: Coordinator approves
    PrincipalReview --> Confirmed: Principal sanctions
    HODReview --> Draft: Modification requested
    CoordinatorReview --> Draft: Modification requested
    PrincipalReview --> Draft: Modification requested
    HODReview --> Rejected: Reason required
    CoordinatorReview --> Rejected: Reason required
    PrincipalReview --> Rejected: Reason required
    Confirmed --> [*]
    Rejected --> [*]
```

**Rules**
- A rejection **must** include a written reason, which is stored in the immutable audit trail.
- "Request Modification" sends the booking back to **Draft** so the faculty can edit and resubmit.
- Administrators can expedite any step.

### Who gets notified

```mermaid
sequenceDiagram
    actor Faculty
    participant HOD
    participant Coord as Hall Coordinator
    participant Principal
    participant Sys as System (Notifications + Audit)

    Faculty->>Sys: Submit booking
    Sys->>HOD: 🔔 Pending verification
    HOD->>Sys: Verify
    Sys->>Coord: 🔔 Pending review
    Coord->>Sys: Approve
    Sys->>Principal: 🔔 Pending final approval
    Principal->>Sys: Sanction
    Sys->>Faculty: 📧 Booking confirmed
    Sys->>HOD: 📧 Department copy
    Note over Sys: Every action is written to the audit log
```

---

## 7. Database model

```mermaid
erDiagram
    DEPARTMENT ||--o{ USER : "has"
    DEPARTMENT ||--o{ BOOKING : "organises"
    USER ||--o{ BOOKING : "creates"
    HALL ||--o{ BOOKING : "is reserved in"
    HALL ||--o{ MAINTENANCE : "has downtime"
    BOOKING ||--o{ APPROVAL : "goes through"
    USER ||--o{ APPROVAL : "acts on"
    USER ||--o{ NOTIFICATION : "receives"
    BOOKING ||--o{ AUDIT_LOG : "recorded in"

    USER {
        int id
        string email
        string role
    }
    DEPARTMENT {
        int id
        string name
    }
    HALL {
        int id
        string name
        int capacity
        string facilities
    }
    BOOKING {
        int id
        date event_date
        time start_time
        time end_time
        int participants
        string status
    }
    APPROVAL {
        int id
        string level
        string decision
        string reason
    }
    MAINTENANCE {
        int id
        datetime from_time
        datetime to_time
    }
    NOTIFICATION {
        int id
        string message
        bool is_read
    }
    AUDIT_LOG {
        int id
        string action
        datetime timestamp
    }
```

> ℹ️ Simplified view. Field names are illustrative; see each app's `models.py` for the exact schema.

---

## 8. Local setup

```mermaid
flowchart LR
    A["1️⃣ pip install -r requirements.txt"] --> B["2️⃣ python manage.py migrate"]
    B --> C["3️⃣ python manage.py seed_data"]
    C --> D["4️⃣ python manage.py runserver"]
    D --> E["🌐 http://127.0.0.1:8000"]
```

```powershell
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data      # 10 departments, 5 halls, 7 sample users, 20 bookings
python manage.py runserver 127.0.0.1:8000
```

Open http://127.0.0.1:8000 and pick a demo account.

### Demo accounts (development only)

Set `ENABLE_DEMO_LOGIN=True` in `.env`. Passwords are defined in the seed data, not in this README.

| Role | Email |
| :--- | :--- |
| System Administrator | `admin@mcet.in` |
| Principal | `principal@mcet.in` |
| Hall Coordinator | `coordinator@mcet.in` |
| HOD (IT) | `hod.it@mcet.in` |
| Faculty Coordinator | `faculty.it@mcet.in` |
| Student Representative | `727624P80@mcet.in` |

---

## 9. Deployment on MilesWeb cPanel

```mermaid
flowchart TD
    S1["1. Create subdomain<br/>booking.dexoshpuse.com"] --> S2["2. Create MySQL DB + user<br/>MySQL Database Wizard"]
    S2 --> S3["3. Setup Python App<br/>startup file: passenger_wsgi.py<br/>entry point: application"]
    S3 --> S4["4. Upload project files<br/>keep cPanel virtualenv"]
    S4 --> S5["5. Create .env<br/>production values"]
    S5 --> S6["6. Activate virtualenv<br/>pip install -r requirements.txt"]
    S6 --> S7["7. migrate + collectstatic<br/>(optional seed_data)"]
    S7 --> S8["8. createsuperuser"]
    S8 --> S9["9. Restart app in cPanel"]
    S9 --> LIVE(["🚀 Live"])

    style LIVE fill:#1D5FA7,color:#fff
```

### Microsoft Entra ID setup

1. Open the [Microsoft Entra Admin Center](https://entra.microsoft.com/) and register an application.
2. Add a **Web** platform with redirect URI `https://booking.dexoshpuse.com/auth/microsoft/callback/`.
3. Create a client secret, then copy the Client ID and Tenant ID.

### Production `.env`

```ini
SECRET_KEY=generate-a-strong-random-50-character-secret-key
DEBUG=False
ALLOWED_HOSTS=booking.dexoshpuse.com,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://booking.dexoshpuse.com

# Database
DB_ENGINE=mysql
DB_NAME=username_mcethall
DB_USER=username_mcetusr
DB_PASSWORD=your_secure_mysql_password
DB_HOST=localhost
DB_PORT=3306

# Microsoft Entra ID
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret
MICROSOFT_TENANT_ID=common
MICROSOFT_REDIRECT_URI=https://booking.dexoshpuse.com/auth/microsoft/callback/
ALLOWED_EMAIL_DOMAINS=mcet.in,drmcet.ac.in

# Security
ENABLE_DEMO_LOGIN=False

# Email (SMTP)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=mail.booking.dexoshpuse.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=notifications@booking.dexoshpuse.com
EMAIL_HOST_PASSWORD=your-email-account-password
DEFAULT_FROM_EMAIL=MCET College ERP <notifications@booking.dexoshpuse.com>
```

### Commands (virtualenv active)

```bash
cd /home/username/booking.dexoshpuse.com
pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed_data          # optional
python manage.py createsuperuser    # if not seeded
```

Then click **Restart** in cPanel → **Setup Python App**.

---

<p align="center">Built for Dr. Mahalingam College of Engineering and Technology, Pollachi</p>
