import threading
import queue
import time
import uuid
import subprocess
from concurrent.futures import ThreadPoolExecutor

# Global context to store current job ID in thread
job_context = threading.local()

# Constants
MAX_LOG_LINES = 5000

# Global Buffers (Persistent History)
system_log_buffer = []
job_log_buffers = {} # job_id -> list of strings

# Global Listeners (Active Connections)
# We use a set of Queues. When a message comes in, we put it into all active queues.
system_log_listeners = set() # Set of Queue objects
job_log_listeners = {} # job_id -> Set of Queue objects

# Lock for Log Structures
log_lock = threading.Lock()

def log(message):
    """Adds a message to the log buffer and broadcasts to listeners."""
    timestamp = time.strftime("%H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    print(formatted_message)  # stdout

    with log_lock:
        # 1. System Log
        system_log_buffer.append(formatted_message)
        if len(system_log_buffer) > MAX_LOG_LINES:
            system_log_buffer.pop(0)

        # Broadcast to System Listeners
        for q in list(system_log_listeners):
            try:
                q.put(formatted_message)
            except:
                pass

        # 2. Job Log
        job_id = getattr(job_context, 'job_id', None)
        if job_id:
            # Ensure buffer exists
            if job_id not in job_log_buffers:
                job_log_buffers[job_id] = []

            # Append
            job_log_buffers[job_id].append(formatted_message)

            # Broadcast to Job Listeners
            if job_id in job_log_listeners:
                listeners = job_log_listeners[job_id]
                for q in list(listeners):
                    try:
                        q.put(formatted_message)
                    except:
                        pass

class JobManager:
    def __init__(self, max_workers=4):
        self.lock = threading.Lock()
        self.pending_jobs = []
        self.running_jobs = {} # job_id -> job_dict
        self.history = []

        # job_id -> subprocess.Popen (for cancellation)
        self.active_processes = {}
        self.cancelled_flags = {} # job_id -> bool

        # Thread Pool
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.max_workers = max_workers

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
            # Initialize log buffer
            with log_lock:
                job_log_buffers[job_id] = []

        log(f"Job Queued: {name}")

        # Trigger execution attempt (non-blocking)
        self.executor.submit(self._process_queue)

        return job_id

    def _process_queue(self):
        """Picks a job from pending and runs it if slots available."""
        # Loop to fill available slots
        while True:
            job_to_run = None
            with self.lock:
                # Check active count
                if len(self.running_jobs) >= self.max_workers:
                    return # No slots

                if self.pending_jobs:
                    job_to_run = self.pending_jobs.pop(0)
                    self.running_jobs[job_to_run['id']] = job_to_run
                    self.cancelled_flags[job_to_run['id']] = False
                else:
                    return # No jobs

            if job_to_run:
                self.executor.submit(self._run_job, job_to_run)

    def _run_job(self, job):
        """The actual worker function running in a thread."""
        job_id = job['id']
        job_context.job_id = job_id # Set context for log()

        job_name = job.get('name', 'Unknown Job')

        with self.lock:
            job['status'] = 'running'
            job['started_at'] = time.time()
            if 'details' not in job: job['details'] = {}
            if 'action' not in job['details']: job['details']['action'] = 'Starting...'

        log(f"Starting Job: {job_name}")

        target = job.get('target')
        args = job.get('args', ())

        try:
            target(*args)

            # Check cancellation status
            if self.is_cancelled(job_id):
                job['status'] = 'cancelled'
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

            with self.lock:
                # Move from running to history
                if job_id in self.running_jobs:
                    del self.running_jobs[job_id]

                # Cleanup process references
                if job_id in self.active_processes:
                    del self.active_processes[job_id]
                if job_id in self.cancelled_flags:
                    del self.cancelled_flags[job_id]

                job['completed_at'] = time.time()
                self.history.insert(0, job)
                if len(self.history) > 50: self.history.pop()

                # Note: We do NOT delete the log buffer here.
                # We keep it so the user can view logs of finished jobs.

            # Trigger next job
            self._process_queue()

    # --- Public API ---

    def update_job_details(self, details):
        """Updates details for the CURRENT thread's job."""
        job_id = getattr(job_context, 'job_id', None)
        if not job_id: return

        with self.lock:
            if job_id in self.running_jobs:
                job = self.running_jobs[job_id]
                if 'details' not in job: job['details'] = {}
                job['details'].update(details)

    def set_current_process(self, process):
        """Registers subprocess for the CURRENT thread's job."""
        job_id = getattr(job_context, 'job_id', None)
        if not job_id: return

        with self.lock:
            self.active_processes[job_id] = process

    def is_cancelled(self, job_id=None):
        """Checks cancellation status. If no job_id, uses current thread's job."""
        if job_id is None:
            job_id = getattr(job_context, 'job_id', None)

        if not job_id: return False

        with self.lock:
            return self.cancelled_flags.get(job_id, False)

    def cancel_job(self, job_id):
        with self.lock:
            # 1. Check Running Jobs
            if job_id in self.running_jobs:
                log(f"Cancelling RUNNING job: {self.running_jobs[job_id]['name']}")
                self.cancelled_flags[job_id] = True

                # Update UI
                self.running_jobs[job_id]['details']['error'] = "User requested cancellation"
                self.running_jobs[job_id]['status'] = 'cancelling'

                # Kill Process if exists
                if job_id in self.active_processes:
                    proc = self.active_processes[job_id]
                    try:
                        proc.terminate()
                        log(f"Terminated process for job {job_id}")
                    except Exception as e:
                        log(f"Error terminating process: {e}")
                return True

            # 2. Check Pending Jobs
            for i, job in enumerate(self.pending_jobs):
                if job['id'] == job_id:
                    removed = self.pending_jobs.pop(i)
                    removed['status'] = 'cancelled'
                    removed['completed_at'] = time.time()
                    removed['details'] = {'error': 'Cancelled by user before starting'}
                    self.history.insert(0, removed)
                    if len(self.history) > 50: self.history.pop()
                    log(f"Cancelled PENDING job: {removed['name']}")
                    return True

            return False

    def get_status(self):
        with self.lock:
            def sanitize(job):
                if not job: return None
                j = job.copy()
                if 'target' in j: del j['target']
                if 'args' in j: del j['args']
                return j

            return {
                'running': [sanitize(j) for j in self.running_jobs.values()], # List of running
                'pending': [sanitize(j) for j in self.pending_jobs],
                'history': [sanitize(j) for j in self.history]
            }

    def clear_history(self):
        with self.lock:
            self.history = []

            # Clean up logs for non-running jobs
            running_ids = set(self.running_jobs.keys())

            with log_lock:
                for jid in list(job_log_buffers.keys()):
                    if jid not in running_ids:
                        del job_log_buffers[jid]
                        # Clean listeners if any (should be none ideally)
                        if jid in job_log_listeners:
                             del job_log_listeners[jid]

    # --- Log Listener Methods ---

    def register_system_listener(self):
        """Returns (current_history, queue)."""
        q = queue.Queue()
        with log_lock:
            system_log_listeners.add(q)
            history = list(system_log_buffer)
        return history, q

    def unregister_system_listener(self, q):
        with log_lock:
            if q in system_log_listeners:
                system_log_listeners.remove(q)

    def register_job_listener(self, job_id):
        """Returns (current_history, queue). Returns (None, None) if job not found log."""
        q = queue.Queue()
        with log_lock:
            if job_id not in job_log_buffers:
                return None, None

            if job_id not in job_log_listeners:
                job_log_listeners[job_id] = set()
            job_log_listeners[job_id].add(q)
            history = list(job_log_buffers[job_id])

        return history, q

    def unregister_job_listener(self, job_id, q):
        with log_lock:
            if job_id in job_log_listeners:
                if q in job_log_listeners[job_id]:
                    job_log_listeners[job_id].remove(q)
                if not job_log_listeners[job_id]:
                    del job_log_listeners[job_id]

# Create global instance
job_manager = JobManager(max_workers=4)
