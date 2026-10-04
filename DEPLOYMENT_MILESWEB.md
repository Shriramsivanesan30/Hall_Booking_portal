# MilesWeb Deployment Guide for bookings.dexoshouse.com

This guide provides the complete, step-by-step instructions to deploy the **MCET Seminar Hall Booking System** onto **MilesWeb cPanel** hosting using CloudLinux **Setup Python App** (Phusion Passenger) and MySQL.

---

## 1. Prerequisites in MilesWeb cPanel

- Domain / Subdomain: `bookings.dexoshouse.com`
- Python version: `3.10` or `3.11` (Available in cPanel "Setup Python App")
- MySQL Database created via cPanel "MySQL Databases" wizard
- SSL Certificate installed via cPanel "Let's Encrypt SSL" or AutoSSL

---

## 2. Step-by-Step Deployment Instructions

### Step 1: Create the Subdomain
1. Log in to your **MilesWeb cPanel**.
2. Navigate to **Domains** > **Subdomains** (or **Domains**).
3. Create subdomain:
   - **Subdomain:** `bookings`
   - **Domain:** `dexoshouse.com`
   - **Document Root:** `public_html/bookings` (or `/home/<cpanel_user>/bookings.dexoshouse.com`)
4. Ensure an SSL certificate is active for `bookings.dexoshouse.com`.

---

### Step 2: Create MySQL Database & User
1. In cPanel, click **MySQL Database Wizard**.
2. Create a database, e.g. `dexos_mcet_booking`.
3. Create a user, e.g. `dexos_mcet_user`, with a strong password.
4. Grant **ALL PRIVILEGES** to this user for the database.
5. Note the full database name, username, and password.

---

### Step 3: Configure "Setup Python App" in cPanel
1. In cPanel, open **Setup Python App** (under Software section).
2. Click **Create Application**:
   - **Python version:** Select `3.11` (or `3.10`).
   - **Application root:** `bookings.dexoshouse.com` (or folder where code will reside).
   - **Application URL:** Select `bookings.dexoshouse.com`.
   - **Application startup file:** `passenger_wsgi.py`.
   - **Application Entry point:** `application`.
3. Click **Create**.
4. Note the virtual environment activation command shown at the top of the page (e.g., `source /home/<user>/virtualenv/bookings.dexoshouse.com/3.11/bin/activate`).

---

### Step 4: Upload Project Code
1. Upload all files from this project directory into the **Application root** folder on MilesWeb using cPanel File Manager or FTP/SSH.
2. Confirm the directory structure looks like:
   ```
   bookings.dexoshouse.com/
   ├── apps/
   ├── config/
   ├── static/
   ├── staticfiles/
   ├── templates/
   ├── scripts/
   ├── manage.py
   ├── passenger_wsgi.py
   ├── requirements.txt
   ├── .htaccess
   └── .env
   ```

---

### Step 5: Configure the Production `.env` File
In the project root folder on MilesWeb, create or edit `.env`:

```ini
# Production Secret Key (replace with your secure 50+ character string)
SECRET_KEY=mcet-prod-vault-2026-bookings-dexoshouse-secure-key-9981

# Disable debug in production
DEBUG=False

# Hostnames allowed
ALLOWED_HOSTS=bookings.dexoshouse.com,www.bookings.dexoshouse.com

# CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS=https://bookings.dexoshouse.com

# Database Connection (MilesWeb MySQL)
DB_ENGINE=mysql
DB_NAME=dexos_mcet_booking
DB_USER=dexos_mcet_user
DB_PASSWORD=your_actual_db_password
DB_HOST=localhost
DB_PORT=3306

# Microsoft Entra ID / Outlook Credentials
MICROSOFT_CLIENT_ID=your-azure-app-client-id
MICROSOFT_CLIENT_SECRET=your-azure-client-secret-value
MICROSOFT_TENANT_ID=common
MICROSOFT_REDIRECT_URI=https://bookings.dexoshouse.com/auth/microsoft/callback/
ALLOWED_EMAIL_DOMAINS=mcet.in,drmcet.ac.in

# Disable demo login for production
ENABLE_DEMO_LOGIN=False

# Production Email Delivery (cPanel Webmail / SMTP)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=mail.dexoshouse.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=notifications@dexoshouse.com
EMAIL_HOST_PASSWORD=your_webmail_password
DEFAULT_FROM_EMAIL=MCET College ERP <notifications@dexoshouse.com>
```

---

### Step 6: Install Requirements & Run Database Migrations
Open cPanel **Terminal** (or SSH), activate the Python virtual environment and run:

```bash
# 1. Activate your virtual environment (use the command from Setup Python App page)
source /home/<cpanel_user>/virtualenv/bookings.dexoshouse.com/3.11/bin/activate

# 2. Navigate to your project folder
cd /home/<cpanel_user>/bookings.dexoshouse.com

# 3. Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Apply database migrations to MySQL
python manage.py migrate

# 5. Populate initial institutional data (Halls, Departments, Roles, Demo Accounts)
python scripts/seed_data.py

# 6. Collect static assets (processed via WhiteNoise)
python manage.py collectstatic --noinput
```

---

### Step 7: Restart the Python Application
1. Go back to cPanel > **Setup Python App**.
2. Click the **Restart** button next to `bookings.dexoshouse.com`.
   *(Or via terminal: `touch tmp/restart.txt` inside the application root).*
3. Open your browser and visit: **`https://bookings.dexoshouse.com`**

---

### Step 8: Microsoft Entra ID (Azure) App Registration Update
In [Microsoft Entra Admin Center](https://entra.microsoft.com/):
1. Navigate to **App registrations** > your MCET application.
2. Under **Authentication** > **Web** > **Redirect URIs**, add:
   `https://bookings.dexoshouse.com/auth/microsoft/callback/`
3. Save changes.
