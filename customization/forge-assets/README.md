# Amazon Nova HyperPod Training Guide

### ⭐ Forge Exclusive Content

## ✅ START HERE to get Hyperpod Setup completed
## Get your starter assets here `s3://nova-forge-c7363-206080352451-us-east-1/v1/starter_samples/`
## Get your recipes here: `s3://nova-forge-c7363-206080352451-us-east-1/v1/src` (pre-downloded as part of installation)

Complete guide for training and deploying Amazon Nova models using SageMaker HyperPod.

## Table of Contents

1. [Installation](#installation)
2. [Launching Jobs](#launching-jobs)
3. [Monitoring Jobs](#monitoring-jobs)
4. [Viewing Logs](#viewing-logs)
5. [Scripts Workflow](#scripts-workflow)
6. [Evaluation](#evaluation)
7. [Model Hosting](#model-hosting)

---

## Installation

### 1. Install HyperPod CLI

Run the installation script:

```bash
./install_hyperpod_cli.sh
```

This script will:

- ✅ Check prerequisites (Python 3.8-3.12, AWS credentials, build tools)
- ✅ Download and patch the official AWS HyperPod CLI installer
- ✅ Create an isolated Python environment at `~/hyperpod-cli-env`
- ✅ Install HyperPod CLI and dependencies

### 2. Activate the Environment

After installation, activate the HyperPod CLI environment:

```bash
source ~/hyperpod-cli-env/bin/activate
```

You'll need to activate this environment every time you want to use HyperPod commands.

### 3. Verify Installation

```bash
hyperpod --help
```

---

## Launching Jobs

### Quick Start

Navigate to the launcher directory:

```bash
cd launcher/
```

### Using the Bash Launcher

```bash
./hyperpod_launcher.sh \
    --recipe ../micro_pt_recipe.yaml \
    --namespace kubeflow \
    --name my-training-job \
    --instance-type ml.p5.48xlarge \
    --container YOUR_ECR_CONTAINER_URI \
    --data s3://your-bucket/path/train.jsonl \
    --val s3://your-bucket/path/val.jsonl \
    --output s3://your-bucket/path/output/ \
    --mlflow arn:aws:sagemaker:region:account:mlflow-app/app-ID
```

### Required Arguments

- `--recipe` - Path to recipe YAML file (e.g., `../micro_pt_recipe.yaml`)
- `--name` - Job name (will have random suffix added by HyperPod)
- `--data` - S3 path to training data
- `--output` - S3 path for output
- `--container` - Container image URI from ECR

[See full hyerpod_launcher.sh documentation →](launcher/LAUNCHER_README.md)

### Optional Arguments

- `--val` - S3 path to validation data
- `--mlflow` - MLflow tracking URI for experiment tracking
- `--instance-type` - Instance type (default: `ml.p5.48xlarge`)
- `--namespace` - Kubernetes namespace (default: `kubeflow`)
- `--dry-run` - Print command without executing

### Recipe Files

Two recipe templates are provided:

- __`micro_pt_recipe.yaml`__ - Standard pre-training/fine-tuning
- __`micro_eval.yaml`__ - Model evaluation

Edit these files to customize:

- Model parameters (learning rate, batch size, etc.)
- Training duration (steps, epochs)
- Hardware configuration (GPUs per node)

### Example Output

```md
======================================================================
🚀 Launching HyperPod Job
======================================================================
Timestamp: 20260522_091959
Recipe: ../micro_pt_recipe.yaml
Job Name: my-training-job
Instance: ml.p5.48xlarge
...
======================================================================

[... HyperPod output ...]

======================================================================
✅ Job Successfully Deployed
📝 Job Name: my-training-job-a0yrv
======================================================================

📝 Logs saved to: ../logs/20260522_091959_my-training-job-a0yrv.log
📋 Summary updated: ../logs/jobs_summary.log

JOB_NAME=my-training-job-a0yrv
```

---

## Listing Jobs

### List Running Jobs

```bash
hyperpod list-jobs
```

### Get Job Status

```bash
hyperpod get-job --name <job-name>
```

### Watch Job Logs (Real-time)

```bash
hyperpod logs --name <job-name> --follow
```

### Check Kubernetes Pods

```bash
kubectl get pods -n kubeflow | grep <job-name>
```

### View Pod Details

```bash
kubectl describe pod <pod-name> -n kubeflow
```

---

## Viewing Logs

### View Job History

From the `launcher/` directory:

```bash
# View all submitted jobs
python3 view_jobs.py

# View latest job
python3 view_jobs.py --latest

# View last 5 jobs
python3 view_jobs.py --last 5

# Search for specific jobs
python3 view_jobs.py --search my-training

# View full log for a specific job
python3 view_jobs.py --job a0yrv
```

---

## Scripts Workflow

After launching a job, use the utility scripts in the `scripts/` directory for the complete ML workflow.

### Complete Workflow Sequence

#### 1. Fetch Training Logs

Monitor your training job by fetching logs from CloudWatch:

```bash
cd scripts/

# Fetch logs using job name
python3 fetch_logs.py \
    --job-name my-training-job-a0yrv \
    --cluster my-hyperpod-rig \
    --lines 1000 \
    --output training_logs.txt
```

**What it does:**

- Connects to CloudWatch Logs
- Finds your training job's log stream
- Downloads recent logs for debugging/monitoring

[See full fetch_logs.py documentation →](scripts/README.md#1-fetch-logs-fetch_logspy)

#### 2. View Training Metrics (MLflow)

Access your MLflow tracking server to view training progress:

```bash
# Get presigned MLflow URL
python3 get_mlflow_url.py \
    --tracking-server-name TestRigTrackingServer

# URL expires in 5 minutes by default
# Open the URL in your browser to view:
# - Training loss curves
# - Validation metrics
# - Hyperparameters
# - Model artifacts
```

**What it does:**

- Generates a presigned URL for MLflow UI
- Provides access to experiment tracking
- Shows real-time training metrics

[See full get_mlflow_url.py documentation →](scripts/README.md#4-get-mlflow-url-get_mlflow_urlpy)

#### 3. Deploy Model Endpoint

Once training completes, deploy your model for inference:

```bash
# Deploy the trained model
python3 deploy_simple_endpoint.py \
    --model-s3-location s3://my-bucket/output/my-training-job-a0yrv/model/ \
    --model-name my-nova-model \
    --instance-type ml.p5.48xlarge \
    --region us-west-2

# Deployment takes 15-30 minutes
# The script will wait for the endpoint to be InService
```

**What it does:**

- Creates SageMaker model from S3 artifacts
- Creates endpoint configuration
- Launches inference endpoint
- Waits for endpoint to be ready

[See full deploy_simple_endpoint.py documentation →](scripts/README.md#2-deploy-endpoint-deploy_simple_endpointpy)

#### 4. Verify Endpoint Status

Check your endpoint's configuration and status:

```bash
# Get detailed endpoint information
python3 describe-endpoint.py my-nova-model-Endpoint
```

**What it does:**

- Shows endpoint status (InService, Creating, Failed, etc.)
- Displays instance configuration
- Lists inference components (if using)
- Shows model details

[See full describe-endpoint.py documentation →](scripts/README.md#3-describe-endpoint-describe-endpointpy)

### Quick Reference

```bash
# Navigate to scripts directory
cd scripts/

# 1. Fetch logs
python3 fetch_logs.py --job-name <job-name> --cluster <cluster-name>

# 2. Get MLflow URL
python3 get_mlflow_url.py --tracking-server-name <server-name>

# 3. Deploy endpoint
python3 deploy_simple_endpoint.py \
    --model-s3-location <s3-uri> \
    --model-name <name>

# 4. Verify endpoint
python3 describe-endpoint.py <endpoint-name>
```

### Full Documentation

For detailed documentation, examples, and troubleshooting, see:

- **[scripts/README.md](scripts/README.md)** - Complete scripts documentation

---

## Evaluation

### Running Evaluation Jobs

Use the evaluation recipe:

```bash
cd launcher/

./hyperpod_launcher.sh \
    --recipe ../micro_eval.yaml \
    --namespace kubeflow \
    --name my-model-eval \
    --instance-type ml.p5.48xlarge \
    --container 708977205387.dkr.ecr.us-east-1.amazonaws.com/nova-evaluation-repo:SM-HP-Eval-Beta-latest \
    --model_name_or_path s3://customer-escrow-618100645563-hp-ae89f69b/dewanup-cpt-dm-ce-chkpt-j43kd/outputs/checkpoints/step_100 \
    --data s3://your-bucket/path/eval_data.jsonl \
    --output s3://your-bucket/path/eval_output/
```

### Evaluation Metrics

Evaluation results will be saved to your output S3 path:

- Accuracy scores
- Perplexity
- Task-specific metrics
- Confusion matrices

### View Evaluation Results

```bash
# Download results from S3
aws s3 cp s3://your-bucket/path/eval_output/ ./eval_results/ --recursive

# View metrics
cat eval_results/metrics.json
```

---

## Model Hosting

### Option 1: SageMaker Endpoint

#### Deploy Model

Use the deployment script from the `scripts/` directory:

```bash
cd scripts/

python3 deploy_simple_endpoint.py \
    --model-s3-location s3://your-bucket/output/my-training-job/model/ \
    --model-name my-nova-model \
    --instance-type ml.p5.48xlarge \
    --region us-west-2
```

See [Scripts Workflow](#scripts-workflow) for complete deployment instructions.

#### Verify Endpoint

Check endpoint status:

```bash
python3 describe-endpoint.py my-nova-model-Endpoint
```

---

## Project Structure

```ini
.
├── README.md                    # This file
├── install_hyperpod_cli.sh     # HyperPod CLI installation
├── micro_pt_recipe.yaml        # Training recipe
├── micro_eval.yaml             # Evaluation recipe
├── train.jsonl                 # Sample training data
├── launcher/                   # Job launcher tools
│   ├── hyperpod_launcher.py    # Python launcher
│   ├── hyperpod_launcher.sh    # Bash launcher
│   ├── view_jobs.py            # View job history
│   ├── launcher_examples.sh    # Usage examples
│   ├── launcher.md             # Quick reference
│   └── LAUNCHER_README.md      # Detailed launcher docs
├── scripts/                    # Utility scripts
│   ├── README.md               # Scripts documentation
│   ├── fetch_logs.py           # Fetch CloudWatch logs
│   ├── get_mlflow_url.py       # Get MLflow tracking URL
│   ├── deploy_simple_endpoint.py  # Deploy SageMaker endpoint
│   └── describe-endpoint.py    # Describe endpoint details
└── logs/                       # Auto-generated logs
    ├── TIMESTAMP_JOBNAME.log   # Individual job logs
    └── jobs_summary.log        # All jobs summary
```

---

## Troubleshooting

### HyperPod CLI Not Found

Make sure to activate the environment:

```bash
source ~/hyperpod-cli-env/bin/activate
```

### AWS Credentials Error

Configure AWS credentials:

```bash
aws configure
```

### Job Stuck in Pending

Check Kubernetes pods:

```bash
kubectl get pods -n kubeflow
kubectl describe pod <pod-name> -n kubeflow
```

Common issues:

- Insufficient resources
- Image pull errors
- Configuration errors

### Can't Find Job Name

Check your logs:

```bash
cd launcher/
python3 view_jobs.py --latest
```

---

## Additional Resources

- [Amazon Nova Documentation](https://docs.aws.amazon.com/nova/)
- [SageMaker HyperPod Guide](https://docs.aws.amazon.com/sagemaker/latest/dg/hyperpod.html)
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)

---

## Quick Reference Commands

```bash
# Activate environment
source ~/hyperpod-cli-env/bin/activate

# Launch training job
cd launcher/
./hyperpod_launcher.sh --recipe ../micro_pt_recipe.yaml --name my-job ...

# View job history
python3 view_jobs.py

# Monitor job
hyperpod list-jobs
hyperpod logs --name <job-name> --follow

# Check Kubernetes
kubectl get pods -n kubeflow

# Post-training workflow (scripts/)
cd scripts/

# Fetch logs
python3 fetch_logs.py --job-name <job-name> --cluster <cluster-name>

# Get MLflow URL
python3 get_mlflow_url.py --tracking-server-name <server-name>

# Deploy endpoint
python3 deploy_simple_endpoint.py --model-s3-location <s3-uri> --model-name <name>

# Verify endpoint
python3 describe-endpoint.py <endpoint-name>
```

---

**Note**: This guide assumes you have:

- AWS account with SageMaker HyperPod access
- Configured Kubernetes cluster
- ECR repository with training container
- S3 bucket for data and outputs
