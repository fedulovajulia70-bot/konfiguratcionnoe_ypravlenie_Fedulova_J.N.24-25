"""Independent demonstration only: compare our graph with npm's results."""

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from src.depgraph.config import load_config, split_package
from src.depgraph.graph import build_graph
from src.depgraph.operations import load_order
from src.depgraph.repository import create_repository

PROJECT = Path(__file__).resolve().parents[1]
PACKAGES = ("is-odd", "is-even", "string-width")


def command(arguments, directory):
    """Run an npm comparison command without shell interpolation."""
    result = subprocess.run(
        arguments, cwd=directory, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=180, check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result


def npm_graph(name, tree):
    """Extract name@version nodes and edges from npm ls --all --json."""
    nodes, edges = set(), set()

    def visit(package, details):
        """Read the logical npm tree, merging repeated package versions."""
        key = f"{package}@{details['version']}"
        nodes.add(key)
        for child, info in details.get("dependencies", {}).items():
            child_key = f"{child}@{info['version']}"
            edges.add((key, child_key))
            visit(child, info)

    visit(name, tree["dependencies"][name])
    return nodes, edges


def install(npm, config, directory):
    """Install solely for comparison, disabling lifecycle scripts."""
    directory.mkdir(parents=True, exist_ok=True)
    name, version = split_package(config.package)
    manifest = {"name": "variant26-comparison", "version": "1.0.0",
                "private": True, "dependencies": {name: version}}
    (directory / "package.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8",
    )
    arguments = [
        npm, "install", "--ignore-scripts", "--no-audit", "--no-fund",
        "--omit=dev", "--omit=optional", "--legacy-peer-deps",
        "--loglevel=silly", "--registry", config.repository,
        "--cache", str(PROJECT / "tmp/npm-cache"),
    ]
    result = command(arguments, directory)
    log = result.stdout + result.stderr
    (directory / "install.log").write_text(log, encoding="utf-8")
    return re.findall(r"silly fetch manifest ([^\r\n]+)", log)


def compare_one(npm, name):
    """Run our DFS and npm separately, retaining raw comparison evidence."""
    config = load_config(PROJECT / f"examples/configs/{name}.json")
    repository = create_repository(config)
    root = repository.resolve(*split_package(config.package))
    graph = build_graph(repository, root)
    directory = PROJECT / f"tmp/npm-comparison/{name}"
    fetched = install(npm, config, directory)
    raw = command([npm, "ls", "--all", "--json"], directory).stdout
    (directory / "npm-ls.json").write_text(raw, encoding="utf-8")
    tree = command([npm, "ls", "--all", "--unicode=false"], directory).stdout
    (directory / "npm-ls.txt").write_text(tree, encoding="utf-8")
    npm_nodes, npm_edges = npm_graph(name, json.loads(raw))
    our_edges = {(key, child) for key, children in graph.edges.items()
                 for child in children}
    return {
        "package": root.key, "nodes": sorted(graph.nodes),
        "edges": sorted(our_edges), "load_order": load_order(graph),
        "npm_fetch_manifest_order": fetched,
        "nodes_match": set(graph.nodes) == npm_nodes,
        "edges_match": our_edges == npm_edges, "npm_tree": tree,
        "only_our_edges": sorted(our_edges - npm_edges),
        "only_npm_edges": sorted(npm_edges - our_edges),
    }


def main():
    """Write a reproducible three-package comparison to output/."""
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm:
        raise RuntimeError("Install Node.js and npm to run this comparison")
    report = {
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "npm_version": command([npm, "--version"], PROJECT).stdout.strip(),
        "results": [compare_one(npm, name) for name in PACKAGES],
    }
    destination = PROJECT / "output/comparison.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    for result in report["results"]:
        print(f"{result['package']}: nodes={result['nodes_match']}, "
              f"edges={result['edges_match']}")
    print(destination)


if __name__ == "__main__":
    main()
