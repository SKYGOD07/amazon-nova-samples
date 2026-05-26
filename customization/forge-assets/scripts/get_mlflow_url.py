#!/usr/bin/env python3
"""Utility to get presigned MLflow tracking server URL for monitoring."""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta


def get_presigned_mlflow_url(
    tracking_server_name: str,
    region: str = "us-east-1",
    expires_in_seconds: int = 300,
    session_expiration_duration_in_seconds: int = 43200
) -> dict:
    """
    Get a presigned URL for MLflow tracking server.

    Args:
        tracking_server_name: Name of the MLflow tracking server
        region: AWS region (default: us-east-1)
        expires_in_seconds: URL expiration in seconds (default: 300 = 5 minutes, max: 300)
        session_expiration_duration_in_seconds: Session duration (default: 43200 = 12 hours)

    Returns:
        dict with 'AuthorizedUrl' and 'ExpiresAt' fields
    """
    cmd = [
        "aws", "sagemaker-dev",
        "create-presigned-mlflow-tracking-server-url",
        "--tracking-server-name", tracking_server_name,
        "--region", region,
        "--expires-in-seconds", str(expires_in_seconds),
        "--session-expiration-duration-in-seconds", str(session_expiration_duration_in_seconds)
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}", file=sys.stderr)
        print(f"stderr: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}", file=sys.stderr)
        sys.exit(1)


def format_expiration(timestamp: int) -> str:
    """Format Unix timestamp to human-readable date."""
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def make_clickable_link(url: str, text: str = "Click here to open MLflow") -> str:
    """Create a clickable terminal hyperlink using ANSI escape codes."""
    # ANSI OSC 8 hyperlink format: \033]8;;URL\033\\TEXT\033]8;;\033\\
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"


def main():
    parser = argparse.ArgumentParser(
        description="Get presigned MLflow tracking server URL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get URL for default tracking server
  %(prog)s --tracking-server-name TestRigTrackingServer

  # Get URL with custom expiration (max 5 minutes)
  %(prog)s --tracking-server-name TestRigTrackingServer --expires-in-seconds 180

  # Get URL in JSON format
  %(prog)s --tracking-server-name TestRigTrackingServer --json

  # Get URL for different region
  %(prog)s --tracking-server-name TestRigTrackingServer --region us-west-2
        """
    )

    parser.add_argument(
        "--tracking-server-name",
        required=True,
        help="Name of the MLflow tracking server"
    )

    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region (default: us-east-1)"
    )

    parser.add_argument(
        "--expires-in-seconds",
        type=int,
        default=300,
        help="URL expiration in seconds (default: 300 = 5 minutes, max: 300)"
    )

    parser.add_argument(
        "--session-expiration-duration-in-seconds",
        type=int,
        default=43200,
        help="Session expiration in seconds (default: 43200 = 12 hours)"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON response"
    )

    parser.add_argument(
        "--url-only",
        action="store_true",
        help="Output only the URL (useful for scripting)"
    )

    parser.add_argument(
        "--no-hyperlink",
        action="store_true",
        help="Disable clickable hyperlink formatting"
    )

    args = parser.parse_args()

    response = get_presigned_mlflow_url(
        tracking_server_name=args.tracking_server_name,
        region=args.region,
        expires_in_seconds=args.expires_in_seconds,
        session_expiration_duration_in_seconds=args.session_expiration_duration_in_seconds
    )

    if args.json:
        print(json.dumps(response, indent=2))
    elif args.url_only:
        print(response.get("AuthorizedUrl", ""))
    else:
        print(f"MLflow Tracking Server: {args.tracking_server_name}")
        print(f"Region: {args.region}")

        url = response.get("AuthorizedUrl", "")

        if url:
            print(f"\n{'='*80}")
            if not args.no_hyperlink:
                # Output clickable hyperlink
                clickable = make_clickable_link(url)
                print(f"🔗 {clickable}")
                print(f"\n(If the link above is not clickable, copy the URL below)")

            print(f"\nPresigned URL:")
            print(url)
            print(f"{'='*80}")

        if "ExpiresAt" in response:
            expires_at = response["ExpiresAt"]
            print(f"\n⏰ Expires at: {format_expiration(expires_at)}")

            # Calculate time until expiration
            now = datetime.now().timestamp()
            time_left = expires_at - now
            if time_left > 0:
                minutes_left = time_left / 60
                print(f"⏱️  Time remaining: {minutes_left:.1f} minutes")


if __name__ == "__main__":
    main()
