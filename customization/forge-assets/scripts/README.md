# Scripts Directory

Utility scripts for managing SageMaker endpoints and monitoring training jobs.

## Overview

This directory contains four key scripts that work together for the complete workflow:

1. **Fetch Logs** - Get CloudWatch logs from HyperPod training jobs
2. **Deploy Endpoint** - Deploy a SageMaker endpoint for your trained model
3. **Describe Endpoint** - Get detailed information about a deployed endpoint
4. **Get MLflow URL** - Access the MLflow tracking server for monitoring experiments

---

## 1. Fetch Logs (`fetch_logs.py`)

Fetch HyperPod training job logs from CloudWatch based on job ID or node ID.

### Purpose
After launching a training job, use this to retrieve logs from CloudWatch for debugging and monitoring.

### Prerequisites
- AWS credentials configured
- kubectl installed (optional, if using `--job-name`)
- Training job running on HyperPod cluster

### Usage

#### Option A: Using Job Name (requires kubectl)
```bash
python3 fetch_logs.py \
    --job-name my-training-job-a0yrv \
    --cluster my-hyperpod-rig \
    --lines 500
```

#### Option B: Using Node ID (skips kubectl)
```bash
python3 fetch_logs.py \
    --node-id i-00b3d8a1bf25714e4 \
    --cluster my-hyperpod-rig \
    --lines 500
```

#### With Custom Region and Output File
```bash
python3 fetch_logs.py \
    --node-id i-00b3d8a1bf25714e4 \
    --cluster my-hyperpod-rig \
    --region us-west-2 \
    --output training_logs.txt
```

### Arguments

| Argument | Required | Description | Default |
|----------|----------|-------------|---------|
| `--job-name` | Either this or `--node-id` | Name of the training job | - |
| `--node-id` | Either this or `--job-name` | Node instance ID (e.g., `i-00b3d8a1bf25714e4`) | - |
| `--cluster` | Yes | Name of the HyperPod cluster | - |
| `--lines` | No | Number of recent log lines to fetch | 100 |
| `--namespace` | No | Kubernetes namespace | kubeflow |
| `--region` | No | AWS region | us-east-1 |
| `--output` | No | Output file path (prints to stdout if not specified) | - |

### Example Output
```
Cluster: my-hyperpod-rig
Job name: my-training-job-a0yrv
================================================================================
Found master node: i-00b3d8a1bf25714e4
================================================================================
Using log group: /aws/sagemaker/Clusters/my-hyperpod-rig
Found log stream: i-00b3d8a1bf25714e4

Fetching last 100 lines...

Logs (100 lines):

[2026-05-22T14:23:15.123456] Step 100: loss=2.456
[2026-05-22T14:23:20.234567] Step 101: loss=2.423
...
```

---

## 2. Deploy Endpoint (`deploy_simple_endpoint.py`)

Deploy a SageMaker endpoint using the traditional 3-step deployment process.

### Purpose
After training completes, use this to deploy your model as a SageMaker endpoint for inference.

### Prerequisites
- Trained model artifacts stored in S3
- AWS credentials with SageMaker permissions
- ECR container image for inference

### Usage

#### Standard Deployment
```bash
python3 deploy_simple_endpoint.py \
    --model-s3-location s3://my-bucket/models/my-trained-model/ \
    --model-name my-nova-model \
    --instance-type ml.p5.48xlarge \
    --region us-west-2
```

#### With Custom Configuration
```bash
python3 deploy_simple_endpoint.py \
    --model-s3-location s3://my-bucket/models/my-trained-model/ \
    --model-name my-nova-model \
    --instance-type ml.p5.48xlarge \
    --region us-west-2 \
    --context-length 16000 \
    --max-concurrency 4 \
    --quantization fp8 \
    --enable-rai
```

#### Demo Mode (for testing)
```bash
python3 deploy_simple_endpoint.py \
    --model-s3-location s3://dummy/path/ \
    --model-name test-model \
    --demo-mode
```

### Arguments

| Argument | Required | Description | Default |
|----------|----------|-------------|---------|
| `--model-s3-location` | Yes | S3 URI of model artifacts | - |
| `--model-name` | Yes | Name for model, config, and endpoint | - |
| `--instance-type` | No | Instance type for deployment | ml.p5.48xlarge |
| `--region` | No | AWS region | us-west-2 |
| `--account-id` | No | AWS account ID (auto-detected if not provided) | Auto-detected |
| `--execution-role` | No | SageMaker execution role ARN | Auto-constructed |
| `--image` | No | Container image URI | Default Nova inference image |
| `--context-length` | No | Model context length | 8000 |
| `--max-concurrency` | No | Maximum concurrent requests | 2 |
| `--quantization` | No | Quantization dtype | fp8 |
| `--enable-rai` | No | Enable RAI (Responsible AI) | False |
| `--poll-interval` | No | Seconds between status polls | 30 |
| `--skip-wait` | No | Don't wait for endpoint to be InService | False |
| `--demo-mode` | No | Fake deployment for testing | False |

### Deployment Process

The script follows three steps:

1. **Create Model** - Register model artifacts and container image
2. **Create Endpoint Config** - Define instance type and variant settings
3. **Create Endpoint** - Launch the inference endpoint

### Example Output
```
================================================================================
🚀 SageMaker Simple Endpoint Deployment
================================================================================
Model Name:         my-nova-model-MODEL
Endpoint Config:    my-nova-model-CONFIG
Endpoint Name:      my-nova-model-Endpoint
Model S3 Location:  s3://my-bucket/models/my-trained-model/
Instance Type:      ml.p5.48xlarge
Region:             us-west-2
Account ID:         123456789012
Container Image:    145107590327.dkr.ecr.us-west-2.amazonaws.com/nova-inference-repo:v1.5
Execution Role:     arn:aws:iam::123456789012:role/SageMakerExecutionRole
================================================================================

================================================================================
STEP 1: Create SageMaker Model
================================================================================
Creating model 'my-nova-model-MODEL'...
✅ Model created successfully!
   Model ARN: arn:aws:sagemaker:us-west-2:123456789012:model/my-nova-model-MODEL

================================================================================
STEP 2: Create Endpoint Configuration
================================================================================
Creating endpoint config 'my-nova-model-CONFIG'...
✅ Endpoint config created successfully!
   Config ARN: arn:aws:sagemaker:us-west-2:123456789012:endpoint-config/my-nova-model-CONFIG

================================================================================
STEP 3: Create Endpoint
================================================================================
Creating endpoint 'my-nova-model-Endpoint'...
✅ Endpoint creation initiated!
   Endpoint ARN: arn:aws:sagemaker:us-west-2:123456789012:endpoint/my-nova-model-Endpoint

⏳ Waiting for endpoint 'my-nova-model-Endpoint' to be InService...
This typically takes 15-30 minutes...

[180s] Status: Creating - Provisioning infrastructure and loading model...
[360s] Status: Creating - Provisioning infrastructure and loading model...
[540s] Status: InService

✅ Endpoint 'my-nova-model-Endpoint' is ready!
   Total time: 540s (9 minutes)

================================================================================
[SageMaker Deployment Done] Endpoint Name: my-nova-model-Endpoint
================================================================================
```

---

## 3. Describe Endpoint (`describe-endpoint.py`)

Get detailed information about a specific SageMaker endpoint.

### Purpose
After deploying an endpoint, use this to verify its configuration and status.

### Prerequisites
- AWS credentials configured
- Deployed SageMaker endpoint

### Usage

```bash
# Basic usage
python3 describe-endpoint.py my-nova-model-Endpoint

# With custom region
python3 describe-endpoint.py my-nova-model-Endpoint --region us-east-1

# With specific AWS profile
python3 describe-endpoint.py my-nova-model-Endpoint --profile production
```

### Arguments

| Argument | Required | Description | Default |
|----------|----------|-------------|---------|
| `endpoint-name` | Yes | Name of the endpoint (positional argument) | - |
| `--region` | No | AWS region | us-west-2 |
| `--profile` | No | AWS profile to use | Default profile |

### Example Output
```
Endpoint: my-nova-model-Endpoint
Region: us-west-2

Status: InService
ARN: arn:aws:sagemaker:us-west-2:123456789012:endpoint/my-nova-model-Endpoint
Config: my-nova-model-CONFIG
Created: 2026-05-26 14:30:45.123456+00:00
Modified: 2026-05-26 14:39:12.654321+00:00

Production Variants:
  - Variant: primary
    Instance Type: ml.p5.48xlarge
    Initial Instance Count: 1
    Model: my-nova-model-MODEL
```

---

## 4. Get MLflow URL (`get_mlflow_url.py`)

Get a presigned URL for accessing the MLflow tracking server.

### Purpose
Access the MLflow tracking server to view training metrics, experiments, and model artifacts.

### Prerequisites
- AWS credentials configured
- MLflow tracking server deployed in SageMaker

### Usage

#### Basic Usage
```bash
python3 get_mlflow_url.py --tracking-server-name TestRigTrackingServer
```

#### Custom Expiration (max 5 minutes)
```bash
python3 get_mlflow_url.py \
    --tracking-server-name TestRigTrackingServer \
    --expires-in-seconds 180
```

#### JSON Output
```bash
python3 get_mlflow_url.py \
    --tracking-server-name TestRigTrackingServer \
    --json
```

#### URL Only (for scripting)
```bash
python3 get_mlflow_url.py \
    --tracking-server-name TestRigTrackingServer \
    --url-only
```

### Arguments

| Argument | Required | Description | Default |
|----------|----------|-------------|---------|
| `--tracking-server-name` | Yes | Name of the MLflow tracking server | - |
| `--region` | No | AWS region | us-east-1 |
| `--expires-in-seconds` | No | URL expiration in seconds (max: 300) | 300 |
| `--session-expiration-duration-in-seconds` | No | Session expiration in seconds | 43200 (12 hours) |
| `--json` | No | Output raw JSON response | False |
| `--url-only` | No | Output only the URL | False |
| `--no-hyperlink` | No | Disable clickable hyperlink formatting | False |

### Example Output
```
MLflow Tracking Server: TestRigTrackingServer
Region: us-east-1

================================================================================
🔗 Click here to open MLflow

(If the link above is not clickable, copy the URL below)

Presigned URL:
https://mlflow-tracking-server.us-east-1.sagemaker.aws/...?AWSAccessKeyId=...
================================================================================

⏰ Expires at: 2026-05-22 14:45:00
⏱️  Time remaining: 5.0 minutes
```

---

## Complete Workflow Example

Here's how to use all four scripts in sequence for a typical ML workflow:

### Step 1: Monitor Training Job
```bash
# Get logs from your running training job
python3 fetch_logs.py \
    --job-name my-training-job-a0yrv \
    --cluster my-hyperpod-rig \
    --lines 1000 \
    --output training_logs.txt
```

### Step 2: Check Training Progress in MLflow
```bash
# Get MLflow URL to view metrics
python3 get_mlflow_url.py \
    --tracking-server-name TestRigTrackingServer
# Open the URL in your browser to view training metrics
```

### Step 3: Deploy Trained Model
```bash
# Once training completes, deploy the model
python3 deploy_simple_endpoint.py \
    --model-s3-location s3://my-bucket/output/my-training-job-a0yrv/model/ \
    --model-name my-nova-model \
    --instance-type ml.p5.48xlarge \
    --region us-west-2
```

### Step 4: Verify Endpoint Deployment
```bash
# Verify the endpoint is ready
python3 describe-endpoint.py my-nova-model-Endpoint
```

---

## Troubleshooting

### Fetch Logs

**Error: kubectl not found**
- Install kubectl or use `--node-id` instead of `--job-name`
- Installation: `curl -LO https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl`

**Error: Could not find log stream**
- Verify the cluster name is correct
- Check that the job is running and producing logs
- Verify you have CloudWatch read permissions

### Deploy Endpoint

**Error: Credentials not found**
- Ensure AWS credentials are configured: `aws configure`
- Or use AWS_PROFILE environment variable: `export AWS_PROFILE=your-profile`
- Check credentials: `aws sts get-caller-identity`

**Error: Endpoint creation failed**
- Check that the S3 model path exists and is accessible
- Verify the instance type is available in your region
- Check SageMaker service limits/quotas

**Endpoint stuck in Creating**
- This is normal - endpoints take 15-30 minutes to deploy
- Use `--skip-wait` to launch deployment and check back later

### Describe Endpoint

**Error: Endpoint not found**
- Verify the endpoint name is correct
- Check that the endpoint exists: `aws sagemaker list-endpoints`

### Get MLflow URL

**Error: aws: command not found**
- Install AWS CLI v2
- Ensure aws-sagemaker-dev plugin is installed

**Error: Tracking server not found**
- Verify the tracking server name is correct
- Check the region matches where the server was created

---

## Additional Notes

### Credential Management
- Scripts use standard AWS credentials from your environment
- Configure credentials with `aws configure` or use AWS_PROFILE
- Ensure you have the correct IAM permissions for SageMaker operations
- Account ID is auto-detected from your AWS credentials

### Default Configuration
- Default region: us-west-2 (us-east-1 for MLflow)
- Default instance type: ml.p5.48xlarge
- Default container image: Nova inference image v1.5
- Execution role: Auto-constructed as `SageMakerExecutionRole` (can be overridden)

---

## Quick Reference

```bash
# 1. Fetch logs
python3 fetch_logs.py --job-name <job-name> --cluster <cluster-name>

# 2. Get MLflow URL
python3 get_mlflow_url.py --tracking-server-name <server-name>

# 3. Deploy endpoint
python3 deploy_simple_endpoint.py --model-s3-location <s3-uri> --model-name <name>

# 4. Check endpoint
python3 describe-endpoint.py <endpoint-name>
```
