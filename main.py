import csv
import datetime
import os
import shutil
import smtplib
import subprocess
import time
from email.message import EmailMessage
from pathlib import Path
import settings

# Constants
RUNS_DIR = Path("runs")
TIMEOUT_SECONDS = 300  # 5 minutes
RETENTION_DAYS = 10

def cleanup_old_runs():
    """Deletes run folders older than RETENTION_DAYS."""
    if not RUNS_DIR.exists():
        return
    now = time.time()
    for run_folder in RUNS_DIR.iterdir():
        if run_folder.is_dir():
            folder_time = run_folder.stat().st_mtime
            if (now - folder_time) > RETENTION_DAYS * 86400:
                print(f"Deleting old run folder: {run_folder}")
                shutil.rmtree(run_folder, ignore_errors=True)

def find_test_dir(repo_dir):
    """Finds the first directory containing test files to run tests from."""
    for root, _, files in os.walk(repo_dir):
        if any(f.startswith("test_") and f.endswith(".py") for f in files):
            return Path(root)
    return repo_dir # Fallback to repo root if no specific test dir found

def process_student_repo(student_name, repo_url, run_base_dir):
    """Clones a repo, runs tests with timeout, returns status and output."""
    student_dir = run_base_dir / student_name
    student_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Clone repository
    print(f"Cloning {repo_url} for {student_name}...")
    try:
        subprocess.run(
            ["git", "clone", repo_url, "repo"],
            cwd=student_dir,
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        return "Clone Failed", e.stderr

    print(f"Cloned {repo_url} for {student_name}... OK")
    repo_dir = student_dir / "repo"
    
    # 2. Run tests (Assuming standard python unittest structure)
    print(f"Running tests for {student_name}... in {repo_dir}")
    test_cwd = find_test_dir(repo_dir)
    print(f"Running tests in directory: {test_cwd}")
    try:
        result = subprocess.run(
            ["python", "-m", "unittest", "discover"],
            cwd=test_cwd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS
        )
        
        output = result.stdout + "\n" + result.stderr
        
        # Stricter check for success. Unittest summary is on stderr.
        # A successful run must have exit code 0, have "OK" in stderr,
        # and must NOT report that zero tests were run.
        status = "Failed" # Default to Failed
        if result.returncode == 0 and "OK" in result.stderr and "Ran 0 tests" not in result.stderr:
            status = "Success"
        elif "Ran 0 tests" in result.stderr:
            status = "Failed (No tests found)"

        return status, output
    except subprocess.TimeoutExpired as e:
        return "Timeout (5m+)", f"Tests exceeded 5 minutes.\n{e.stdout}\n{e.stderr}"
    except Exception as e:
        return "Error", str(e)

def send_email(csv_path):
    """Sends the result CSV via email."""
    print(f"Sending email to {settings.EMAIL_TO}...")
    msg = EmailMessage()
    msg['Subject'] = f"Homework Run Results - {datetime.date.today()}"
    msg['From'] = settings.EMAIL_FROM
    msg['To'] = settings.EMAIL_TO
    msg.set_content("Please find the attached homework run results.")

    if csv_path.exists():
        with open(csv_path, 'rb') as f:
            csv_data = f.read()
            msg.add_attachment(csv_data, maintype='text', subtype='csv', filename=csv_path.name)

    try:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.EMAIL_FROM, settings.EMAIL_PASSWORD)
            server.send_message(msg)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

def main(input_csv):
    cleanup_old_runs()

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    current_run_dir = RUNS_DIR / timestamp
    current_run_dir.mkdir(parents=True, exist_ok=True)
    
    output_csv_path = current_run_dir / f"results_{timestamp}.csv"
    
    results = []

    if not Path(input_csv).exists():
        print(f"Input file {input_csv} not found.")
        return

    with open(input_csv, mode='r', newline='', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            student_name = row.get('student_name')
            repo_url = row.get('repo_url')
            
            if not student_name or not repo_url:
                continue
                
            status, output = process_student_repo(student_name, repo_url, current_run_dir)
            results.append({
                'student_name': student_name,
                'repo_url': repo_url,
                'status': status,
                'output': output
            })

    # Write results to output CSV
    with open(output_csv_path, mode='w', newline='', encoding='utf-8') as outfile:
        fieldnames = ['student_name', 'repo_url', 'status', 'output']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Results saved to {output_csv_path}")
    send_email(output_csv_path)

if __name__ == "__main__":
    input_file = "students.csv"  # Name of the input CSV file
    main(input_file)