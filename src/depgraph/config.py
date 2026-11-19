"""Load and validate the six JSON configuration parameters."""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .errors import AppError

FIELDS = {
    "package", "repository", "test_mode", "output", "ascii_tree",
    "filter_substring",
}
NPM_NAME = re.compile(r"(?:@[a-z0-9._-]+/)?[a-z0-9][a-z0-9._-]*")
TEST_NAME = re.compile(r"[A-Z]+")


def read_json(path):
    """Read a UTF-8 JSON file and report file or syntax errors."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, ValueError) as error:
        raise AppError(f"Cannot read JSON {path}: {error}") from error


def split_package(value):
    """Split an npm name, optionally followed by @version or @range."""
    name, separator, version = value.rpartition("@")
    if separator and name:
        if not version.strip():
            raise AppError("package: version after @ must not be empty")
        return name, version
    return value, "latest"


def validate_package(value, test_mode):
    """Check a test node name or npm package specification."""
    if not isinstance(value, str) or not value:
        raise AppError("package: expected a nonempty string")
    name = value if test_mode else split_package(value)[0]
    pattern = TEST_NAME if test_mode else NPM_NAME
    if not pattern.fullmatch(name):
        raise AppError("package: invalid test node or npm package name")


def validate_repository(value, test_mode, base):
    """Resolve a test file or validate an HTTP(S) registry URL."""
    if not isinstance(value, str) or not value.strip():
        raise AppError("repository: expected a nonempty string")
    if test_mode:
        try:
            path = (base / value).resolve()
        except (OSError, ValueError) as error:
            raise AppError(f"repository: invalid path: {error}") from error
        if not path.is_file():
            raise AppError(f"repository: file does not exist: {path}")
        return str(path)
    try:
        parsed = urlparse(value)
        parsed.port
    except ValueError as error:
        raise AppError("repository: invalid URL or port") from error
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise AppError("repository: expected an HTTP(S) URL")
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise AppError("repository: credentials, query and fragment forbidden")
    return value.rstrip("/")


def validate_output(value, base, protected):
    """Validate an SVG destination without creating files."""
    if not isinstance(value, str) or not value.strip():
        raise AppError("output: expected a nonempty string")
    try:
        path = (base / value).resolve()
    except (OSError, ValueError) as error:
        raise AppError(f"output: invalid path: {error}") from error
    if path.suffix.lower() != ".svg" or path.is_dir():
        raise AppError("output: expected an SVG file path")
    if path in protected or path.with_suffix(".d2") in protected:
        raise AppError("output: would overwrite an input file")
    ancestor = path.parent
    while not ancestor.exists():
        ancestor = ancestor.parent
    if not ancestor.is_dir() or not os.access(ancestor, os.W_OK):
        raise AppError("output: parent directory is not writable")
    if path.exists() and not os.access(path, os.W_OK):
        raise AppError("output: file is not writable")
    return path


@dataclass(frozen=True)
class Config:
    """Validated, path-resolved application configuration."""

    package: str
    repository: str
    test_mode: bool
    output: Path
    ascii_tree: bool
    filter_substring: str


def validate_fields(data):
    """Reject unknown, missing or incorrectly typed configuration fields."""
    if not isinstance(data, dict):
        raise AppError("config: expected a JSON object")
    if set(data) != FIELDS:
        missing = sorted(FIELDS - set(data))
        extra = sorted(set(data) - FIELDS)
        raise AppError(f"config: missing={missing}, unknown={extra}")
    for key in ("test_mode", "ascii_tree"):
        if type(data[key]) is not bool:
            raise AppError(f"{key}: expected true or false")
    if not isinstance(data["filter_substring"], str):
        raise AppError("filter_substring: expected a string")
    validate_package(data["package"], data["test_mode"])
    name = split_package(data["package"])[0]
    substring = data["filter_substring"]
    if substring and substring in name:
        raise AppError("filter_substring: excludes the root package")


def load_config(path):
    """Load configuration; resolve relative paths against its directory."""
    path = Path(path).resolve()
    data = read_json(path)
    validate_fields(data)
    repository = validate_repository(
        data["repository"], data["test_mode"], path.parent,
    )
    protected = {path}
    if data["test_mode"]:
        protected.add(Path(repository))
    output = validate_output(data["output"], path.parent, protected)
    return Config(**{**data, "repository": repository, "output": output})
