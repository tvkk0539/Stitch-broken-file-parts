import requests
import time
import threading
import json

def create_mock_job():
    """Triggers a repair job on a dummy folder to generate logs."""
    # First create a dummy folder
    requests.post('http://127.0.0.1:5000/api/mkdir', json={'path': '', 'name': 'test_logs_job'})
    time.sleep(1)

    # Trigger repair (it will fail fast because no files, but it will generate logs)
    res = requests.post('http://127.0.0.1:5000/api/repair', json={'path': 'test_logs_job'})
    return res.json()['job_id']

def test_log_persistence():
    print("1. Creating a job...")
    job_id = create_mock_job()
    print(f"   Job ID: {job_id}")

    # Allow job to run and finish (it's fast)
    time.sleep(2)

    print("2. Connect to logs (First time)...")
    # Stream logs for 1 second
    logs_1 = []
    with requests.get(f'http://127.0.0.1:5000/api/logs/{job_id}', stream=True) as r:
        for line in r.iter_lines():
            if line:
                logs_1.append(line.decode('utf-8'))
            # We break early to simulate "user leaving"
            if len(logs_1) > 2:
                break

    print(f"   Received {len(logs_1)} lines.")

    print("3. disconnect and reconnect (Second time)...")
    logs_2 = []
    with requests.get(f'http://127.0.0.1:5000/api/logs/{job_id}', stream=True) as r:
        start_time = time.time()
        for line in r.iter_lines():
            if line:
                logs_2.append(line.decode('utf-8'))
            # Break if we stop receiving data (job finished) or timeout
            if time.time() - start_time > 1:
                break

    print(f"   Received {len(logs_2)} lines.")

    # Verification
    # logs_2 should contain ALL lines from logs_1 plus more (or same if finished)
    print("4. Verifying persistence...")

    # Check if the first line of logs_1 is in logs_2
    if logs_1[0] in logs_2:
        print("   SUCCESS: Old logs reappeared in the second connection.")
    else:
        print("   FAILURE: Old logs are missing.")
        print("   Logs 1 Head:", logs_1[:2])
        print("   Logs 2 Head:", logs_2[:2])

if __name__ == "__main__":
    try:
        test_log_persistence()
    except Exception as e:
        print(f"Error: {e}")
