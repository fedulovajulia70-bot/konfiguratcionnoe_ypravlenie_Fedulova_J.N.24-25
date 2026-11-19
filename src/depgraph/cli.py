"""Command line interface and stage demonstrations."""

import argparse
import sys
from dataclasses import asdict

from .config import load_config, split_package
from .errors import AppError
from .graph import build_graph, describe_graph
from .operations import load_order
from .repository import create_repository
from .visualization import ascii_tree, export_graph


def run(config, stage):
    """Execute the selected assignment stage."""
    if stage == 1:
        for key, value in asdict(config).items():
            print(f"{key}={value}")
        return
    repository = create_repository(config)
    name, spec = split_package(config.package)
    root = repository.resolve(name, spec)
    if stage == 2:
        print(root.key)
        for name, spec in sorted(root.dependencies.items()):
            print(f"{name}: {spec}")
        return
    graph = build_graph(repository, root, config.filter_substring)
    if stage == 4:
        print("Load order: " + " -> ".join(load_order(graph)))
        return
    if stage == 5:
        if config.ascii_tree:
            print(ascii_tree(graph))
        source, image = export_graph(graph, config.output)
        print(f"D2: {source}\nSVG: {image}")
        return
    print(describe_graph(graph))
    for cycle in graph.cycles:
        print(f"Cycle: {' -> '.join(cycle)}")


def main(argv=None):
    """Read arguments and return a process exit code."""
    parser = argparse.ArgumentParser(description="npm dependency graph, v26")
    parser.add_argument("config", help="path to the JSON configuration")
    parser.add_argument("--stage", type=int, choices=range(1, 6), default=5)
    args = parser.parse_args(argv)
    try:
        run(load_config(args.config), args.stage)
    except (AppError, OSError, RecursionError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0
