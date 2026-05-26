#!/bin/bash

# Script to download and install HyperPod CLI
# Based on: https://github.com/aws-samples/amazon-nova-samples/blob/main/customization/nova-forge-hyperpod-cli-installation/INSTALL_USAGE.md

set -e  # Exit on any error

SCRIPT_URL="https://raw.githubusercontent.com/aws-samples/amazon-nova-samples/refs/heads/main/customization/nova-forge-hyperpod-cli-installation/install_hp_cli.sh"
TEMP_SCRIPT="/tmp/install_hp_cli.sh"

echo "======================================"
echo "HyperPod CLI Installation Script"
echo "======================================"
echo ""

# Check prerequisites
echo "Checking prerequisites..."
echo ""

# Check if running in a virtual environment
if [[ -n "$VIRTUAL_ENV" ]] || [[ -n "$CONDA_DEFAULT_ENV" ]]; then
    echo "ERROR: Please deactivate any active Python virtual environments before running this script."
    echo "Run: deactivate (for venv) or conda deactivate (for conda)"
    exit 1
fi

# Check Python version
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    echo "✓ Python version: $PYTHON_VERSION"

    # Check if version is 3.8-3.12
    if [[ ! "$PYTHON_VERSION" =~ ^3\.(8|9|10|11|12)$ ]]; then
        echo "WARNING: Python version should be 3.8-3.12 for compatibility"
    fi
else
    echo "ERROR: Python 3 is not installed"
    exit 1
fi

# Check AWS credentials
if command -v aws &> /dev/null; then
    if aws sts get-caller-identity &> /dev/null; then
        echo "✓ AWS credentials configured"
    else
        echo "ERROR: AWS credentials not configured or invalid"
        echo "Please run: aws configure"
        exit 1
    fi
else
    echo "ERROR: AWS CLI is not installed"
    exit 1
fi

# Check for build tools (optional warning)
if ! command -v gcc &> /dev/null && ! command -v clang &> /dev/null; then
    echo "WARNING: No C compiler (gcc/clang) found. Installation may fail."
    echo "Install build tools if needed:"
    echo "  macOS: xcode-select --install"
    echo "  Ubuntu/Debian: sudo apt-get install build-essential python3-dev"
    echo ""
fi

echo ""
echo "Downloading installation script..."
curl -fsSL "$SCRIPT_URL" -o "$TEMP_SCRIPT"

if [[ ! -f "$TEMP_SCRIPT" ]]; then
    echo "ERROR: Failed to download installation script"
    exit 1
fi

echo "✓ Installation script downloaded"
echo ""

# Patch the script to support Python 3.12
echo "Patching installation script to support Python 3.12..."

# Create a temporary patched version
cp "$TEMP_SCRIPT" "${TEMP_SCRIPT}.orig"

# Apply patches to support Python 3.12
# 1. Update the version check conditional: change -gt 11 to -gt 12
# 2. Update version messages
sed 's/3\.8, 3\.9, 3\.10, 3\.11/3.8, 3.9, 3.10, 3.11, 3.12/g' "${TEMP_SCRIPT}.orig" | \
sed 's/Python 3\.11/Python 3.12/g' | \
sed 's/SUPPORTED_VERSIONS=("3\.8" "3\.9" "3\.10" "3\.11")/SUPPORTED_VERSIONS=("3.8" "3.9" "3.10" "3.11" "3.12")/g' | \
sed 's/\[\[ "$minor" -gt 11 \]\]/[[ "$minor" -gt 12 ]]/g' | \
sed 's/"\$minor" -gt 11/"$minor" -gt 12/g' > "$TEMP_SCRIPT"

rm -f "${TEMP_SCRIPT}.orig"
echo "✓ Script patched for Python 3.12 support"
echo ""

# Make the script executable
chmod +x "$TEMP_SCRIPT"

# Determine if we should run with debug flag
DEBUG_FLAG=""
if [[ "$1" == "--debug" ]] || [[ "$1" == "-d" ]]; then
    DEBUG_FLAG="--debug"
    echo "Running installation with debug output enabled..."
else
    echo "Running installation..."
    echo "(Use --debug flag for verbose output)"
fi

echo ""
echo "======================================"
echo ""

# Run the installation script
bash "$TEMP_SCRIPT" $DEBUG_FLAG

# Cleanup
rm -f "$TEMP_SCRIPT"

echo ""
echo "======================================"
echo "Installation Complete!"
echo "======================================"
echo ""
echo "To use HyperPod CLI:"
echo "  1. Activate the environment:"
echo "       source ~/hyperpod-cli-env/bin/activate"
echo ""
echo "  2. Run HyperPod commands:"
echo "       hyperpod --help"
echo ""
echo "  3. Deactivate when done:"
echo "       deactivate"
echo ""
