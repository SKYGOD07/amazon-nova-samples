#!/bin/bash
# Example usage of HyperPod launchers
# Run from the launcher/ directory

# Note: All jobs are automatically logged to ../logs/ directory
# Use: python3 view_jobs.py to view job history

# ============================================================================
# Example 1: Python launcher with all parameters
# ============================================================================

python3 hyperpod_launcher.py \
    --recipe ../micro_pt_recipe.yaml \
    --name dewanup-cpt-nodm-ce-chkpt \
    --data s3://618100645563-nova-customization-beta/dewanup/data/cpt/train.jsonl \
    --val s3://618100645563-nova-customization-beta/dewanup/data/cpt/val.jsonl \
    --output s3://618100645563-nova-customization-beta/dewanup/output/ \
    --mlflow arn:aws:sagemaker:us-east-1:618100645563:mlflow-app/app-QYBQZINLZDLY \
    --container 708977205387.dkr.ecr.us-east-1.amazonaws.com/nova-fine-tune-repo:SM-HP-CPT-V2-BETA-latest \
    --instance-type ml.p5.48xlarge \
    --namespace kubeflow

# ============================================================================
# Example 2: Bash launcher with minimal parameters (no validation data)
# ============================================================================

./hyperpod_launcher.sh \
    --recipe ../micro_pt_recipe.yaml \
    --name my-simple-job \
    --data s3://bucket/train.jsonl \
    --output s3://bucket/output/ \
    --container 708977205387.dkr.ecr.us-east-1.amazonaws.com/nova-fine-tune-repo:latest

# ============================================================================
# Example 3: Dry run to see the command without executing
# ============================================================================

python3 hyperpod_launcher.py \
    --recipe ../micro_pt_recipe.yaml \
    --name test-job \
    --data s3://bucket/train.jsonl \
    --output s3://bucket/output/ \
    --container my-container:tag \
    --dry-run

# ============================================================================
# Example 4: Capture job name in a variable for further processing
# ============================================================================

# Run the launcher and capture output
OUTPUT=$(python3 hyperpod_launcher.py \
    --recipe ../micro_pt_recipe.yaml \
    --name my-job \
    --data s3://bucket/train.jsonl \
    --output s3://bucket/output/ \
    --container my-container:tag)

# Extract the job name
JOB_NAME=$(echo "$OUTPUT" | grep "^JOB_NAME=" | cut -d'=' -f2)

echo "Deployed job: $JOB_NAME"

# Now you can use $JOB_NAME for monitoring, logging, etc.
# hyperpod list-jobs | grep "$JOB_NAME"

# ============================================================================
# Example 5: Using different instance types
# ============================================================================

./hyperpod_launcher.sh \
    --recipe ../micro_pt_recipe.yaml \
    --name large-job \
    --data s3://bucket/train.jsonl \
    --output s3://bucket/output/ \
    --container my-container:tag \
    --instance-type ml.p5en.48xlarge

# ============================================================================
# Example 6: View job history
# ============================================================================

# View all submitted jobs
python3 view_jobs.py

# View latest job details
python3 view_jobs.py --latest

# View last 3 jobs
python3 view_jobs.py --last 3

# Search for specific jobs
python3 view_jobs.py --search dewanup

# View full log for a specific job
python3 view_jobs.py --job dewanup-cpt-nodm-ce-chkpt-a0yrv

# ============================================================================
# Example 7: Disable logging (if needed)
# ============================================================================

python3 hyperpod_launcher.py \
    --recipe ../micro_pt_recipe.yaml \
    --name temp-job \
    --data s3://bucket/train.jsonl \
    --output s3://bucket/output/ \
    --container my-container:tag \
    --no-logs

# ============================================================================
# Example 8: Custom logs directory
# ============================================================================

python3 hyperpod_launcher.py \
    --recipe ../micro_pt_recipe.yaml \
    --name my-job \
    --data s3://bucket/train.jsonl \
    --output s3://bucket/output/ \
    --container my-container:tag \
    --logs-dir my_custom_logs
