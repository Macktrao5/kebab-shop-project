import os
from django.core.wsgi import get_wsgi_application
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Crea le tabelle automaticamente se non esistono
try:
    call_command('migrate')
except Exception as e:
    print(f"Errore migrazione automatica: {e}")

application = get_wsgi_application()