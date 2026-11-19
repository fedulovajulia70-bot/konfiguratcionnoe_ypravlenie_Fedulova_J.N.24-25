"""Read npm registry JSON directly or use a local test repository."""

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .config import NPM_NAME, TEST_NAME, read_json, split_package
from .errors import AppError
from .semver import select_version

HTTP_TIMEOUT = 30


@dataclass
class Package:
    """Resolved package identity and direct dependency requirements."""

    name: str
    version: str
    dependencies: dict

    @property
    def key(self):
        """Identify each concrete npm version as a separate graph node."""
        return f"{self.name}@{self.version}" if self.version else self.name


class NpmRepository:
    """Access packuments using urllib; cache metadata for one execution."""

    def __init__(self, url):
        """Remember the registry URL and initialize a metadata cache."""
        self.url = url.rstrip("/")
        self.cache = {}

    def metadata(self, name):
        """Fetch and validate JSON metadata for one package name."""
        if name in self.cache:
            return self.cache[name]
        request = Request(
            f"{self.url}/{quote(name, safe='@')}",
            headers={"Accept": "application/vnd.npm.install-v1+json"},
        )
        try:
            with urlopen(request, timeout=HTTP_TIMEOUT) as response:
                data = json.load(response)
        except (HTTPError, URLError, OSError, ValueError) as error:
            raise AppError(f"Cannot fetch {name}: {error}") from error
        if not isinstance(data, dict) or not isinstance(
            data.get("versions"), dict,
        ):
            raise AppError(f"Invalid npm metadata for {name}")
        self.cache[name] = data
        return data

    def resolve(self, name, spec="latest"):
        """Select a package version, supporting npm package aliases."""
        if spec.startswith("npm:"):
            name, spec = split_package(spec[len("npm:"):])
        if not NPM_NAME.fullmatch(name):
            raise AppError(f"Invalid npm dependency name: {name}")
        data = self.metadata(name)
        tags = data.get("dist-tags", {})
        if not isinstance(tags, dict) or any(
            not isinstance(value, str) for value in tags.values()
        ):
            raise AppError(f"Invalid dist-tags for {name}")
        version = select_version(data["versions"], spec, tags)
        manifest = data["versions"][version]
        if not isinstance(manifest, dict):
            raise AppError(f"Invalid manifest for {name}@{version}")
        dependencies = manifest.get("dependencies", {})
        validate_dependencies(dependencies, name)
        return Package(name, version, dependencies)


def validate_dependencies(dependencies, name):
    """Reject malformed runtime dependency maps rather than hiding errors."""
    if not isinstance(dependencies, dict):
        raise AppError(f"Invalid dependencies for {name}")
    for child, spec in dependencies.items():
        if not NPM_NAME.fullmatch(child) or not isinstance(spec, str):
            raise AppError(f"Invalid dependency in {name}: {child}")


class TestRepository:
    """Represent a JSON adjacency list whose nodes use capital letters."""

    def __init__(self, path):
        """Load all nodes and reject malformed or dangling edges."""
        self.data = read_json(path)
        if not isinstance(self.data, dict) or not self.data:
            raise AppError("Test repository must be a nonempty JSON object")
        for name, children in self.data.items():
            self.validate_node(name, children)

    def validate_node(self, name, children):
        """Require capital names, unique edges and explicitly listed nodes."""
        if not TEST_NAME.fullmatch(name) or not isinstance(children, list):
            raise AppError(f"Invalid test repository node: {name}")
        if any(not isinstance(child, str) for child in children):
            raise AppError(f"Invalid dependency list for {name}")
        if len(children) != len(set(children)):
            raise AppError(f"Duplicate dependencies for {name}")
        for child in children:
            if not TEST_NAME.fullmatch(child) or child not in self.data:
                raise AppError(f"Unknown test dependency: {name} -> {child}")

    def resolve(self, name, spec="latest"):
        """Return a test node with versionless dependency references."""
        if name not in self.data:
            raise AppError(f"Test package does not exist: {name}")
        return Package(name, "", dict.fromkeys(self.data[name], "*"))


def create_repository(config):
    """Choose the configured npm or local test data source."""
    repository = TestRepository if config.test_mode else NpmRepository
    return repository(config.repository)
