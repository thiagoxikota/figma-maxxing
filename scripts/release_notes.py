#!/usr/bin/env python3
"""Release gate: check that a version matches every manifest, then print its CHANGELOG section.

Stdlib only. Fails (exit 1) when:
  - the version differs from any version field: .claude-plugin/plugin.json, every other JSON
    file at the root or in a root dot folder (.codex-plugin/, .cursor-plugin/) that has a
    top-level "version" string, CITATION.cff, the "Version x.y.z." line of llms.txt, or the
    metadata.version of any SKILL.md, or
  - CHANGELOG.md has no '## [<version>]' section, or the section is empty.
Otherwise prints the section body, ready for `gh release create --notes-file`.

Usage:
  python3 scripts/release_notes.py 1.1.1 > notes.md
  python3 scripts/release_notes.py v1.1.1            # a leading v is ignored
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def json_manifests(root: Path = ROOT) -> list[Path]:
    """JSON files at the root and in root dot folders (not .git), the places manifests live."""
    found = set(root.glob('*.json')) | {p for p in root.glob('.*/*.json') if p.parts[-2] != '.git'}
    return sorted(found)


def versions(root: Path = ROOT) -> dict[str, str]:
    """Every version field in the repository, keyed by where it lives."""
    found = {'.claude-plugin/plugin.json': json.loads((root / '.claude-plugin/plugin.json').read_text())['version']}
    for path in json_manifests(root):
        data = json.loads(path.read_text())
        if isinstance(data, dict) and isinstance(data.get('version'), str):
            found[path.relative_to(root).as_posix()] = data['version']
    llms = root / 'llms.txt'
    if llms.is_file():
        m = re.search(r'\bVersion (\d+\.\d+\.\d+)\.', llms.read_text())
        found['llms.txt'] = m.group(1) if m else '(missing)'
    cff = root / 'CITATION.cff'
    if cff.is_file():
        m = re.search(r'^version:\s*["\']?([^"\'\s]+)', cff.read_text(), re.M)
        found['CITATION.cff'] = m.group(1) if m else '(missing)'
    for skill in sorted((root / 'skills').glob('*/SKILL.md')):
        head = skill.read_text().split('\n---\n', 1)[0]
        m = re.search(r'^\s+version:\s*["\']?([^"\'\s]+)', head, re.M)
        found[str(skill.relative_to(root))] = m.group(1) if m else '(missing)'
    return found


def section(version: str, root: Path = ROOT) -> str:
    text = (root / 'CHANGELOG.md').read_text()
    m = re.search(rf'^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)', text, re.M | re.S)
    return m.group(1).strip() if m else ''


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(__doc__.strip().split('\n\n')[-1], file=sys.stderr)
        return 2
    version = args[0].removeprefix('v')
    problems = [f'{where} has {found}, expected {version}' for where, found in versions().items() if found != version]
    notes = section(version)
    if not notes:
        problems.append(f'CHANGELOG.md has no "## [{version}]" section with content')
    if problems:
        for p in problems:
            print(f'release_notes: {p}', file=sys.stderr)
        return 1
    print(notes)
    return 0


if __name__ == '__main__':
    sys.exit(main())
