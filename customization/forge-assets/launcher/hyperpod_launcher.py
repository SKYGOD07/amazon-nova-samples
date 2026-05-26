#!/usr/bin/env python3
"""
Simple HyperPod Job Launcher

Usage:
    python hyperpod_launcher.py \
        --recipe micro_pt_recipe.yaml \
        --name my-training-job \
        --data s3://bucket/path/train.jsonl \
        --val s3://bucket/path/val.jsonl \
        --output s3://bucket/path/output/ \
        --mlflow arn:aws:sagemaker:region:account:mlflow-app/app-ID \
        --container 123456.dkr.ecr.us-east-1.amazonaws.com/repo:tag \
        --instance-type ml.p5.48xlarge \
        --namespace kubeflow
"""

import argparse
import subprocess
import sys
import json
import re
import os
from datetime import datetime
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description='Launch HyperPod training job')

    # Required arguments
    parser.add_argument('--recipe', required=True, help='Path to recipe YAML file')
    parser.add_argument('--name', required=True, help='Job name')
    parser.add_argument('--data', required=True, help='S3 path to training data')
    parser.add_argument('--output', required=True, help='S3 path for output')
    parser.add_argument('--container', required=True, help='Container image URI')

    # Optional arguments
    parser.add_argument('--val', help='S3 path to validation data')
    parser.add_argument('--mlflow', help='MLflow tracking URI')
    parser.add_argument('--model-path', '--model_name_or_path', dest='model_path', help='S3 path to model checkpoint')
    parser.add_argument('--instance-type', default='ml.p5.48xlarge', help='Instance type')
    parser.add_argument('--namespace', default='kubeflow', help='Kubernetes namespace')
    parser.add_argument('--dry-run', action='store_true', help='Print command without executing')
    parser.add_argument('--logs-dir', default='../logs', help='Directory to save logs (default: ../logs)')
    parser.add_argument('--no-logs', action='store_true', help='Disable logging')

    return parser.parse_args()


def build_override_parameters(args):
    """Build the override parameters JSON"""
    params = {
        "instance_type": args.instance_type,
        "recipes.run.name": args.name,
        "container": args.container,
        "recipes.run.data_s3_path": args.data,
        "recipes.run.output_s3_path": args.output,
    }

    # Add optional parameters
    if args.val:
        params["recipes.run.validation_data_s3_path"] = args.val

    if args.mlflow:
        params["recipes.run.mlflow_tracking_uri"] = args.mlflow

    if args.model_path:
        params["recipes.run.model_name_or_path"] = args.model_path

    return json.dumps(params)


def extract_job_name(output):
    """Extract the deployed job name from hyperpod output"""
    # Look for pattern: "NAME: job-name-12345"
    match = re.search(r'^NAME:\s+(.+)$', output, re.MULTILINE)
    if match:
        return match.group(1).strip()

    # Fallback: look in the results directory path
    match = re.search(r'results/([^/]+)/k8s_templates', output)
    if match:
        return match.group(1).strip()

    return None


def save_logs(args, job_name, output, timestamp):
    """Save job submission logs"""
    if args.no_logs or args.dry_run:
        return

    # Resolve logs directory relative to script location
    script_dir = Path(__file__).parent
    logs_dir = (script_dir / args.logs_dir).resolve()
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Save individual job log
    safe_job_name = job_name or "unknown"
    log_filename = f"{timestamp}_{safe_job_name}.log"
    log_filepath = logs_dir / log_filename

    with open(log_filepath, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("HyperPod Job Submission Log\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Job Name: {job_name or 'N/A'}\n\n")

        f.write("Parameters:\n")
        f.write(f"  Recipe: {args.recipe}\n")
        f.write(f"  Name: {args.name}\n")
        f.write(f"  Instance Type: {args.instance_type}\n")
        f.write(f"  Namespace: {args.namespace}\n")
        f.write(f"  Data: {args.data}\n")
        if args.val:
            f.write(f"  Validation: {args.val}\n")
        f.write(f"  Output: {args.output}\n")
        if args.model_path:
            f.write(f"  Model Path: {args.model_path}\n")
        if args.mlflow:
            f.write(f"  MLflow: {args.mlflow}\n")
        f.write(f"  Container: {args.container}\n\n")

        f.write("=" * 80 + "\n")
        f.write("Full Output:\n")
        f.write("=" * 80 + "\n\n")
        f.write(output)

    # Append to summary log
    summary_file = logs_dir / "jobs_summary.log"
    with open(summary_file, 'a') as f:
        f.write(f"{timestamp} | {job_name or 'N/A'} | {args.name} | {args.instance_type} | {log_filename}\n")

    print(f"\n📝 Logs saved to: {log_filepath}")
    print(f"📋 Summary updated: {summary_file}")


def run_hyperpod_job(args):
    """Execute the hyperpod start-job command"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    override_params = build_override_parameters(args)

    # Convert recipe path to absolute path
    recipe_path = Path(args.recipe).resolve()
    if not recipe_path.exists():
        print(f"❌ Error: Recipe file not found: {recipe_path}", file=sys.stderr)
        sys.exit(1)

    # Build the command
    cmd = [
        'hyperpod', 'start-job',
        '-n', args.namespace,
        '--recipe', str(recipe_path),
        '--override-parameters', override_params
    ]

    print("=" * 70)
    print("🚀 Launching HyperPod Job")
    print("=" * 70)
    print(f"Timestamp: {timestamp}")
    print(f"Recipe: {recipe_path}")
    print(f"Job Name: {args.name}")
    print(f"Instance: {args.instance_type}")
    print(f"Namespace: {args.namespace}")
    print(f"Data: {args.data}")
    if args.val:
        print(f"Validation: {args.val}")
    print(f"Output: {args.output}")
    if args.model_path:
        print(f"Model Path: {args.model_path}")
    if args.mlflow:
        print(f"MLflow: {args.mlflow}")
    print(f"Container: {args.container}")
    print("=" * 70)
    print()

    if args.dry_run:
        print("DRY RUN - Command that would be executed:")
        print(" ".join(cmd))
        return None, timestamp

    # Execute the command
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        output = result.stdout
        print(output)

        if result.stderr:
            print(result.stderr, file=sys.stderr)

        # Extract and display the job name
        job_name = extract_job_name(output)

        # Save logs
        save_logs(args, job_name, output, timestamp)

        if job_name:
            print()
            print("=" * 70)
            print(f"✅ Job Successfully Deployed")
            print(f"📝 Job Name: {job_name}")
            print("=" * 70)
            return job_name, timestamp
        else:
            print()
            print("⚠️  Job deployed but couldn't extract job name from output")
            return None, timestamp

    except subprocess.CalledProcessError as e:
        print(f"❌ Error executing hyperpod command:", file=sys.stderr)
        print(e.stderr, file=sys.stderr)

        # Save error logs
        if not args.no_logs:
            save_logs(args, None, f"ERROR:\n{e.stderr}", timestamp)

        sys.exit(1)
    except FileNotFoundError:
        print("❌ Error: 'hyperpod' command not found", file=sys.stderr)
        print("Make sure you have activated the hyperpod-cli environment:", file=sys.stderr)
        print("  source ~/hyperpod-cli-env/bin/activate", file=sys.stderr)
        sys.exit(1)


def main():
    args = parse_args()
    job_name, timestamp = run_hyperpod_job(args)

    # Return job name for scripting purposes
    if job_name and not args.dry_run:
        # Print just the job name on the last line for easy parsing
        print(f"\nJOB_NAME={job_name}")


if __name__ == '__main__':
    main()
