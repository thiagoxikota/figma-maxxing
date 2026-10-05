#!/usr/bin/env python3
"""Build the release zips from a git commit: one per skill and one bundle, plus SHA256SUMS.

Stdlib only. Every byte comes from the commit (git ls-tree and git cat-file), never from the
working tree, so uncommitted edits cannot leak into a release and the same commit gives the
same zips: entries are sorted, timestamps are fixed at 1980-01-01, and file modes come from git.

  dist/<skill>-<version>.zip          <skill>/SKILL.md at the root, plus <skill>/LICENSE.
                                       Upload it as a custom skill in claude.ai, or unzip it
                                       into a skills folder (~/.claude/skills, .agents/skills).
  dist/figma-maxxing-<version>.zip    the plugin layout under figma-maxxing-<version>/: skills,
                                       hooks, .claude-plugin, install.py and the docs.
  dist/SHA256SUMS                     sha256sum format, for `sha256sum -c SHA256SUMS`.

Usage:
  python3 scripts/build_dist.py                  # HEAD into dist/
  python3 scripts/build_dist.py --ref v1.1.0     # any commit or tag
  python3 scripts/build_dist.py --out /tmp/out   # another output folder
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EPOCH = (1980, 1, 1, 0, 0, 0)
BUNDLE_PATHS = ('.claude-plugin/', 'skills/', 'hooks/', 'install.py', 'LICENSE', 'README.md',
                'CHANGELOG.md', 'SECURITY.md', 'llms.txt', 'docs/README.pt-BR.md')
SKIP = re.compile(r'(^|/)(__pycache__/|\.DS_Store$)|\.pyc$')


def git(*args: str, data: bytes | None = None) -> bytes:
    return subprocess.run(['git', *args], cwd=ROOT, input=data, capture_output=True, check=True).stdout


def tree(ref: str) -> dict[str, tuple[int, str]]:
    """path -> (mode, blob sha) for every file in ref."""
    out = {}
    for row in git('ls-tree', '-r', '-z', ref).decode().split('\0'):
        if not row:
            continue
        meta, path = row.split('\t', 1)
        mode, kind, sha = meta.split()
        if kind == 'blob' and not SKIP.search(path):
            out[path] = (int(mode, 8), sha)
    return out


def blobs(shas: list[str]) -> dict[str, bytes]:
    """Read many blobs with one git cat-file --batch call."""
    raw = git('cat-file', '--batch', data=''.join(s + '\n' for s in shas).encode())
    out, i = {}, 0
    while i < len(raw):
        header_end = raw.index(b'\n', i)
        sha, _, size = raw[i:header_end].decode().split()
        start = header_end + 1
        out[sha] = raw[start:start + int(size)]
        i = start + int(size) + 1
    return out


def write_zip(target: Path, entries: list[tuple[str, int, bytes]]) -> None:
    with zipfile.ZipFile(target, 'w') as z:
        for name, mode, data in sorted(entries):
            info = zipfile.ZipInfo(name, EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3                      # unix, so the mode bits are honored
            info.external_attr = (0o100755 if mode & 0o111 else 0o100644) << 16
            z.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def build(ref: str, out: Path) -> list[Path]:
    files = tree(ref)
    content = blobs(sorted({sha for _, sha in files.values()}))
    def entry(path, name):
        mode, sha = files[path]
        return name, mode, content[sha]
    version = json.loads(content[files['.claude-plugin/plugin.json'][1]])['version']
    skills = sorted({p.split('/')[1] for p in files if re.fullmatch(r'skills/[^/]+/SKILL\.md', p)})
    if not skills:
        sys.exit(f'build_dist: no skills/*/SKILL.md in {ref}')
    out.mkdir(parents=True, exist_ok=True)
    for stale in [*out.glob('*.zip'), out / 'SHA256SUMS']:
        stale.unlink(missing_ok=True)
    built = []
    for skill in skills:
        prefix = f'skills/{skill}/'
        entries = [entry(p, p[len('skills/'):]) for p in files if p.startswith(prefix)]
        entries.append(entry('LICENSE', f'{skill}/LICENSE'))
        target = out / f'{skill}-{version}.zip'
        write_zip(target, entries)
        built.append(target)
    top = f'figma-maxxing-{version}/'
    entries = [entry(p, top + p) for p in files
               if any(p == b or (b.endswith('/') and p.startswith(b)) for b in BUNDLE_PATHS)]
    bundle = out / f'figma-maxxing-{version}.zip'
    write_zip(bundle, entries)
    built.append(bundle)
    sums = ''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in built)
    (out / 'SHA256SUMS').write_text(sums)
    return built


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--ref', default='HEAD', help='commit or tag to build (default HEAD)')
    ap.add_argument('--out', default=str(ROOT / 'dist'), help='output folder (default dist/)')
    args = ap.parse_args(argv)
    try:
        commit = git('rev-parse', '--verify', args.ref + '^{commit}').decode().strip()
    except subprocess.CalledProcessError:
        print(f'build_dist: {args.ref} is not a commit in this repository', file=sys.stderr)
        return 2
    built = build(commit, Path(args.out))
    for p in built:
        print(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.stat().st_size:>7}  {p.name}')
    print(f'build_dist: {len(built)} zips from {commit[:7]} in {args.out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
