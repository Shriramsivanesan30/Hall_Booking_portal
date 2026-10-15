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
