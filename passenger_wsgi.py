import os
import sys
import traceback

# 1. Ensure project root is at the head of sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 2. PyMySQL hook for cPanel MySQL database
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except Exception:
    pass

# 3. Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 4. Initialize Django WSGI application with self-diagnostic fallback
try:
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
except Exception as exc:
    error_trace = traceback.format_exc()

    # Log to a local file for cPanel File Manager inspection
    try:
        log_file = os.path.join(PROJECT_ROOT, 'passenger_error.log')
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n--- Startup Error ({sys.version}) ---\n{error_trace}\n")
    except Exception:
        pass

    # Provide a clear, actionable diagnostic page instead of a generic 500 error
    def application(environ, start_response):
        status = '500 Internal Server Error'
        python_info = f"Python {sys.version.split()[0]} ({sys.executable})"
        sys_path_info = "\n".join(sys.path[:6])

        html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Application Startup Diagnostic</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0F172A; color: #F8FAFC; padding: 40px 20px; }}
    .card {{ max-width: 900px; margin: 0 auto; background: #1E293B; border-radius: 12px; padding: 28px; border: 1px solid #334155; }}
    h1 {{ color: #F87171; font-size: 20px; margin-top: 0; }}
    .badge {{ display: inline-block; padding: 4px 10px; background: #7F1D1D; color: #FECACA; border-radius: 6px; font-size: 12px; font-weight: 600; margin-bottom: 16px; }}
    pre {{ background: #0B1120; color: #E2E8F0; padding: 18px; border-radius: 8px; overflow-x: auto; font-size: 13px; line-height: 1.5; border: 1px solid #1E293B; }}
    .info {{ font-size: 12px; color: #94A3B8; margin-top: 16px; }}
    .guide {{ background: #1E3A8A; border: 1px solid #3B82F6; padding: 16px; border-radius: 8px; margin-top: 20px; font-size: 13px; }}
    .guide h3 {{ margin-top: 0; color: #93C5FD; font-size: 14px; }}
    ol {{ margin-bottom: 0; padding-left: 20px; }}
    li {{ margin-bottom: 6px; }}
    code {{ background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 4px; color: #FDE047; }}
  </style>
</head>
<body>
  <div class="card">
    <span class="badge">MilesWeb / Phusion Passenger Startup Error</span>
    <h1>The Django application encountered an error while starting up</h1>
    
    <pre>{error_trace}</pre>

    <div class="guide">
      <h3>Quick Fix Checklist on MilesWeb cPanel:</h3>
      <ol>
        <li><strong>Missing Dependencies:</strong> Open cPanel Terminal, activate virtualenv, and run: <code>pip install -r requirements.txt</code></li>
        <li><strong>Database Connection:</strong> Check your <code>.env</code> file credentials (DB_NAME, DB_USER, DB_PASSWORD, DB_HOST=localhost).</li>
        <li><strong>Database Migrations:</strong> Run <code>python manage.py migrate</code> in terminal.</li>
        <li><strong>Restart App:</strong> Click <strong>Restart</strong> in cPanel &gt; <em>Setup Python App</em>.</li>
      </ol>
    </div>

    <div class="info">
      <strong>Environment:</strong> {python_info}<br>
      <strong>Search Paths:</strong><br>
      <pre style="padding:10px; font-size:11px;">{sys_path_info}</pre>
    </div>
  </div>
</body>
</html>"""
        output = html.encode('utf-8')
        response_headers = [
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Content-Length', str(len(output)))
        ]
        start_response(status, response_headers)
        return [output]
