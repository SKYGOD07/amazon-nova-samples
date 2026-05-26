#!/usr/bin/env python3
"""Get detailed information about a specific SageMaker endpoint."""

import argparse
import sys
import boto3
from botocore.exceptions import ClientError

DEFAULT_REGION = "us-west-2"


def main():
    parser = argparse.ArgumentParser(
        description="Get detailed information about a SageMaker endpoint"
    )
    parser.add_argument(
        "endpoint_name",
        help="Name of the SageMaker endpoint"
    )
    parser.add_argument(
        "--region",
        default=DEFAULT_REGION,
        help=f"AWS region (default: {DEFAULT_REGION})"
    )
    parser.add_argument(
        "--profile",
        help="AWS profile to use (optional)"
    )

    args = parser.parse_args()

    # Create boto3 session with optional profile
    session_kwargs = {'region_name': args.region}
    if args.profile:
        session_kwargs['profile_name'] = args.profile

    session = boto3.Session(**session_kwargs)
    client = session.client('sagemaker')

    print(f"Endpoint: {args.endpoint_name}")
    print(f"Region: {args.region}")
    if args.profile:
        print(f"Profile: {args.profile}")
    print()

    # Describe endpoint
    try:
        endpoint = client.describe_endpoint(EndpointName=args.endpoint_name)
        print(f"Status: {endpoint['EndpointStatus']}")
        print(f"ARN: {endpoint['EndpointArn']}")
        print(f"Config: {endpoint['EndpointConfigName']}")
        print(f"Created: {endpoint['CreationTime']}")
        print(f"Modified: {endpoint['LastModifiedTime']}")
        print()

        # Get endpoint config
        config_name = endpoint['EndpointConfigName']
        try:
            config = client.describe_endpoint_config(EndpointConfigName=config_name)
            print("Production Variants:")
            for variant in config['ProductionVariants']:
                print(f"  - Variant: {variant.get('VariantName', 'N/A')}")
                print(f"    Instance Type: {variant.get('InstanceType', 'N/A')}")
                print(f"    Initial Instance Count: {variant.get('InitialInstanceCount', 'N/A')}")
                if 'ModelName' in variant:
                    print(f"    Model: {variant['ModelName']}")
                print()
        except ClientError as e:
            print(f"⚠️  Could not describe endpoint config: {e.response['Error']['Message']}\n")

        # Check for inference components
        try:
            ic_response = client.list_inference_components(
                EndpointNameEquals=args.endpoint_name,
                MaxResults=50
            )
            if ic_response.get('InferenceComponents'):
                print("Inference Components:")
                for ic_summary in ic_response['InferenceComponents']:
                    ic_name = ic_summary['InferenceComponentName']
                    print(f"  - {ic_name}")

                    # Get detailed info
                    try:
                        ic_detail = client.describe_inference_component(InferenceComponentName=ic_name)
                        spec = ic_detail.get('Specification', {})
                        compute = spec.get('ComputeResourceRequirements', {})

                        print(f"    Status: {ic_detail['InferenceComponentStatus']}")
                        print(f"    Model: {spec.get('ModelName', 'N/A')}")
                        print(f"    Min Memory (MB): {compute.get('MinMemoryRequiredInMb', 'N/A')}")
                        print(f"    Number of Accelerators: {compute.get('NumberOfAcceleratorDevicesRequired', 'N/A')}")

                        # Runtime config
                        runtime = ic_detail.get('RuntimeConfig', {})
                        print(f"    Copies: {runtime.get('CopyCount', 'N/A')}")
                        print()
                    except Exception as e:
                        print(f"    (Could not get details: {e})")
                        print()
        except Exception as e:
            print(f"Note: Could not check inference components: {e}\n")

    except ClientError as e:
        print(f"❌ Error: {e.response['Error']['Message']}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
