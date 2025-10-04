"""
test_runner.py

Command-line runner for all Car Repair MCP project tests.
Allows selection of test subsets (e.g., only MCP-related tests), verbosity, and integration with CI pipelines.
"""

import argparse
import sys

import pytest


def main() -> int:
    """
    Main CLI entrypoint for running project tests.
    Returns exit code (0 if all tests pass, nonzero otherwise).
    """
    parser = argparse.ArgumentParser(
        description="Run Car Repair MCP API tests (all or by category)."
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="all",
        choices=["all", "mcp"],
        help="Test mode to run: 'all' for full test suite, 'mcp' for core MCP/LLM tests only.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase test output verbosity (can repeat for more verbosity).",
    )
    parser.add_argument(
        "pytest_args",
        nargs="*",
        help="Additional pytest arguments (e.g., -m 'not slow').",
    )
    args = parser.parse_args()

    # Build pytest arguments
    pytest_args = args.pytest_args
    if args.mode == "mcp":
        pytest_args += ["-m", "integration"]
    if args.verbose:
        pytest_args.append("-" + "v" * args.verbose)
    if "--tb=short" not in pytest_args:
        pytest_args.append("--tb=short")

    print(f"Running pytest with arguments: {pytest_args}")
    return pytest.main(pytest_args)


if __name__ == "__main__":
    sys.exit(main())
