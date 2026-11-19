"""Command line interface and stage demonstrations."""

import argparse
import sys
from dataclasses import asdict

from .config import load_config
from .errors import AppError


def run(config, stage):
    """Execute the selected assignment stage."""
    for key, value in asdict(config).items():
        print(f"{key}={value}")


def main(argv=None):
    """Read arguments and return a process exit code."""
    parser = argparse.ArgumentParser(description="npm dependency graph, v26")
    parser.add_argument("config", help="path to the JSON configuration")
    parser.add_argument("--stage", type=int, choices=range(1, 6), default=1)
    args = parser.parse_args(argv)
    try:
        run(load_config(args.config), args.stage)
    except (AppError, OSError, RecursionError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0
