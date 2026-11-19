"""Command line interface and stage demonstrations."""

import argparse
import sys
from dataclasses import asdict

from .config import load_config, split_package
from .errors import AppError
from .repository import create_repository


def run(config, stage):
    """Execute the selected assignment stage."""
    if stage == 1:
        for key, value in asdict(config).items():
            print(f"{key}={value}")
        return
    repository = create_repository(config)
    name, spec = split_package(config.package)
    root = repository.resolve(name, spec)
    print(root.key)
    for name, spec in sorted(root.dependencies.items()):
        print(f"{name}: {spec}")


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
