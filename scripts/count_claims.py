#!/usr/bin/env python3
"""Count what the docs cite (skills, gotchas, gate checks) and check every numeric claim against it.

Stdlib only. The counts come from the files themselves:
  skills             skills/*/SKILL.md
  gotchas            '## ' headings in plugin-api-anomalies.md and field-notes.md, minus the two
                     headings that are not gotchas ('Research vs ...', 'Anti-patterns ...')
  handoff_checks     '### <n>.' headings in figma-handoff-gate/SKILL.md
  preflight_checks   '### Check <n>:' headings in figma-preflight/SKILL.md
  slop_checks        '### S<n>.' headings in figma-slop-check/SKILL.md
  hook_patterns      entries in PATTERNS in hooks/figma-canon-precheck.py (and how many BLOCK)

Claims are checked in README.md, docs/*.md (except docs about other projects), llms.txt,
CITATION.cff, the manifests and every SKILL.md, in English and Brazilian Portuguese:
'8 skills', 'eight skills', '90 gotchas' (digits only), 'more than 80 notes', '17 checks'.
For a checks claim, a gate named earlier on the same line decides which gate it counts, then
the first gate named in its paragraph, then the SKILL.md it sits in.

Usage:
  python3 scripts/count_claims.py            # print the counts as JSON
  python3 scripts/count_claims.py --check    # also check the claims; exit 1 on a mismatch
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOT_GOTCHAS = ('## Research vs', '## Anti-patterns')
OTHER_PROJECTS = {'landscape.md'}  # docs that describe other repositories, whose counts are theirs
WORDS = {w: i for i, w in enumerate(
    'zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen '
    'sixteen seventeen eighteen nineteen twenty'.split())}
WORDS.update({w: i for i, w in enumerate(
    'zero um dois tres quatro cinco seis sete oito nove dez onze doze treze quatorze quinze '
    'dezesseis dezessete dezoito dezenove vinte'.split())})
WORDS.update({'uma': 1, 'duas': 2, 'três': 3, 'catorze': 14})
NUMBER = r'(\d+|' + '|'.join(sorted(WORDS, key=len, reverse=True)) + r')'
GATES = {'handoff': 'handoff_checks', 'preflight': 'preflight_checks', 'slop': 'slop_checks'}
SKILL_FILE_GATE = {'figma-handoff-gate': 'handoff', 'figma-preflight': 'preflight', 'figma-slop-check': 'slop'}

SKILLS_CLAIM = re.compile(rf'\b{NUMBER}\s+(?:Agent\s+)?[Ss]kills\b', re.I)
GOTCHAS_CLAIM = re.compile(r'\b(\d+)\s+(?:gotchas|armadilhas|pegadinhas)\b', re.I)  # totals are digits; 'three gotchas' is a sub-count
MORE_THAN = re.compile(r'\b(?:more than|over|mais de)\s+(\d+)\s+(?:gotchas|notes|notas|armadilhas|pegadinhas)\b', re.I)
CHECKS_CLAIM = re.compile(rf'\b{NUMBER}(?:[- ]checks|-check gate|[- ]checagens|[- ]verificações|[- ]verificacoes)\b', re.I)
GATE_NAME = re.compile(r'handoff|preflight|slop', re.I)


def headings(path: Path, pattern: str) -> list[str]:
    return [line for line in path.read_text().split('\n') if re.match(pattern, line)]


def counts(root: Path = ROOT) -> dict:
    skills = root / 'skills'
    refs = skills / 'figma-canon/references'
    per_file = {name: len([h for h in headings(refs / name, r'## ') if not h.startswith(NOT_GOTCHAS)])
                for name in ('plugin-api-anomalies.md', 'field-notes.md')}
    patterns = []
    for node in ast.walk(ast.parse((root / 'hooks/figma-canon-precheck.py').read_text())):
        if isinstance(node, ast.Assign) and getattr(node.targets[0], 'id', '') == 'PATTERNS':
            patterns = [e.elts[1].value for e in node.value.elts]
    return {
        'skills': len(list(skills.glob('*/SKILL.md'))),
        'gotchas': sum(per_file.values()),
        'gotchas_anomalies': per_file['plugin-api-anomalies.md'],
        'gotchas_field_notes': per_file['field-notes.md'],
        'handoff_checks': len(headings(skills / 'figma-handoff-gate/SKILL.md', r'### \d+\. ')),
        'preflight_checks': len(headings(skills / 'figma-preflight/SKILL.md', r'### Check \d+: ')),
        'slop_checks': len(headings(skills / 'figma-slop-check/SKILL.md', r'### S\d+\. ')),
        'hook_patterns': len(patterns),
        'hook_block_patterns': patterns.count('BLOCK'),
    }


def claim_files(root: Path = ROOT) -> list[Path]:
    docs = [p for p in sorted((root / 'docs').glob('*.md')) if p.name not in OTHER_PROJECTS]
    files = [root / 'README.md', root / 'llms.txt', root / 'CITATION.cff', *docs,
             *sorted((root / '.claude-plugin').glob('*.json')), *sorted((root / 'skills').glob('*/SKILL.md'))]
    return [f for f in files if f.is_file()]


def value(token: str) -> int:
    return int(token) if token.isdigit() else WORDS[token.lower()]


def claims(text: str, default_gate: str | None = None) -> list[tuple[str, int, int, str]]:
    """(metric, number, line, matched text) for every numeric claim found in text.

    metric is 'skills', 'gotchas', 'gotchas_floor' (a 'more than N' claim) or a gate count key.
    A checks claim with no gate name before it in its paragraph (and no default) is skipped.
    """
    found = []
    def line(pos):
        return text.count('\n', 0, pos) + 1
    for m in SKILLS_CLAIM.finditer(text):
        found.append(('skills', value(m.group(1)), line(m.start()), m.group(0)))
    for m in GOTCHAS_CLAIM.finditer(text):
        found.append(('gotchas', value(m.group(1)), line(m.start()), m.group(0)))
    for m in MORE_THAN.finditer(text):
        found.append(('gotchas_floor', int(m.group(1)), line(m.start()), m.group(0)))
    for m in CHECKS_CLAIM.finditer(text):
        # A gate named earlier on the same line wins; otherwise the paragraph's first gate name
        # (its subject, as in a bold '**figma-handoff-gate**' lead line); otherwise the file's.
        on_line = GATE_NAME.findall(text[text.rfind('\n', 0, m.start()) + 1:m.start()])
        in_paragraph = GATE_NAME.findall(text[max(0, text.rfind('\n\n', 0, m.start())):m.start()])
        gate = (on_line[-1] if on_line else in_paragraph[0] if in_paragraph else default_gate or '').lower()
        if gate:
            found.append((GATES[gate], value(m.group(1)), line(m.start()), m.group(0)))
    return sorted(found, key=lambda f: f[2])


def check_text(text: str, c: dict, default_gate: str | None = None) -> list[str]:
    """Every numeric claim in text that disagrees with the counts, as 'line N: ...' strings."""
    problems = []
    for metric, number, line, quote in claims(text, default_gate):
        if metric == 'gotchas_floor':
            if number >= c['gotchas']:
                problems.append(f'line {line}: "{quote}" but there are {c["gotchas"]} gotchas')
        elif number != c[metric]:
            problems.append(f'line {line}: "{quote}" but the count is {c[metric]} ({metric})')
    return problems


def check(root: Path = ROOT) -> dict[str, list[str]]:
    c, out = counts(root), {}
    for path in claim_files(root):
        gate = SKILL_FILE_GATE.get(path.parent.name) if path.name == 'SKILL.md' else None
        problems = check_text(path.read_text(), c, gate)
        if problems:
            out[str(path.relative_to(root))] = problems
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--check', action='store_true', help='check the numeric claims in the docs')
    args = ap.parse_args(argv)
    print(json.dumps(counts(), indent=2))
    if not args.check:
        return 0
    problems = check()
    for path, items in problems.items():
        for p in items:
            print(f'MISMATCH {path} {p}')
    n = sum(map(len, problems.values()))
    print(f'count_claims: {len(claim_files())} files checked, {n} mismatch{"es" if n != 1 else ""}')
    return 1 if n else 0


if __name__ == '__main__':
    sys.exit(main())
