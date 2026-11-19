"""Small independent implementation of npm's common semantic ranges."""

import re
from dataclasses import dataclass
from functools import total_ordering

from .errors import AppError

VERSION = re.compile(
    r"v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?"
)
PARTIAL = re.compile(
    r"[v=]?(\d+|[xX*])(?:\.(\d+|[xX*]))?"
    r"(?:\.(\d+|[xX*]))?(?:-([0-9A-Za-z.-]+))?"
    r"(?:\+[0-9A-Za-z.-]+)?"
)
COMPONENTS = 3


@total_ordering
@dataclass(frozen=True)
class Version:
    """Comparable SemVer value; build metadata does not affect precedence."""

    core: tuple
    prerelease: tuple = ()

    @classmethod
    def parse(cls, text):
        """Parse a complete semantic version."""
        match = VERSION.fullmatch(text)
        if not match:
            raise AppError(f"Invalid semantic version: {text}")
        core = tuple(int(value) for value in match.groups()[:COMPONENTS])
        pre = tuple(match[4].split(".")) if match[4] else ()
        if any(part.isdigit() and len(part) > 1 and part[0] == "0"
               for part in pre):
            raise AppError(f"Invalid prerelease version: {text}")
        return cls(core, pre)

    def __lt__(self, other):
        """Compare numeric cores, then numeric/text prerelease identifiers."""
        if self.core != other.core:
            return self.core < other.core
        if not self.prerelease or not other.prerelease:
            return bool(self.prerelease) and not other.prerelease
        left = tuple((0, int(x)) if x.isdigit() else (1, x)
                     for x in self.prerelease)
        right = tuple((0, int(x)) if x.isdigit() else (1, x)
                      for x in other.prerelease)
        return left < right


def partial(text):
    """Return a zero-filled lower version and number of fixed components."""
    match = PARTIAL.fullmatch(text)
    if not match:
        raise AppError(f"Unsupported npm version range: {text}")
    fixed = []
    wildcard = False
    for value in match.groups()[:COMPONENTS]:
        if value is None or value.lower() in {"x", "*"}:
            wildcard = True
        elif wildcard:
            raise AppError(f"Invalid wildcard range: {text}")
        else:
            fixed.append(int(value))
    core = tuple(fixed + [0] * (COMPONENTS - len(fixed)))
    pre = tuple(match[4].split(".")) if match[4] else ()
    if pre and len(fixed) != COMPONENTS:
        raise AppError(f"Incomplete prerelease range: {text}")
    return Version(core, pre), len(fixed)


def increment(version, index):
    """Increase one component and reset all components to its right."""
    core = list(version.core)
    core[index] += 1
    core[index + 1:] = [0] * (COMPONENTS - index - 1)
    return Version(tuple(core))


def upper_bound(version):
    """Exclude all prereleases of a synthetic upper version, as npm does."""
    return Version(version.core, ("0",))


def bounded(operator, version, count):
    """Expand caret, tilde, exact or wildcard ranges into comparisons."""
    if not count:
        return []
    if operator == "^":
        nonzero = next((i for i, n in enumerate(version.core) if n), None)
        index = min(nonzero if nonzero is not None else 2, count - 1)
    elif operator == "~":
        index = min(1, count - 1)
    elif count == COMPONENTS:
        return [("=", version)]
    else:
        index = count - 1
    return [(">=", version), ("<", upper_bound(increment(version, index)))]


def comparator(token):
    """Expand one npm comparator, including partial version bounds."""
    match = re.fullmatch(r"(>=|<=|>|<|=|\^|~)?(.+)", token)
    if not match:
        raise AppError(f"Invalid npm comparator: {token}")
    operator, text = match.groups()
    version, count = partial(text)
    if operator in {None, "=", "^", "~"}:
        return bounded(operator, version, count)
    if not count:
        if operator in {">", "<"}:
            return [("<", Version((0, 0, 0)))]
        return []
    if count < COMPONENTS and operator in {">", "<="}:
        version = increment(version, count - 1)
        operator = ">=" if operator == ">" else "<"
    if count < COMPONENTS and operator == "<":
        version = upper_bound(version)
    return [(operator, version)]


def compile_group(text):
    """Compile an AND group, with optional npm hyphen notation."""
    hyphen = re.fullmatch(r"\s*(\S+)\s+-\s+(\S+)\s*", text)
    if hyphen:
        lower, lower_count = partial(hyphen[1])
        upper, upper_count = partial(hyphen[2])
        bounds = [(">=", lower)] if lower_count else []
        if upper_count:
            bound = ("<=", upper) if upper_count == COMPONENTS else (
                "<", upper_bound(increment(upper, upper_count - 1)),
            )
            bounds.append(bound)
        return bounds
    text = re.sub(r"(>=|<=|>|<|=|\^|~)\s+", r"\1", text.strip())
    return [item for token in text.split() for item in comparator(token)]


def matches(version, comparisons):
    """Apply comparisons and npm's explicit prerelease opt-in rule."""
    if version.prerelease and not any(
        bound.prerelease and bound.core == version.core
        for _, bound in comparisons
    ):
        return False
    for operator, bound in comparisons:
        valid = {
            "=": version == bound, ">": version > bound,
            ">=": version >= bound, "<": version < bound,
            "<=": version <= bound,
        }
        if not valid[operator]:
            return False
    return True


def select_version(versions, spec, tags):
    """Choose a dist-tag or the highest version satisfying an npm range."""
    spec = spec.strip()
    if spec in tags:
        spec = tags[spec]
    if spec in versions:
        return spec
    groups = [compile_group(group) for group in spec.split("||")]
    candidates = []
    for text in versions:
        try:
            version = Version.parse(text)
        except AppError:
            continue
        if any(matches(version, group) for group in groups):
            candidates.append((version, text))
    if not candidates:
        raise AppError(f"No published version satisfies {spec!r}")
    return max(candidates)[1]
