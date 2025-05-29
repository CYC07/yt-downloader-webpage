# backend_project/backend_project/celery.py
import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
# Make sure 'backend_project.settings' matches your project structure/name
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_project.settings')

# Create the Celery application instance
# The first argument 'backend_project' is the name of the current module (or can be arbitrary)
app = Celery('backend_project')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix (e.g., CELERY_BROKER_URL).
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
# This automatically finds tasks defined in files like 'tasks.py' within your apps.
app.autodiscover_tasks()

# (Optional) Example debug task:
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')