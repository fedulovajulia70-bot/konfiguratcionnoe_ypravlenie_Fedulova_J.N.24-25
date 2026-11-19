"""Generate the test and npm examples with the final CLI application."""

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
TESTS = ("chain", "diamond", "cycle", "filtered", "isolated")
NPM = ("is-odd", "is-even", "string-width")


def main():
    """Save CLI output alongside generated SVG and D2 examples."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true",
                        help="render only local test repositories")
    args = parser.parse_args()
    names = TESTS if args.offline else TESTS + NPM
    output = PROJECT / "output"
    output.mkdir(exist_ok=True)
    for name in names:
        result = subprocess.run(
            [sys.executable, "src/main.py", f"examples/configs/{name}.json"],
            cwd=PROJECT, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=180, check=False,
        )
        if result.returncode:
            raise RuntimeError(result.stderr)
        (output / f"{name}.txt").write_text(result.stdout, encoding="utf-8")
        print(f"Rendered {name}")


if __name__ == "__main__":
    main()
