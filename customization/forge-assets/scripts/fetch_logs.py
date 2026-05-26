#!/usr/bin/env python3
"""
Fetch HyperPod training job logs from CloudWatch based on job ID.

This script:
1. Finds the master node for a given job ID using kubectl
2. Locates the corresponding CloudWatch log stream
3. Fetches the last N lines of logs
"""

import argparse
import subprocess
import sys
import re
import boto3
from datetime import datetime, timedelta


def get_master_node(job_name, namespace="kubeflow"):
    """
    Get the master node ID for a given job name using kubectl.

    Args:
        job_name: Name of the training job
        namespace: Kubernetes namespace (default: kubeflow)

    Returns:
        Node instance ID (e.g., 'i-00b3d8a1bf25714e4')
    """
    try:
        # Check if kubectl is available
        check_cmd = subprocess.run(
            ['which', 'kubectl'],
            capture_output=True,
            text=True
        )

        if check_cmd.returncode != 0:
            print("Error: kubectl is not installed or not in PATH")
            print("\nTo install kubectl:")
            print("  - Amazon Linux/EC2: curl -LO https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl")
            print("  - Then: chmod +x kubectl && sudo mv kubectl /usr/local/bin/")
            print("  - Or use snap: sudo snap install kubectl --classic")
            print("\nAlternatively, if you already know the node ID, use --node-id option")
            sys.exit(1)

        # Run kubectl command to get pods
        cmd = f"kubectl get pods -o wide -n {namespace}"
        result = subprocess.run(
            cmd.split(),
            capture_output=True,
            text=True,
            check=True
        )

        # Parse output to find the job and extract node
        lines = result.stdout.strip().split('\n')
        header = lines[0]

        # Find NODE column index
        headers = header.split()
        try:
            node_idx = headers.index('NODE')
        except ValueError:
            print("Error: Could not find NODE column in kubectl output")
            sys.exit(1)

        # Find the master pod for this job
        master_node = None
        for line in lines[1:]:
            if job_name in line and 'master' in line.lower():
                # Extract instance ID directly from the line using regex
                # Format: hyperpod-i-xxxxxxxxxxxx
                match = re.search(r'hyperpod-(i-[a-f0-9]+)', line)
                if match:
                    master_node = match.group(1)
                    print(f"Found master node: {master_node}")
                    break

        if not master_node:
            print(f"Error: Could not find master node for job '{job_name}'")
            print(f"\nAvailable pods in namespace '{namespace}':")
            for line in lines[1:]:
                if job_name in line:
                    print(f"  {line}")
            sys.exit(1)

        return master_node

    except subprocess.CalledProcessError as e:
        print(f"Error running kubectl: {e}")
        print(f"stderr: {e.stderr}")
        sys.exit(1)


def fetch_cloudwatch_logs(cluster_name, node_id, num_lines=100, region='us-east-1'):
    """
    Fetch logs from CloudWatch for the given node.

    Args:
        cluster_name: Name of the HyperPod cluster (e.g., 'my-hyperpod-rig')
        node_id: Node instance ID (e.g., 'i-00b3d8a1bf25714e4')
        num_lines: Number of recent lines to fetch
        region: AWS region

    Returns:
        List of log lines
    """
    try:
        client = boto3.client('logs', region_name=region)

        # Get log groups matching the pattern
        log_group_prefix = f'/aws/sagemaker/Clusters/{cluster_name}'

        print(f"Searching for log groups with prefix: {log_group_prefix}")

        # List log groups
        response = client.describe_log_groups(
            logGroupNamePrefix=log_group_prefix
        )

        if not response['logGroups']:
            print(f"Error: No log groups found with prefix '{log_group_prefix}'")
            sys.exit(1)

        log_group_name = response['logGroups'][0]['logGroupName']
        print(f"Using log group: {log_group_name}")

        # Find log stream for this node
        # Search for just the node ID (e.g., i-09b8ad93b3d07e149)
        log_stream_pattern = node_id

        print(f"Searching for log stream containing: {log_stream_pattern}")

        # List log streams - paginate through all to find the target
        target_stream = None
        next_token = None
        streams_checked = 0

        while target_stream is None:
            params = {
                'logGroupName': log_group_name,
                'orderBy': 'LastEventTime',
                'descending': True,
                'limit': 50
            }
            if next_token:
                params['nextToken'] = next_token

            streams_response = client.describe_log_streams(**params)

            for stream in streams_response['logStreams']:
                streams_checked += 1
                if log_stream_pattern in stream['logStreamName']:
                    target_stream = stream['logStreamName']
                    print(f"Found log stream: {target_stream} (checked {streams_checked} streams)")
                    break

            # Check if we need to paginate
            if 'nextToken' in streams_response and target_stream is None:
                next_token = streams_response['nextToken']
                print(f"Checked {streams_checked} streams, paginating...")
            else:
                break

        if not target_stream:
            print(f"Error: Could not find log stream for node '{node_id}' after checking {streams_checked} streams")
            print("\nRecent log streams (sample):")
            # Re-fetch first page to show samples
            streams_response = client.describe_log_streams(
                logGroupName=log_group_name,
                orderBy='LastEventTime',
                descending=True,
                limit=10
            )
            for stream in streams_response['logStreams']:
                print(f"  {stream['logStreamName']}")
            sys.exit(1)

        # Fetch log events
        print(f"\nFetching last {num_lines} lines...")

        # Get logs from the last 7 days (increased window for more logs)
        start_time = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)

        # AWS CloudWatch has a max limit of 10,000 per request
        MAX_LIMIT = 10000

        events = []
        prev_token = None

        # Fetch in batches
        while len(events) < num_lines:
            # Calculate how many more events we need
            remaining = num_lines - len(events)
            batch_limit = min(remaining, MAX_LIMIT)

            params = {
                'logGroupName': log_group_name,
                'logStreamName': target_stream,
                'startTime': start_time,
                'limit': batch_limit,
                'startFromHead': False
            }

            if prev_token:
                params['nextToken'] = prev_token

            events_response = client.get_log_events(**params)
            new_events = events_response['events']

            if not new_events:
                print(f"No more events available (fetched {len(events)} total)")
                break

            # Check if we're getting the same token (no more events)
            current_token = events_response.get('nextBackwardToken')
            if current_token == prev_token:
                print(f"Reached end of log stream (fetched {len(events)} total)")
                break

            # Add new events to the beginning (we're going backwards)
            events = new_events + events
            prev_token = current_token

            print(f"Fetched {len(new_events)} events (total: {len(events)}/{num_lines})")

        # Return last N lines
        return events[-num_lines:] if len(events) > num_lines else events

    except Exception as e:
        print(f"Error fetching CloudWatch logs: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Fetch HyperPod training job logs from CloudWatch',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  # Using job name (requires kubectl)
  python fetch_logs.py --job-name my-training-job --cluster my-hyperpod-rig
  python fetch_logs.py --job-name my-training-job --cluster my-hyperpod-rig --lines 500

  # Using node ID directly (skips kubectl)
  python fetch_logs.py --node-id i-00b3d8a1bf25714e4 --cluster my-hyperpod-rig

  # With custom region and output file
  python fetch_logs.py --node-id i-00b3d8a1bf25714e4 --cluster my-hyperpod-rig --region us-west-2 --output logs.txt
        """
    )

    parser.add_argument(
        '--job-name',
        help='Name of the training job (used to find the pod in kubectl)'
    )

    parser.add_argument(
        '--node-id',
        help='Node instance ID (e.g., i-00b3d8a1bf25714e4) - skips kubectl lookup if provided'
    )

    parser.add_argument(
        '--cluster',
        required=True,
        help='Name of the HyperPod cluster (e.g., my-hyperpod-rig)'
    )

    parser.add_argument(
        '--lines',
        type=int,
        default=100,
        help='Number of recent log lines to fetch (default: 100)'
    )

    parser.add_argument(
        '--namespace',
        default='kubeflow',
        help='Kubernetes namespace (default: kubeflow)'
    )

    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )

    parser.add_argument(
        '--output',
        help='Output file path (optional, prints to stdout if not specified)'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.node_id and not args.job_name:
        parser.error("Either --job-name or --node-id must be specified")

    print(f"Cluster: {args.cluster}")
    if args.job_name:
        print(f"Job name: {args.job_name}")
    if args.node_id:
        print(f"Node ID: {args.node_id}")
    print(f"=" * 80)

    # Step 1: Get master node ID (if not provided directly)
    if args.node_id:
        node_id = args.node_id
        print(f"Using provided node ID: {node_id}")
    else:
        node_id = get_master_node(args.job_name, args.namespace)

    print("=" * 80)

    # Step 2: Fetch logs from CloudWatch
    events = fetch_cloudwatch_logs(args.cluster, node_id, args.lines, args.region)

    print("=" * 80)
    print(f"\nLogs ({len(events)} lines):\n")

    # Format and output logs
    output_lines = []
    for event in events:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        log_line = f"[{timestamp.isoformat()}] {event['message']}"
        output_lines.append(log_line)

        if not args.output:
            print(log_line)

    # Write to file if specified
    if args.output:
        with open(args.output, 'w') as f:
            f.write('\n'.join(output_lines))
        print(f"\nLogs written to: {args.output}")

    print(f"\n{'=' * 80}")
    print(f"Successfully fetched {len(events)} log lines")


if __name__ == '__main__':
    main()
