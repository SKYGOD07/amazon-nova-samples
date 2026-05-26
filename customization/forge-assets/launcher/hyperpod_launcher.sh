#!/bin/bash
# Simple HyperPod Job Launcher Script

set -e

# Default values
NAMESPACE="kubeflow"
INSTANCE_TYPE="ml.p5.48xlarge"
DRY_RUN=false
LOGS_DIR="../logs"
NO_LOGS=false

# Usage function
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Required:
  --recipe PATH           Path to recipe YAML file
  --name NAME            Job name
  --data S3_PATH         S3 path to training data
  --output S3_PATH       S3 path for output
  --container URI        Container image URI

Optional:
  --val S3_PATH          S3 path to validation data
  --model-path S3_PATH   S3 path to model checkpoint (for evaluation)
  --mlflow URI           MLflow tracking URI
  --instance-type TYPE   Instance type (default: ml.p5.48xlarge)
  --namespace NS         Kubernetes namespace (default: kubeflow)
  --logs-dir DIR         Directory to save logs (default: ../logs)
  --no-logs              Disable logging
  --dry-run              Print command without executing

Example:
  $0 \\
    --recipe micro_pt_recipe.yaml \\
    --name my-training-job \\
    --data s3://bucket/train.jsonl \\
    --val s3://bucket/val.jsonl \\
    --output s3://bucket/output/ \\
    --mlflow arn:aws:sagemaker:region:account:mlflow-app/app-ID \\
    --container 123456.dkr.ecr.us-east-1.amazonaws.com/repo:tag
EOF
    exit 1
}

# Parse arguments
RECIPE=""
NAME=""
DATA=""
VAL=""
OUTPUT=""
MODEL_PATH=""
MLFLOW=""
CONTAINER=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --recipe) RECIPE="$2"; shift 2 ;;
        --name) NAME="$2"; shift 2 ;;
        --data) DATA="$2"; shift 2 ;;
        --val) VAL="$2"; shift 2 ;;
        --output) OUTPUT="$2"; shift 2 ;;
        --model-path|--model_name_or_path) MODEL_PATH="$2"; shift 2 ;;
        --mlflow) MLFLOW="$2"; shift 2 ;;
        --container) CONTAINER="$2"; shift 2 ;;
        --instance-type) INSTANCE_TYPE="$2"; shift 2 ;;
        --namespace) NAMESPACE="$2"; shift 2 ;;
        --logs-dir) LOGS_DIR="$2"; shift 2 ;;
        --no-logs) NO_LOGS=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

# Validate required arguments
if [[ -z "$RECIPE" || -z "$NAME" || -z "$DATA" || -z "$OUTPUT" || -z "$CONTAINER" ]]; then
    echo "Error: Missing required arguments"
    usage
fi

# Convert recipe path to absolute path
if [[ ! "$RECIPE" = /* ]]; then
    # Relative path - convert to absolute
    RECIPE="$(cd "$(dirname "$RECIPE")" && pwd)/$(basename "$RECIPE")"
fi

# Verify recipe file exists
if [[ ! -f "$RECIPE" ]]; then
    echo "Error: Recipe file not found: $RECIPE"
    exit 1
fi

# Build override parameters JSON
PARAMS=$(cat <<EOF
{
  "instance_type": "$INSTANCE_TYPE",
  "recipes.run.name": "$NAME",
  "container": "$CONTAINER",
  "recipes.run.data_s3_path": "$DATA",
  "recipes.run.output_s3_path": "$OUTPUT"
EOF
)

# Add optional parameters
if [[ -n "$VAL" ]]; then
    PARAMS="${PARAMS},
  \"recipes.run.validation_data_s3_path\": \"$VAL\""
fi

if [[ -n "$MODEL_PATH" ]]; then
    PARAMS="${PARAMS},
  \"recipes.run.model_name_or_path\": \"$MODEL_PATH\""
fi

if [[ -n "$MLFLOW" ]]; then
    PARAMS="${PARAMS},
  \"recipes.run.mlflow_tracking_uri\": \"$MLFLOW\""
fi

PARAMS="${PARAMS}
}"

# Generate timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Print job info
echo "======================================================================"
echo "🚀 Launching HyperPod Job"
echo "======================================================================"
echo "Timestamp: $TIMESTAMP"
echo "Recipe: $RECIPE (absolute path)"
echo "Job Name: $NAME"
echo "Instance: $INSTANCE_TYPE"
echo "Namespace: $NAMESPACE"
echo "Data: $DATA"
[[ -n "$VAL" ]] && echo "Validation: $VAL"
echo "Output: $OUTPUT"
[[ -n "$MODEL_PATH" ]] && echo "Model Path: $MODEL_PATH"
[[ -n "$MLFLOW" ]] && echo "MLflow: $MLFLOW"
echo "Container: $CONTAINER"
echo "======================================================================"
echo ""

# Build and execute command
if [[ "$DRY_RUN" == true ]]; then
    echo "DRY RUN - Command that would be executed:"
    echo "hyperpod start-job \\"
    echo "  -n $NAMESPACE \\"
    echo "  --recipe $RECIPE \\"
    echo "  --override-parameters '$PARAMS'"
    exit 0
fi

# Execute and capture output
OUTPUT_FILE=$(mktemp)
trap "rm -f $OUTPUT_FILE" EXIT

hyperpod start-job \
    -n "$NAMESPACE" \
    --recipe "$RECIPE" \
    --override-parameters "$PARAMS" 2>&1 | tee "$OUTPUT_FILE"

# Extract job name from output
JOB_NAME=$(grep -E "^NAME:" "$OUTPUT_FILE" | awk '{print $2}' | head -1)

if [[ -z "$JOB_NAME" ]]; then
    # Fallback: try to extract from results directory
    JOB_NAME=$(grep -oE "results/[^/]+/k8s_templates" "$OUTPUT_FILE" | cut -d'/' -f2 | head -1)
fi

# Save logs
if [[ "$NO_LOGS" != true ]]; then
    mkdir -p "$LOGS_DIR"

    # Create individual job log
    SAFE_JOB_NAME="${JOB_NAME:-unknown}"
    LOG_FILE="$LOGS_DIR/${TIMESTAMP}_${SAFE_JOB_NAME}.log"

    cat > "$LOG_FILE" <<EOF_LOG
================================================================================
HyperPod Job Submission Log
================================================================================

Timestamp: $TIMESTAMP
Job Name: ${JOB_NAME:-N/A}

Parameters:
  Recipe: $RECIPE
  Name: $NAME
  Instance Type: $INSTANCE_TYPE
  Namespace: $NAMESPACE
  Data: $DATA
EOF_LOG

    [[ -n "$VAL" ]] && echo "  Validation: $VAL" >> "$LOG_FILE"
    echo "  Output: $OUTPUT" >> "$LOG_FILE"
    [[ -n "$MODEL_PATH" ]] && echo "  Model Path: $MODEL_PATH" >> "$LOG_FILE"
    [[ -n "$MLFLOW" ]] && echo "  MLflow: $MLFLOW" >> "$LOG_FILE"
    echo "  Container: $CONTAINER" >> "$LOG_FILE"

    cat >> "$LOG_FILE" <<EOF_LOG

================================================================================
Full Output:
================================================================================

EOF_LOG

    cat "$OUTPUT_FILE" >> "$LOG_FILE"

    # Append to summary log
    SUMMARY_FILE="$LOGS_DIR/jobs_summary.log"
    echo "$TIMESTAMP | ${JOB_NAME:-N/A} | $NAME | $INSTANCE_TYPE | $(basename "$LOG_FILE")" >> "$SUMMARY_FILE"

    echo ""
    echo "📝 Logs saved to: $LOG_FILE"
    echo "📋 Summary updated: $SUMMARY_FILE"
fi

echo ""
echo "======================================================================"
if [[ -n "$JOB_NAME" ]]; then
    echo "✅ Job Successfully Deployed"
    echo "📝 Job Name: $JOB_NAME"
    echo "======================================================================"
    echo ""
    echo "JOB_NAME=$JOB_NAME"
else
    echo "⚠️  Job deployed but couldn't extract job name from output"
    echo "======================================================================"
fi
