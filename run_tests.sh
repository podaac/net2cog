#!/bin/bash
#
# Script to manage Python environment, install dependencies, and run tests.
# The script can be used to build and run pytest both locally and within
# a Docker container.
#

# Exit immediately if a command exits with a non-zero status.
set -e

# Configuration
VENV_DIR=".venv"
TEST_REPORT_DIR="test-reports"
VENV_ACTIVATE_SCRIPT="$VENV_DIR/bin/activate"

# Function to check for and install Poetry
function install_poetry() 
{
    if ! command -v poetry >/dev/null 2>&1; then
        echo "Poetry not found. Installing with pip..."
        python3 -m pip install poetry
        echo "Poetry installed successfully: $(poetry --version)"
    else
        echo "Poetry is already installed: $(poetry --version)"
    fi
}

# Function to create, activate, and install dependencies in the virtual environment
function setup_venv() 
{
    if [ ! -d "$VENV_DIR" ]; then
        echo "No $VENV_DIR found. Creating virtual environment..."
        # Create venv using python3 to ensure compatibility
        python3 -m venv "$VENV_DIR"
        
        # Activate and install
        source "$VENV_ACTIVATE_SCRIPT"
        echo "Installing packages with 'harmony' extra dependencies..."
        poetry install -E harmony
    fi
    
    # Always ensure the environment is activated before proceeding
    if [ -z "$VIRTUAL_ENV" ]; then
        echo "Activating virtual environment..."
        source "$VENV_ACTIVATE_SCRIPT"
    else
        echo "Virtual environment is already active."
    fi
}

# Function to run pytest and generate reports
function run_tests() 
{
    echo "Running tests..."
    mkdir -p "$TEST_REPORT_DIR"

    # Use poetry run to execute pytest within the project's environment
    poetry run pytest \
        --junitxml="$TEST_REPORT_DIR/pytest.xml" \
        --cov=net2cog/ \
        --cov-report=xml:"$TEST_REPORT_DIR/coverage.xml"
    
    result=$?
    
    if [ "$result" -ne 0 ]; then
        echo "ERROR: Tests failed with exit code $result"
        return 1
    fi
    
    echo "Tests passed successfully."
    return 0
}

# Function to display coverage report summary
function show_coverage_report() 
{
    echo ""
    echo "--- Test Coverage Estimates ---"
    # Execute coverage report within the poetry environment
    poetry run coverage report --omit="*tests/*"
    echo "-------------------------------"
}


#####################################################################
#
# Main entry
#
#####################################################################

# The Docker container already has the dependency packages installed,
# so there's no need to install them
if [[ -z "${DOCKER_RUNNING}" ]]; then
    echo "Running in Docker container, packages and enviornment already setup"
    install_poetry
    setup_venv
fi

# Run tests
run_tests

# Report
show_coverage_report
    
# Cleanup (Deactivate Venv if it was activated here)
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
    echo "Deactivated virtual environment."
fi
