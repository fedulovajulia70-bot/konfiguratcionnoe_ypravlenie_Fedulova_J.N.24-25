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

STAGE_CONFIG = 1
STAGE_DIRECT = 2
STAGE_GRAPH = 3
STAGE_ORDER = 4
STAGE_VISUALIZATION = 5
STAGES = (STAGE_CONFIG, STAGE_DIRECT, STAGE_GRAPH, STAGE_ORDER,
          STAGE_VISUALIZATION)


def run(config, stage):
    """Execute the selected assignment stage."""
    if stage == STAGE_CONFIG:
        for key, value in asdict(config).items():
            print(f"{key}={value}")
        return
    repository = create_repository(config)
    name, spec = split_package(config.package)
    root = repository.resolve(name, spec)
    if stage == STAGE_DIRECT:
        print(root.key)
        for name, spec in sorted(root.dependencies.items()):
            print(f"{name}: {spec}")
        return
    graph = build_graph(repository, root, config.filter_substring)
    if stage == STAGE_ORDER:
        print("Load order: " + " -> ".join(load_order(graph)))
        return
    if stage == STAGE_VISUALIZATION:
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
    parser.add_argument(
        "--stage", type=int, choices=STAGES, default=STAGE_VISUALIZATION,
    )
    args = parser.parse_args(argv)
    try:
        run(load_config(args.config), args.stage)
    except (AppError, OSError, RecursionError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0
