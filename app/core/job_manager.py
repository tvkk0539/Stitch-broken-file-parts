import threading
import queue
import time
import uuid
import subprocess

# Global queue for log streaming
log_queue = queue.Queue()

def log(message):
    """Adds a message to the log queue."""
    timestamp = time.strftime("%H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    print(formatted_message)  # Also print to stdout for container logs
    log_queue.put(formatted_message)

class JobManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.pending_jobs = [] # List of dicts
        self.current_job = None # Dict
        self.history = [] # Finished jobs
        self.current_process = None # subprocess.Popen object
        self._cancelled = False

    def add_job(self, name, target, args=(), initial_details=None):
        job_id = str(uuid.uuid4())
        job = {
            'id': job_id,
            'name': name,
            'target': target,
            'args': args,
            'status': 'queued',
            'added_at': time.time(),
            'details': initial_details or {}
        }
        with self.lock:
            self.pending_jobs.append(job)
        log(f"Job Queued: {name}")
        return job_id

    def get_next_job(self):
        with self.lock:
            if self.pending_jobs:
                return self.pending_jobs.pop(0)
            return None

    def set_current_job(self, job):
        with self.lock:
            self.current_job = job
            self._cancelled = False
            if job:
                self.current_job['status'] = 'running'
                self.current_job['started_at'] = time.time()
                self.current_job['details'] = {'action': 'Starting...'}

    def update_job_details(self, details):
        with self.lock:
            if self.current_job:
                # Merge details
                if 'details' not in self.current_job:
                    self.current_job['details'] = {}
                self.current_job['details'].update(details)

    def set_current_process(self, process):
        """Registers the active subprocess so it can be killed if cancelled."""
        with self.lock:
            self.current_process = process

    def clear_current_process(self):
        with self.lock:
            self.current_process = None

    def is_cancelled(self):
        with self.lock:
            return self._cancelled

    def cancel_job(self, job_id):
        with self.lock:
            # Check if it's the running job
            if self.current_job and self.current_job['id'] == job_id:
                log(f"Cancelling RUNNING job: {self.current_job['name']}")
                self._cancelled = True

                # Update details to reflect cancellation intent
                if 'details' not in self.current_job: self.current_job['details'] = {}
                self.current_job['details']['error'] = "User requested cancellation"

                if self.current_process:
                    try:
                        self.current_process.terminate()
                    except Exception as e:
                        log(f"Error terminating process: {e}")
                return True

            # Check pending jobs
            for i, job in enumerate(self.pending_jobs):
                if job['id'] == job_id:
                    removed = self.pending_jobs.pop(i)
                    removed['status'] = 'cancelled'
                    removed['completed_at'] = time.time()
                    removed['details'] = {'error': 'Cancelled by user before starting'}
                    self.history.insert(0, removed) # Add to history
                    if len(self.history) > 50: self.history.pop()
                    log(f"Cancelled PENDING job: {removed['name']}")
                    return True

            return False

    def get_status(self):
        with self.lock:
            # Return sanitised copies to avoid race conditions and JSON errors
            def sanitize(job):
                if not job: return None
                j = job.copy()
                if 'target' in j: del j['target']
                if 'args' in j: del j['args']
                return j

            return {
                'current': sanitize(self.current_job),
                'pending': [sanitize(j) for j in self.pending_jobs],
                'history': [sanitize(j) for j in self.history]
            }

    def add_to_history(self, job):
        with self.lock:
            # Finalize job state
            job['completed_at'] = time.time()
            self.history.insert(0, job)
            if len(self.history) > 50:
                self.history.pop()

    def clear_history(self):
        with self.lock:
            self.history = []

def worker(job_manager):
    """Background worker that processes jobs from the JobManager."""
    while True:
        job = job_manager.get_next_job()

        if not job:
            time.sleep(1) # Poll for new jobs
            continue

        job_manager.set_current_job(job)
        job_name = job.get('name', 'Unknown Job')
        log(f"Starting Job: {job_name}")

        target = job.get('target')
        args = job.get('args', ())

        try:
            target(*args)
            # Check if job was marked as failed/cancelled internally by the target
            # Ideally target updates job details.
            # We assume success unless exception, OR if job details has error

            # Determine status based on cancellation or error presence
            if job_manager.is_cancelled():
                job['status'] = 'cancelled'
                if 'details' not in job: job['details'] = {}
                if 'error' not in job['details']: job['details']['error'] = 'Cancelled by user'
            elif job.get('details', {}).get('error'):
                 job['status'] = 'failed'
            else:
                 job['status'] = 'completed'

        except Exception as e:
            log(f"Job {job_name} Failed: {e}")
            job['status'] = 'failed'
            if 'details' not in job: job['details'] = {}
            job['details']['error'] = str(e)

            import traceback
            log(traceback.format_exc())
        finally:
            log(f"Finished Job: {job_name} ({job.get('status', 'unknown')})")
            job_manager.add_to_history(job)
            job_manager.set_current_job(None)
            job_manager.clear_current_process()
