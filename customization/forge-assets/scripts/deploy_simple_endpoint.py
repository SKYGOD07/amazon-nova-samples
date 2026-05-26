#!/usr/bin/env python3
"""
Deploy a simple SageMaker endpoint (without inference components).

This script follows the traditional 3-step deployment:
1. Create Model
2. Create Endpoint Config
3. Create Endpoint

Usage:
    python deploy_simple_endpoint.py \
        --model-s3-location s3://bucket/path/to/model/ \
        --model-name my-model \
        --instance-type ml.p5.48xlarge \
        --region us-east-1
"""

import argparse
import time
import boto3
from botocore.exceptions import ClientError

# =============================================================================
# Defaults
# =============================================================================

DEFAULT_REGION = "us-west-2"
DEFAULT_IMAGE = "145107590327.dkr.ecr.us-west-2.amazonaws.com/nova-inference-repo:v1.5"
DEFAULT_INSTANCE_TYPE = "ml.p5.48xlarge"

# =============================================================================
# Helper Functions
# =============================================================================

def get_account_id():
    """Get AWS account ID from current session."""
    try:
        sts_client = boto3.client('sts')
        return sts_client.get_caller_identity()['Account']
    except Exception as e:
        print(f"❌ Error getting AWS account ID: {e}")
        print("   Make sure AWS credentials are configured")
        return None


def get_execution_role_arn(account_id, role_name="SageMakerExecutionRole"):
    """Get the SageMaker execution role ARN."""
    return f"arn:aws:iam::{account_id}:role/{role_name}"

def wait_for_endpoint(client, endpoint_name, poll_interval=30, timeout=1800):
    """Wait for endpoint to reach InService status."""
    print(f"\n⏳ Waiting for endpoint '{endpoint_name}' to be InService...")
    print("This typically takes 15-30 minutes...\n")

    start_time = time.time()
    while True:
        if time.time() - start_time > timeout:
            print(f"❌ Timeout after {timeout}s")
            return False

        try:
            response = client.describe_endpoint(EndpointName=endpoint_name)
            status = response['EndpointStatus']
            elapsed = int(time.time() - start_time)

            if status == 'Creating':
                print(f"[{elapsed}s] Status: {status} - Provisioning infrastructure and loading model...")
            elif status == 'InService':
                print(f"[{elapsed}s] Status: {status}")
                print(f"\n✅ Endpoint '{endpoint_name}' is ready!")
                print(f"   Total time: {elapsed}s ({elapsed//60} minutes)")
                print(f"   Endpoint ARN: {response['EndpointArn']}")
                return True
            elif status == 'Failed':
                print(f"[{elapsed}s] Status: {status}")
                print(f"❌ Failure Reason: {response.get('FailureReason', 'Unknown')}")
                return False
            else:
                print(f"[{elapsed}s] Status: {status}")

        except Exception as e:
            print(f"❌ Error checking endpoint status: {e}")
            return False

        time.sleep(poll_interval)

def endpoint_exists(client, endpoint_name):
    """Check if an endpoint exists and return its status."""
    try:
        response = client.describe_endpoint(EndpointName=endpoint_name)
        return response['EndpointStatus']
    except ClientError as e:
        if e.response['Error']['Code'] in ('ValidationException', 'UnknownOperationException'):
            return None
        raise

# =============================================================================
# Main Deployment Function
# =============================================================================

def fake_demo_deployment(model_name):
    """Fake deployment for demo purposes."""
    endpoint_name = f"{model_name}-Endpoint"

    print("="*80)
    print("🚀 SageMaker Simple Endpoint Deployment (DEMO MODE)")
    print("="*80)
    print(f"Model Name:         {model_name}-MODEL")
    print(f"Endpoint Config:    {model_name}-CONFIG")
    print(f"Endpoint Name:      {endpoint_name}")
    print(f"Region:             us-west-2")
    print("="*80)

    print("\n" + "="*80)
    print("STEP 1: Create SageMaker Model")
    print("="*80)
    print(f"Creating model '{model_name}-MODEL'...")
    time.sleep(0.5)
    print(f"✅ Model created successfully!")

    print("\n" + "="*80)
    print("STEP 2: Create Endpoint Configuration")
    print("="*80)
    print(f"Creating endpoint config '{model_name}-CONFIG'...")
    time.sleep(0.5)
    print(f"✅ Endpoint config created successfully!")

    print("\n" + "="*80)
    print("STEP 3: Create Endpoint")
    print("="*80)
    print(f"Creating endpoint '{endpoint_name}'...")
    time.sleep(0.5)
    print(f"✅ Endpoint creation initiated!")

    print("\n⏳ Waiting for endpoint to be InService...")
    time.sleep(1)
    print("✅ Endpoint is ready!")

    print("\n" + "="*80)
    print("[SageMaker Deployment Done] Endpoint Name: " + endpoint_name)
    print("="*80)

    return 0

def main():
    parser = argparse.ArgumentParser(
        description="Deploy a simple SageMaker endpoint (no inference components)"
    )
    parser.add_argument(
        "--model-s3-location", required=True,
        help="S3 URI of the model artifacts (e.g. s3://bucket/path/to/model/)"
    )
    parser.add_argument(
        "--model-name", required=True,
        help="Name for the model, endpoint config, and endpoint"
    )
    parser.add_argument(
        "--instance-type", default=DEFAULT_INSTANCE_TYPE,
        help=f"Instance type (default: {DEFAULT_INSTANCE_TYPE})"
    )
    parser.add_argument(
        "--region", default=DEFAULT_REGION,
        help=f"AWS region (default: {DEFAULT_REGION})"
    )
    parser.add_argument(
        "--account-id",
        help="AWS account ID (auto-detected if not provided)"
    )
    parser.add_argument(
        "--execution-role",
        help="SageMaker execution role ARN (auto-constructed if not provided)"
    )
    parser.add_argument(
        "--image", default=DEFAULT_IMAGE,
        help="Container image URI"
    )
    parser.add_argument(
        "--context-length", default="8000",
        help="Context length (default: 8000)"
    )
    parser.add_argument(
        "--max-concurrency", default="2",
        help="Max concurrency (default: 2)"
    )
    parser.add_argument(
        "--quantization", default="fp8",
        help="Quantization dtype (default: fp8)"
    )
    parser.add_argument(
        "--enable-rai", action="store_true",
        help="Enable RAI (default: disabled)"
    )
    parser.add_argument(
        "--poll-interval", type=int, default=30,
        help="Seconds between status polls (default: 30)"
    )
    parser.add_argument(
        "--skip-wait", action="store_true",
        help="Don't wait for endpoint to be InService"
    )
    parser.add_argument(
        "--demo-mode", action="store_true",
        help="Demo mode - fake deployment for demo purposes"
    )

    args = parser.parse_args()

    # Construct names
    model_name = f"{args.model_name}-MODEL"
    endpoint_config_name = f"{args.model_name}-CONFIG"
    endpoint_name = f"{args.model_name}-Endpoint"

    # Demo mode - fake deployment and exit early
    if args.demo_mode:
        return fake_demo_deployment(args.model_name)

    # Get AWS account ID if not provided
    if args.account_id:
        account_id = args.account_id
    else:
        account_id = get_account_id()
        if not account_id:
            return 1

    # Get execution role ARN
    if args.execution_role:
        execution_role_arn = args.execution_role
    else:
        execution_role_arn = get_execution_role_arn(account_id)

    # Environment variables for the container
    environment = {
        "CONTEXT_LENGTH": args.context_length,
        "MAX_CONCURRENCY": args.max_concurrency,
        "ENABLE_TOOL_CALLING": "true",
        "ENABLE_RAI": "true" if args.enable_rai else "false",
        "QUANTIZATION_DTYPE": args.quantization,
        "DISABLE_CONFIG_VALIDATION": "true"
    }

    print("="*80)
    print("🚀 SageMaker Simple Endpoint Deployment")
    print("="*80)
    print(f"Model Name:         {model_name}")
    print(f"Endpoint Config:    {endpoint_config_name}")
    print(f"Endpoint Name:      {endpoint_name}")
    print(f"Model S3 Location:  {args.model_s3_location}")
    print(f"Instance Type:      {args.instance_type}")
    print(f"Region:             {args.region}")
    print(f"Account ID:         {account_id}")
    print(f"Container Image:    {args.image}")
    print(f"Execution Role:     {execution_role_arn}")
    print("="*80)

    # Create SageMaker client (using standard AWS credentials)
    client = boto3.client('sagemaker', region_name=args.region)

    # ── Step 1: Create Model ─────────────────────────────────────────────
    print("\n" + "="*80)
    print("STEP 1: Create SageMaker Model")
    print("="*80)

    print(f"Creating model '{model_name}'...")
    try:
        model_response = client.create_model(
            ModelName=model_name,
            PrimaryContainer={
                'Image': args.image,
                'ModelDataSource': {
                    'S3DataSource': {
                        'S3Uri': args.model_s3_location,
                        'S3DataType': 'S3Prefix',
                        'CompressionType': 'None'
                    }
                },
                'Environment': environment
            },
            ExecutionRoleArn=execution_role_arn,
            EnableNetworkIsolation=True
        )
        print(f"✅ Model created successfully!")
        print(f"   Model ARN: {model_response['ModelArn']}")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        if 'already exists' in error_message.lower() or error_code == 'ResourceInUse':
            print(f"✓ Model '{model_name}' already exists, continuing...")
        else:
            print(f"❌ Error creating model: {e}")
            return 1
    except Exception as e:
        print(f"❌ Error creating model: {e}")
        return 1

    # ── Step 2: Create Endpoint Config ───────────────────────────────────
    print("\n" + "="*80)
    print("STEP 2: Create Endpoint Configuration")
    print("="*80)

    print(f"Creating endpoint config '{endpoint_config_name}'...")
    try:
        config_response = client.create_endpoint_config(
            EndpointConfigName=endpoint_config_name,
            ProductionVariants=[{
                'VariantName': 'primary',
                'ModelName': model_name,
                'InitialInstanceCount': 1,
                'InstanceType': args.instance_type,
            }]
        )
        print(f"✅ Endpoint config created successfully!")
        print(f"   Config ARN: {config_response['EndpointConfigArn']}")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        if 'already exists' in error_message.lower() or error_code == 'ResourceInUse':
            print(f"✓ Endpoint config '{endpoint_config_name}' already exists, continuing...")
        else:
            print(f"❌ Error creating endpoint config: {e}")
            return 1
    except Exception as e:
        print(f"❌ Error creating endpoint config: {e}")
        return 1

    # ── Step 3: Create Endpoint ──────────────────────────────────────────
    print("\n" + "="*80)
    print("STEP 3: Create Endpoint")
    print("="*80)

    status = endpoint_exists(client, endpoint_name)
    if status == 'InService':
        print(f"✓ Endpoint '{endpoint_name}' already exists and is InService.")
    elif status is not None:
        print(f"⏳ Endpoint '{endpoint_name}' exists with status: {status}")
        if not args.skip_wait:
            print("   Waiting for it to be ready...")
            if not wait_for_endpoint(client, endpoint_name, args.poll_interval):
                return 1
    else:
        print(f"Creating endpoint '{endpoint_name}'...")
        try:
            endpoint_response = client.create_endpoint(
                EndpointName=endpoint_name,
                EndpointConfigName=endpoint_config_name
            )
            print(f"✅ Endpoint creation initiated!")
            print(f"   Endpoint ARN: {endpoint_response['EndpointArn']}")

            if not args.skip_wait:
                if not wait_for_endpoint(client, endpoint_name, args.poll_interval):
                    return 1
            else:
                print("\n⏭️  Skipping wait (--skip-wait flag set)")
                print(f"   Run: aws sagemaker describe-endpoint --endpoint-name {endpoint_name}")

        except Exception as e:
            print(f"❌ Error creating endpoint: {e}")
            return 1

    # ── Success ──────────────────────────────────────────────────────────
    print("\n" + "="*80)
    print("[SageMaker Deployment Done] Endpoint Name: " + endpoint_name)
    print("="*80)

    return 0

if __name__ == "__main__":
    exit(main())
