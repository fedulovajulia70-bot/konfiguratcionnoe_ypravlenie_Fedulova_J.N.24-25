"""Export D2, render SVG with D2, and display safe ASCII trees."""

import json
import os
import shutil
import subprocess
from pathlib import Path
from xml.etree import ElementTree

from .errors import AppError

RENDER_TIMEOUT = 60
SVG_TAG = "{http://www.w3.org/2000/svg}svg"


def to_d2(graph):
    """Serialize every node and edge using safe generated D2 identifiers."""
    identifiers = {key: f"n{index}" for index, key in enumerate(graph.nodes)}
    lines = ["direction: right", ""]
    for key, identifier in identifiers.items():
        label = json.dumps(key, ensure_ascii=False)
        lines.append(f"{identifier}: {label}")
        if key == graph.root:
            lines.append(f'{identifier}.style.fill: "#dbeafe"')
    lines.append("")
    for parent, children in graph.edges.items():
        for child in children:
            lines.append(f"{identifiers[parent]} -> {identifiers[child]}")
    return "\n".join(lines) + "\n"


def ascii_tree(graph):
    """Print each subtree once, marking cycles and shared dependencies."""
    lines = [graph.root]
    seen = {graph.root}

    def visit(key, prefix, ancestors):
        """Expand a node with ASCII-only tree connectors."""
        children = graph.edges[key]
        for index, child in enumerate(children):
            last = index == len(children) - 1
            connector = "`-- " if last else "|-- "
            marker = ""
            if child in ancestors:
                marker = " [cycle]"
            elif child in seen:
                marker = " [shared]"
            lines.append(prefix + connector + child + marker)
            if not marker:
                seen.add(child)
                continuation = "    " if last else "|   "
                visit(child, prefix + continuation, ancestors | {child})

    visit(graph.root, "", {graph.root})
    return "\n".join(lines)


def find_d2():
    """Locate D2 in an environment override, PATH or local tools directory."""
    override = os.environ.get("D2_BINARY")
    if override:
        executable = shutil.which(override)
        if executable:
            return executable
        raise AppError(f"D2_BINARY executable does not exist: {override}")
    executable = shutil.which("d2")
    if executable:
        return executable
    project = Path(__file__).resolve().parents[2]
    name = "d2.exe" if os.name == "nt" else "d2"
    local = project / "tools/d2" / name
    if local.is_file():
        return str(local)
    raise AppError(
        "D2 is required for SVG. Install d2 or set D2_BINARY; "
        "the .d2 source has already been saved."
    )


def export_graph(graph, output):
    """Save D2 source and render its SVG without invoking a shell."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    source = output.with_suffix(".d2")
    source.write_text(to_d2(graph), encoding="utf-8")
    executable = find_d2()
    try:
        result = subprocess.run(
            [executable, "--layout=dagre", str(source), str(output)],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=RENDER_TIMEOUT, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AppError(f"Cannot render SVG: {error}") from error
    if result.returncode:
        raise AppError(f"D2 failed: {result.stderr.strip()}")
    try:
        root = ElementTree.parse(output).getroot()
    except (OSError, ElementTree.ParseError) as error:
        raise AppError(f"D2 did not produce valid SVG: {error}") from error
    if root.tag != SVG_TAG:
        raise AppError("D2 output is not an SVG document")
    return source, output
