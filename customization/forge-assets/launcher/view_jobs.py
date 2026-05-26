#!/usr/bin/env python3
"""
View HyperPod job submission history
"""

import argparse
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description='View HyperPod job history')
    parser.add_argument('--logs-dir', default='../logs', help='Logs directory (default: ../logs)')
    parser.add_argument('--job', help='View specific job log by name or timestamp')
    parser.add_argument('--latest', action='store_true', help='Show latest job')
    parser.add_argument('--last', type=int, metavar='N', help='Show last N jobs')
    parser.add_argument('--search', help='Search for jobs by name pattern')
    return parser.parse_args()


def read_summary(logs_dir):
    """Read and parse the summary log"""
    summary_file = Path(logs_dir) / "jobs_summary.log"
    if not summary_file.exists():
        return []

    jobs = []
    with open(summary_file, 'r') as f:
        for line in f:
            if line.strip():
                parts = line.strip().split(' | ')
                if len(parts) >= 5:
                    jobs.append({
                        'timestamp': parts[0],
                        'job_name': parts[1],
                        'requested_name': parts[2],
                        'instance_type': parts[3],
                        'log_file': parts[4]
                    })
    return jobs


def print_jobs_table(jobs):
    """Print jobs in a formatted table"""
    if not jobs:
        print("No jobs found")
        return

    print("=" * 120)
    print(f"{'Timestamp':<20} {'Job Name':<40} {'Instance Type':<20} {'Log File':<40}")
    print("=" * 120)

    for job in jobs:
        print(f"{job['timestamp']:<20} {job['job_name']:<40} {job['instance_type']:<20} {job['log_file']:<40}")

    print("=" * 120)
    print(f"Total: {len(jobs)} job(s)")


def show_job_log(logs_dir, identifier):
    """Show detailed log for a specific job"""
    logs_path = Path(logs_dir)

    # Try to find log file by pattern
    log_files = list(logs_path.glob(f"*{identifier}*.log"))

    # Exclude summary file
    log_files = [f for f in log_files if f.name != "jobs_summary.log"]

    if not log_files:
        print(f"No log file found matching: {identifier}")
        return

    if len(log_files) > 1:
        print(f"Multiple log files found matching '{identifier}':")
        for lf in log_files:
            print(f"  - {lf.name}")
        print("\nPlease be more specific.")
        return

    log_file = log_files[0]
    print(f"Reading log: {log_file.name}\n")

    with open(log_file, 'r') as f:
        print(f.read())


def main():
    args = parse_args()
    # Resolve logs directory relative to script location
    script_dir = Path(__file__).parent
    logs_dir = (script_dir / args.logs_dir).resolve()

    if not logs_dir.exists():
        print(f"Logs directory not found: {logs_dir}")
        print("No jobs have been submitted yet.")
        return

    # Show specific job log
    if args.job:
        show_job_log(logs_dir, args.job)
        return

    # Read summary
    jobs = read_summary(logs_dir)

    if not jobs:
        print("No jobs found in history")
        return

    # Filter and display
    if args.latest:
        print_jobs_table([jobs[-1]])
        return

    if args.last:
        print_jobs_table(jobs[-args.last:])
        return

    if args.search:
        filtered = [j for j in jobs if args.search.lower() in j['job_name'].lower() or
                    args.search.lower() in j['requested_name'].lower()]
        print_jobs_table(filtered)
        return

    # Show all jobs
    print_jobs_table(jobs)


if __name__ == '__main__':
    main()
