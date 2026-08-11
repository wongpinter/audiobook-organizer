"""Small stdlib-only TOML configuration loader."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

from audiobook_fetcher.rename.planner import DEFAULT_PATTERN

@dataclass(frozen=True)
class Config:
    input_dir: Path
    output_root: Path
    pattern: str = DEFAULT_PATTERN
    manifest_dir: Path | None = None
    timeout: float = 10.0

    @property
    def resolved_manifest_dir(self) -> Path:
        return self.manifest_dir or self.output_root / ".audiobook-fetcher" / "manifests"


def load_config(path: Path | None = None, **overrides: object) -> Config:
    values: dict[str, object] = {}
    if path and path.exists():
        with path.open("rb") as handle:
            values.update(tomllib.load(handle))
    raw_input = overrides.get("input_dir")
    input_dir = Path(str(raw_input if raw_input is not None else values.get("input_dir", ".")))
    raw_output = overrides.get("output_root")
    output_root = Path(str(raw_output if raw_output is not None else values.get("output_root", input_dir)))
    raw_pattern = overrides.get("pattern")
    pattern = str(raw_pattern if raw_pattern is not None else values.get("pattern", DEFAULT_PATTERN))
    manifest = overrides.get("manifest_dir", values.get("manifest_dir"))
    manifest_dir = Path(str(manifest)) if manifest else None
    timeout = float(overrides.get("timeout", values.get("timeout", 10.0)))
    return Config(input_dir=input_dir, output_root=output_root, pattern=pattern, manifest_dir=manifest_dir, timeout=timeout)
