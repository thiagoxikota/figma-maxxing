#!/usr/bin/env python3
"""Copy the Figma Maxxing skills into an agent's skills directory.

Copies files only. No downloads, no dependencies, no hooks, no settings edited, no overwrites.
"""
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'skills'
TARGETS = {'claude': '.claude', 'agents': '.agents'}
IGNORE = shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store')


def available() -> list:
    return sorted(p.name for p in SOURCE.iterdir() if (p / 'SKILL.md').is_file())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', choices=sorted(TARGETS), default='claude',
                        help='claude: .claude/skills (Claude Code); agents: .agents/skills (Codex, Cursor, Gemini CLI)')
    parser.add_argument('--scope', choices=['project', 'user'], default='project',
                        help='project: inside --project; user: inside your home directory')
    parser.add_argument('--project', type=Path, default=Path.cwd(), help='project directory (default: current)')
    parser.add_argument('--skills', help='comma separated subset (default: all)')
    parser.add_argument('--skip-existing', action='store_true', help='install the rest when some already exist')
    parser.add_argument('--dry-run', action='store_true', help='print what would be copied')
    parser.add_argument('--list', action='store_true', help='list the skills in this repository')
    args = parser.parse_args(argv)

    if not SOURCE.is_dir():
        parser.error('Run install.py from a complete repository checkout.')
    names = available()
    if args.list:
        print('\n'.join(names))
        return 0

    wanted = list(dict.fromkeys(n.strip() for n in args.skills.split(',') if n.strip())) if args.skills else names
    unknown = sorted(set(wanted) - set(names))
    if unknown:
        parser.error(f'Unknown skill(s): {", ".join(unknown)}. Available: {", ".join(names)}')
    if 'figma-canon' not in wanted:
        print('Note: the other skills load references from figma-canon. Install it too.', file=sys.stderr)

    base = Path.home() if args.scope == 'user' else args.project.expanduser().resolve()
    parent = base / TARGETS[args.target] / 'skills'
    existing = [n for n in wanted if (parent / n).exists() or (parent / n).is_symlink()]
    if existing and not args.skip_existing:
        parser.error(f'Already exists in {parent}: {", ".join(existing)}. '
                     'Back up or remove them, or pass --skip-existing to install the rest.')

    pending = [n for n in wanted if n not in existing]
    for name in pending:
        if args.dry_run:
            print(f'Would copy {SOURCE / name} to {parent / name}')
        else:
            parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(SOURCE / name, parent / name, ignore=IGNORE)
            print(f'Installed {parent / name}')
    for name in existing:
        print(f'Skipped (already exists): {parent / name}')
    if pending and not args.dry_run:
        print('Restart or reload your agent to discover the skills.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
