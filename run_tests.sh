#!/bin/bash
set -e

# Default to running all tests
TEST_PATH="tests/"

# Parse command-line arguments
if [ "$#" -gt 0 ]; then
    case "$1" in
        component|components|c)
            if [ -z "$2" ]; then
                echo "Error: Component name required"
                exit 1
            fi
            COMPONENT=${2//-/_}
            TEST_PATH="tests/components/test_${COMPONENT}.py"
            shift 2
            ;;
        application|applications|a|app)
            if [ -z "$2" ]; then
                TEST_PATH="tests/applications/"
                shift 1
            else
                TEST_PATH="tests/applications/test_${2}.py"
                shift 2
            fi
            ;;
        unit|u)
            if [ -z "$2" ]; then
                TEST_PATH="tests/unit/"
                shift 1
            else
                COMPONENT=${2//-/_}
                TEST_PATH="tests/unit/test_${COMPONENT}.py"
                shift 2
            fi
            ;;
        *)
            echo "Usage: $0 [component|application|unit] [name] [-- pytest args]"
            echo "Examples:"
            echo "  $0                       # Run all tests"
            echo "  $0 unit [name]           # Run unit tests (no Docker needed)"
            echo "  $0 component <name>      # Run component tests"
            echo "  $0 application [name]    # Run all application tests or specific application"
            echo "  $0 component foo -- --junitxml=results.xml"
            exit 1
            ;;
    esac
fi

# Strip optional -- separator
if [ "${1:-}" = "--" ]; then
    shift
fi

# Check if test path exists
if [ ! -e "$TEST_PATH" ]; then
    echo "Test path not found: $TEST_PATH"
    exit 1
fi

# Run pytest with proper cleanup
uv run pytest -v $TEST_PATH "$@"
