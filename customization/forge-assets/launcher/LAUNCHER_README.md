# HyperPod Job Launcher

Simple launcher scripts for AWS HyperPod training jobs. Choose either Python or Bash version.

## Features

- ✅ Simple argument-based interface
- ✅ Automatic job name extraction
- ✅ **Automatic logging** - Never lose track of job names again!
- ✅ Job history with searchable logs
- ✅ Dry-run mode for testing
- ✅ Support for optional validation data and MLflow tracking
- ✅ Clear output with job deployment confirmation

## Quick Start

### 1. Activate HyperPod CLI Environment

```bash
source ~/hyperpod-cli-env/bin/activate
```

### 2. Run a Job

**Python version:**
```bash
python3 hyperpod_launcher.py \
    --recipe micro_pt_recipe.yaml \
    --name my-training-job \
    --data s3://bucket/train.jsonl \
    --output s3://bucket/output/ \
    --container 123456.dkr.ecr.region.amazonaws.com/repo:tag
```

**Bash version:**
```bash
./hyperpod_launcher.sh \
    --recipe micro_pt_recipe.yaml \
    --name my-training-job \
    --data s3://bucket/train.jsonl \
    --output s3://bucket/output/ \
    --container 123456.dkr.ecr.region.amazonaws.com/repo:tag
```

## Arguments

### Required
- `--recipe` - Path to recipe YAML file (e.g., `micro_pt_recipe.yaml`)
- `--name` - Job name (will have random suffix added by HyperPod)
- `--data` - S3 path to training data (e.g., `s3://bucket/train.jsonl`)
- `--output` - S3 path for output (e.g., `s3://bucket/output/`)
- `--container` - Container image URI

### Optional
- `--val` - S3 path to validation data
- `--mlflow` - MLflow tracking URI (e.g., `arn:aws:sagemaker:region:account:mlflow-app/app-ID`)
- `--instance-type` - Instance type (default: `ml.p5.48xlarge`)
- `--namespace` - Kubernetes namespace (default: `kubeflow`)
- `--logs-dir` - Directory to save logs (default: `logs`)
- `--no-logs` - Disable logging
- `--dry-run` - Print command without executing

## Output

The script will:
1. Display job configuration
2. Execute the HyperPod command
3. Show the full HyperPod output
4. Extract and highlight the deployed job name
5. Print `JOB_NAME=<name>` for easy parsing

### Example Output

```
======================================================================
🚀 Launching HyperPod Job
======================================================================
Recipe: micro_pt_recipe.yaml
Job Name: dewanup-cpt-nodm-ce-chkpt
Instance: ml.p5.48xlarge
Namespace: kubeflow
Data: s3://bucket/train.jsonl
Output: s3://bucket/output/
======================================================================

[... HyperPod output ...]

======================================================================
✅ Job Successfully Deployed
📝 Job Name: dewanup-cpt-nodm-ce-chkpt-a0yrv
======================================================================

JOB_NAME=dewanup-cpt-nodm-ce-chkpt-a0yrv

📝 Logs saved to: logs/20260521_091959_dewanup-cpt-nodm-ce-chkpt-a0yrv.log
📋 Summary updated: logs/jobs_summary.log
```

## 📝 Automatic Logging

All job submissions are automatically logged to the `logs/` directory:

### Files Created

1. **Individual job logs**: `logs/TIMESTAMP_JOBNAME.log`
   - Complete job details
   - All parameters used
   - Full HyperPod output
   - Perfect for debugging

2. **Summary log**: `logs/jobs_summary.log`
   - One-line summary of all jobs
   - Easy to grep and search
   - Quick job name lookup

### View Job History

Use the `view_jobs.py` script to view past jobs:

```bash
# View all jobs
python3 view_jobs.py

# View latest job
python3 view_jobs.py --latest

# View last 5 jobs
python3 view_jobs.py --last 5

# Search for jobs by name
python3 view_jobs.py --search dewanup

# View specific job log
python3 view_jobs.py --job dewanup-cpt-nodm-ce-chkpt-a0yrv
```

### Example: View Jobs Output

```
========================================================================================================================
Timestamp            Job Name                                 Instance Type        Log File
========================================================================================================================
20260521_091959      dewanup-cpt-nodm-ce-chkpt-a0yrv          ml.p5.48xlarge       20260521_091959_dewanup-cpt-nodm-ce-chkpt-a0yrv.log
20260521_103045      my-training-job-x7k2m                    ml.p5en.48xlarge     20260521_103045_my-training-job-x7k2m.log
========================================================================================================================
Total: 2 job(s)
```

### Disable Logging

If you don't want logs saved:

```bash
python3 hyperpod_launcher.py ... --no-logs
```

## Advanced Usage

### Capture Job Name for Scripting

```bash
# Run and capture output
OUTPUT=$(python3 hyperpod_launcher.py \
    --recipe micro_pt_recipe.yaml \
    --name my-job \
    --data s3://bucket/train.jsonl \
    --output s3://bucket/output/ \
    --container my-container:tag)

# Extract job name
JOB_NAME=$(echo "$OUTPUT" | grep "^JOB_NAME=" | cut -d'=' -f2)

# Use the job name
echo "Monitoring job: $JOB_NAME"
hyperpod list-jobs | grep "$JOB_NAME"
```

### Test Before Running

```bash
python3 hyperpod_launcher.py \
    --recipe micro_pt_recipe.yaml \
    --name test-job \
    --data s3://bucket/train.jsonl \
    --output s3://bucket/output/ \
    --container my-container:tag \
    --dry-run
```

This will print the exact command that would be executed without actually running it.

## Full Example

See `launcher_examples.sh` for more usage examples.

```bash
python3 hyperpod_launcher.py \
    --recipe micro_pt_recipe.yaml \
    --name dewanup-cpt-nodm-ce-chkpt \
    --data s3://618100645563-nova-customization-beta/dewanup/data/cpt/train.jsonl \
    --val s3://618100645563-nova-customization-beta/dewanup/data/cpt/val.jsonl \
    --output s3://618100645563-nova-customization-beta/dewanup/output/ \
    --mlflow arn:aws:sagemaker:us-east-1:618100645563:mlflow-app/app-QYBQZINLZDLY \
    --container 708977205387.dkr.ecr.us-east-1.amazonaws.com/nova-fine-tune-repo:SM-HP-CPT-V2-BETA-latest \
    --instance-type ml.p5.48xlarge \
    --namespace kubeflow
```

## Differences Between Python and Bash Versions

Both versions provide the same functionality:
- **Python version** (`hyperpod_launcher.py`) - Better error handling, easier to extend
- **Bash version** (`hyperpod_launcher.sh`) - No Python dependency, pure shell script

Choose whichever you prefer!

## Troubleshooting

### Command not found: hyperpod
Make sure you've activated the HyperPod CLI environment:
```bash
source ~/hyperpod-cli-env/bin/activate
```

### Job name not extracted
The script will still deploy the job successfully. Check the HyperPod output for the results directory path which contains the job name.

## Files

- `hyperpod_launcher.py` - Python launcher script
- `hyperpod_launcher.sh` - Bash launcher script
- `view_jobs.py` - View job history and logs
- `launcher_examples.sh` - Usage examples
- `LAUNCHER_README.md` - This documentation
- `logs/` - Automatic logs directory (git-ignored)
