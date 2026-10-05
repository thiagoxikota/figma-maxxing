#!/usr/bin/env python3
"""Check every Figma Plugin API name the skills mention against @figma/plugin-typings.

Stdlib only, no Node. Scans skills/**/*.md, skills/**/*.js and hooks/*.py. Each tier is a hard
error on a miss:

  1. chains    figma.* chains anywhere in the text resolve member by member through the typings,
               starting at PluginAPI (figma.variables.getVariableByIdAsync must exist on
               VariablesAPI, figma.currentPage.selection on PageNode, and so on).
  2. editor    a chain that resolves to a member the typings document as "only available in"
               FigJam, Slides or Buzz is an error unless the allowlist names it. The skills target
               Figma Design files, where those members are undefined.
  3. members   member access in fenced JS/TS code, inline code and .js files (`node.foo`,
               `x.bar(`) must name a member declared somewhere in the typings, a JS builtin or a
               name the same file defines. Name level, not type level: it catches typos and
               invented members.
  4. calls     an inline code span that is a bare call (`getAnnotations()`) must name a member
               declared in the typings, a JS builtin or a name the same file defines.
  5. literals  a string literal assigned to or compared with a typed property
               (`layoutSizingHorizontal = 'FILL'`, `type: 'SOLID'`) must be in that property's
               literal union.

Exceptions live in scripts/api-allowlist.txt, one per line, each with a reason. Names marked
"absent" are cited by the skills because they do NOT exist: they must stay absent from the
typings, and every mention must sit on a line (or right below a line) that says so. Members
marked @deprecated in the typings are printed as notes, not errors.

Usage:
  python3 scripts/check_api.py                      # pinned typings, downloaded once and cached
  python3 scripts/check_api.py --version latest     # drift check against the newest release
  python3 scripts/check_api.py --typings-dir DIR    # an unpacked @figma/plugin-typings folder
Exit 0 when clean, 1 on any error, 2 when the typings or the allowlist cannot be loaded.
"""
from __future__ import annotations

import argparse
import base64
import fnmatch
import hashlib
import io
import json
import os
import re
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = Path(__file__).resolve().parent / 'api-allowlist.txt'
PACKAGE = '@figma/plugin-typings'
PINNED = '1.140.0'
# dist.integrity of the pinned tarball as published on registry.npmjs.org.
PINNED_INTEGRITY = 'sha512-xo2yz7QqaK0uHCowOmoqmT2SRKSIgSW00T1DxRTtB8/JSWzr8f800LSxFyp0LuSGd9OiiDC3TCI2payahrKP7g=='
REGISTRY = 'https://registry.npmjs.org/@figma/plugin-typings'
NODE_TYPES = ['BaseNode', 'SceneNode', 'PageNode', 'DocumentNode']
TARGET_EDITOR = 'Figma Design'

KINDS = {
    'absent': 'cited because it does not exist (figma.x chain, .member or bare call())',
    'editor': 'exists only in another editor; the skills mention it on purpose',
    'receiver': 'object outside the Plugin API; its members are not checked',
    'member': 'field of a payload outside the Plugin API; never checked',
    'global': 'figma.<x> that is not the plugin global',
}
NEGATION = re.compile(r"\b(?:not|never|no|instead|throws?|TypeError|isn't|doesn't|does not|cannot)\b", re.I)
FILE_EXT = {'md', 'sh', 'json', 'js', 'mjs', 'cjs', 'py', 'png', 'jpg', 'svg', 'pdf', 'html', 'bak',
            'out', 'err', 'plist', 'txt', 'yml', 'yaml', 'ts', 'tsx', 'jsx', 'css', 'log', 'zip',
            'fig', 'lock', 'toml', 'env'}
JS_BUILTINS = set('''
length push pop shift unshift slice splice map filter find findIndex findLast findLastIndex some
every reduce forEach includes indexOf lastIndexOf join concat sort reverse flat flatMap keys values
entries fill at from of isArray toString toFixed toUpperCase toLowerCase trim trimStart trimEnd
split replace replaceAll startsWith endsWith padStart padEnd repeat match matchAll test exec
search charAt charCodeAt codePointAt substring substr localeCompare normalize then catch finally
resolve reject all allSettled race any assign freeze create defineProperty getOwnPropertyNames
hasOwnProperty stringify parse round floor ceil abs min max pow sqrt random sign trunc hypot atan2
cos sin PI log warn info debug error now getTime toISOString set get has delete clear size add call
apply bind prototype constructor name message stack code isInteger isFinite isNaN parseInt
parseFloat MAX_SAFE_INTEGER EPSILON fromCharCode raw env argv exit cwd stdout stderr write end on
once emit readFileSync writeFileSync existsSync mkdirSync dirname basename extname toJSON valueOf
buffer byteLength subarray setTimeout setInterval clearTimeout clearInterval require
'''.split())

FENCE = re.compile(r'^\s*(```|~~~)\s*(\w*)')
INLINE = re.compile(r'`([^`\n]+)`')
CHAIN = re.compile(r'(?<![\w$./-])figma\.([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)(?![\w$]*/)')
MEMBER = re.compile(r'(?:(?<![\w$/.@-])([A-Za-z_$][\w$]*)|[)\]])\??\.([A-Za-z_$][\w$]*)(?![\w$-]|\.[a-z])')
BARE_CALL = re.compile(r'^(?:await\s+)?([a-z][a-z0-9]*[A-Z][A-Za-z0-9]*)\([^()]*\)$')
LITERAL = re.compile(r'\b([A-Za-z_$][\w$]*)\s*(?:===?|!==?|=|:)\s*([\'"])([A-Z][A-Z0-9_]*)\2')
LOCAL_DEF = re.compile(r'\b(?:const|let|var|function|class)\s+([A-Za-z_$][\w$]*)|[{,]\s*([A-Za-z_$][\w$]*)\s*:')
EDITORS = re.compile(r'only available in ([A-Za-z ]+?)\s*(?:\.|\n|$)')


class LoadError(Exception):
    """The typings or the allowlist could not be loaded (exit 2)."""


# ------------------------------------------------------------------------- typings
class Typings:
    """A shallow model of plugin-api.d.ts: interfaces, extends, members, aliases, literal unions."""

    def __init__(self, *texts: str):
        self.interfaces: dict[str, dict] = {}
        self.aliases: dict[str, str] = {}
        self.all_members: set[str] = set()
        self.literals: dict[str, set[str]] = {}
        self.literal_open: set[str] = set()
        self._pending: list = []  # (field, type) of inline object types
        for text in texts:
            self._parse(text)
        self._index_literals()

    def _parse(self, text: str) -> None:
        lines = text.split('\n')
        i, doc, cur, depth = 0, '', None, 0
        while i < len(lines):
            line, stripped = lines[i], lines[i].strip()
            if stripped.startswith('/*'):
                block = [line]
                while '*/' not in lines[i] and i + 1 < len(lines):
                    i += 1
                    block.append(lines[i])
                doc, i = '\n'.join(block), i + 1
                continue
            if stripped.startswith('//') or not stripped:
                i += 1
                continue
            if depth == 0:
                if re.match(r'(?:declare\s+)?interface\s+\w+', stripped):
                    header = stripped
                    while '{' not in header and i + 1 < len(lines):  # multi-line extends clause
                        i += 1
                        header += ' ' + lines[i].strip()
                    m = re.match(r'(?:declare\s+)?interface\s+(\w+)(?:<.*?>)?(?:\s+extends\s+(.+?))?\s*\{', header)
                    cur = m.group(1)
                    ext = [re.sub(r'<.*', '', e).strip() for e in re.split(r',(?![^<]*>)', m.group(2) or '') if e.strip()]
                    self.interfaces.setdefault(cur, {'extends': [], 'members': {}})['extends'] += ext
                    depth = header.count('{') - header.count('}')
                    if depth <= 0:
                        cur, depth = None, 0
                    doc, i = '', i + 1
                    continue
                m = re.match(r'(?:declare\s+)?type\s+(\w+)(?:<.*?>)?\s*=\s*(.*)', stripped)
                if m:
                    body = [m.group(2)]
                    while i + 1 < len(lines) and (lines[i + 1][:1] in (' ', '\t', '}', '|', '&')):
                        i += 1
                        body.append(lines[i].strip())
                    name, alias = m.group(1), '\n'.join(body)
                    self.aliases[name] = alias
                    for field, typ in re.findall(r'^\s*(?:readonly\s+)?(\w+)\??\s*:\s*([^;\n}]+)', alias, re.M):
                        self._add_member(name, field, 'prop', typ, '')
                    doc, i = '', i + 1
                    continue
                i += 1
                continue
            m = re.match(r'(?:readonly\s+)?([A-Za-z_$][\w$]*)(\?)?\s*([(<:])\s*(.*)', stripped)
            if m:
                kind = 'method' if m.group(3) in '(<' else 'prop'
                typ = m.group(4) if kind == 'prop' else ''
                if depth == 1:
                    self._add_member(cur, m.group(1), kind, typ, doc)
                else:  # field of an inline object type (options bags, ReadonlyArray<{...}>)
                    self.all_members.add(m.group(1))
                    if kind == 'prop':
                        self._pending.append((m.group(1), typ))
            depth += line.count('{') - line.count('}')
            if depth <= 0:
                cur, depth = None, 0
            doc, i = '', i + 1

    def _add_member(self, iface, name, kind, typ, doc):
        editors = EDITORS.search(doc)
        decl = (kind, typ.strip(), '@deprecated' in doc, editors.group(1).strip() if editors else '')
        self.interfaces.setdefault(iface, {'extends': [], 'members': {}})
        self.interfaces[iface]['members'].setdefault(name, []).append(decl)
        self.all_members.add(name)

    def _index_literals(self):
        decls = [(n, t) for i in self.interfaces.values() for n, ds in i['members'].items()
                 for k, t, _, _ in ds if k == 'prop'] + self._pending
        for name, typ in decls:
            values = self.expand_literals(typ)
            if values is None:
                self.literal_open.add(name)
            else:
                self.literals.setdefault(name, set()).update(values)

    def expand_literals(self, typ, seen=frozenset()):
        """The set of string literals when typ is a pure literal union, else None."""
        out = set()
        for part in (p.strip() for p in typ.replace('\n', ' ').split('|')):
            if not part or part in ('null', 'undefined'):
                continue
            if re.fullmatch(r"'[^']*'", part):
                out.add(part[1:-1])
            elif re.fullmatch(r'\w+', part) and part in self.aliases and part not in seen:
                sub = self.expand_literals(self.aliases[part], seen | {part})
                if sub is None:
                    return None
                out |= sub
            else:
                return None
        return out or None

    def type_names(self, typ):
        typ = re.sub(r'\b(?:readonly|ReadonlyArray|Array|Promise)\b', ' ', typ)
        return [t for t in re.findall(r'[A-Z]\w*', typ) if t in self.interfaces or t in self.aliases]

    def members_of(self, names, seen=None):
        seen = set() if seen is None else seen
        out: dict[str, list] = {}
        for n in names:
            if n in seen:
                continue
            seen.add(n)
            if n in self.interfaces:
                sources = [self.members_of(self.interfaces[n]['extends'], seen), self.interfaces[n]['members']]
            elif n in self.aliases:
                sources = [self.members_of(self.type_names(self.aliases[n]), seen)]
            else:
                continue
            for src in sources:
                for k, v in src.items():
                    out.setdefault(k, []).extend(v)
        return out

    def resolve_chain(self, segments):
        """dict(ok, missing, deprecated, editor) for figma.<segments...>."""
        types, is_array = ['PluginAPI'], False
        out = {'ok': True, 'missing': None, 'deprecated': None, 'editor': None}
        for idx, seg in enumerate(segments):
            prefix = 'figma.' + '.'.join(segments[:idx + 1])
            if is_array and seg in JS_BUILTINS:
                return out
            members = self.members_of(types)
            if seg not in members:
                out.update(ok=False, missing=prefix)
                return out
            decls = members[seg]
            if all(d[2] for d in decls):
                out['deprecated'] = prefix
            editors = {d[3] for d in decls}
            if '' not in editors and not any(TARGET_EDITOR in e for e in editors):
                out['editor'] = (prefix, ' / '.join(sorted(editors)))
            if any(d[0] == 'method' for d in decls):
                return out                      # what follows is on the return value
            typ = ' | '.join(d[1] for d in decls)
            is_array = bool(re.search(r'\[\]|ReadonlyArray<|Array<', typ))
            types = self.type_names(typ)
            if not types and not is_array:
                return out                      # string, number, symbol: nothing to walk
        return out


def unwrap_global(text: str) -> str:
    """index.d.ts nests interfaces in `declare global { }`; dedent them to top level."""
    m = re.search(r'declare global \{\n(.*)\n\}\s*// declare global', text, re.S)
    return re.sub(r'^  ', '', m.group(1), flags=re.M) if m else text


def cache_dir() -> Path:
    if os.environ.get('FIGMA_TYPINGS_CACHE'):
        return Path(os.environ['FIGMA_TYPINGS_CACHE'])
    base = os.environ.get('XDG_CACHE_HOME') or str(Path.home() / '.cache')
    return Path(base) / 'figma-maxxing'


def integrity_of(data: bytes) -> str:
    return 'sha512-' + base64.b64encode(hashlib.sha512(data).digest()).decode()


def fetch(url: str, timeout: int) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 (fixed https registry URL)
        return r.read()


def tarball(version: str) -> tuple[bytes, str]:
    """The verified npm tarball for version ('latest' resolves through the registry)."""
    if version == PINNED:
        expected = PINNED_INTEGRITY
    else:
        meta = json.loads(fetch(f'{REGISTRY}/{version}', 30))
        version, expected = meta['version'], meta['dist']['integrity']
    cached = cache_dir() / f'plugin-typings-{version}.tgz'
    if cached.is_file() and integrity_of(cached.read_bytes()) == expected:
        return cached.read_bytes(), version
    data = fetch(f'{REGISTRY}/-/plugin-typings-{version}.tgz', 60)
    if integrity_of(data) != expected:
        raise LoadError(f'{PACKAGE}@{version}: tarball integrity mismatch, refusing to use it')
    try:
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(data)
    except OSError:
        pass  # a read-only cache only costs a download next time
    return data, version


def load_typings(version: str, directory: str | None):
    try:
        if directory:
            d = Path(directory)
            api, idx = (d / 'plugin-api.d.ts').read_text(), (d / 'index.d.ts').read_text()
            version = json.loads((d / 'package.json').read_text()).get('version', directory)
        else:
            data, version = tarball(version)
            with tarfile.open(fileobj=io.BytesIO(data)) as tar:
                api = tar.extractfile('package/plugin-api.d.ts').read().decode()
                idx = tar.extractfile('package/index.d.ts').read().decode()
    except LoadError:
        raise
    except (OSError, ValueError, KeyError, tarfile.TarError) as exc:
        raise LoadError(f'cannot load {PACKAGE} {version}: {exc}') from exc
    return Typings(api, unwrap_global(idx)), version


# ------------------------------------------------------------------------- allowlist
class Allowlist:
    """scripts/api-allowlist.txt: `kind identifier [in=glob] reason`, one entry per line."""

    def __init__(self, path: Path):
        self.entries: list[dict] = []
        try:
            text = path.read_text()
        except OSError as exc:
            raise LoadError(f'cannot read allowlist {path}: {exc}') from exc
        for n, raw in enumerate(text.split('\n'), 1):
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split(None, 2)
            scope = None
            if len(parts) == 3 and parts[2].startswith('in='):
                scope_and_reason = parts[2].split(None, 1)
                scope = scope_and_reason[0][3:]
                parts = parts[:2] + scope_and_reason[1:]
            if len(parts) < 3 or parts[0] not in KINDS:
                raise LoadError(f'{path.name}:{n}: expected "<{"|".join(KINDS)}> <identifier> <reason>"')
            if len(parts[2].split()) < 3:
                raise LoadError(f'{path.name}:{n}: the reason for {parts[1]} needs at least three words')
            self.entries.append({'kind': parts[0], 'id': parts[1], 'scope': scope, 'reason': parts[2],
                                 'line': n, 'used': 0})

    def find(self, kind: str, ident: str, rel: str):
        for e in self.entries:
            if e['kind'] == kind and e['id'] == ident and (e['scope'] is None or fnmatch.fnmatch(rel, e['scope'])):
                e['used'] += 1
                return e
        return None

    def ids(self, kind: str) -> set[str]:
        return {e['id'] for e in self.entries if e['kind'] == kind}


# ------------------------------------------------------------------------- sources
def source_files(root: Path) -> list[Path]:
    skills = root / 'skills'
    return (sorted(skills.rglob('*.md')) + sorted(skills.rglob('*.js'))
            + sorted((root / 'hooks').glob('*.py')))


def code_lines(path: Path, text: str):
    """(line_no, code) for JS files, fenced JS/TS code, and inline code spans (md and py)."""
    if path.suffix in ('.js', '.mjs'):
        for n, line in enumerate(text.split('\n'), 1):
            yield n, re.sub(r'(?<!:)//.*$', '', line), False
        return
    fence, lang = None, ''
    for n, line in enumerate(text.split('\n'), 1):
        if path.suffix == '.md':
            m = FENCE.match(line)
            if m and fence is None:
                fence, lang = m.group(1), m.group(2).lower()
                continue
            if fence and line.strip().startswith(fence):
                fence = None
                continue
            if fence:
                if lang in ('', 'js', 'javascript', 'ts', 'typescript', 'jsx', 'tsx'):
                    yield n, re.sub(r'(?<!:)//.*$', '', line), False
                continue
        for span in INLINE.findall(line):
            if ' ' in span and '(' not in span and '=' not in span:
                continue  # prose or a shell command quoted inline
            yield n, span, True


def file_locals(text: str) -> set[str]:
    names = {a or b for a, b in LOCAL_DEF.findall(text)}
    names |= set(re.findall(r'^\s*(?:async\s+)?([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{', text, re.M))
    return names


def negated(lines: list[str], n: int) -> bool:
    """True when line n (1-based) or the line above it says the name does not work."""
    return bool(NEGATION.search(lines[n - 1]) or (n > 1 and NEGATION.search(lines[n - 2])))


# ------------------------------------------------------------------------- scan
def scan(root: Path, t: Typings, allow: Allowlist) -> dict:
    files = source_files(root)
    r = {k: [] for k in ('missing_chains', 'editor_only', 'missing_members', 'missing_calls',
                         'bad_literals', 'absent_misuse', 'absent_stale', 'deprecated')}
    seen = {'chains': set(), 'members': set(), 'calls': set()}
    mentions = {'chains': 0, 'members': 0, 'calls': 0, 'literals': 0}
    receivers, foreign_members = allow.ids('receiver'), allow.ids('member')
    for path in files:
        rel, text = str(path.relative_to(root)), path.read_text(errors='replace')
        lines, defined = text.split('\n'), file_locals(text)
        for n, line in enumerate(lines, 1):                           # tiers 1 and 2
            for m in CHAIN.finditer(line):
                segs = m.group(1).split('.')
                full = 'figma.' + m.group(1)
                if allow.find('global', 'figma.' + segs[0], rel):
                    continue
                prefixes = ['figma.' + '.'.join(segs[:k]) for k in range(1, len(segs) + 1)]
                absent = next((p for p in prefixes if allow.find('absent', p, rel)), None)
                if absent:
                    if not negated(lines, n):
                        r['absent_misuse'].append(f'{rel}:{n} {absent} is cited as absent but used as if it existed')
                    continue
                seen['chains'].add(full)
                mentions['chains'] += 1
                res = t.resolve_chain(segs)
                if not res['ok']:
                    r['missing_chains'].append(f'{rel}:{n} {full} (no such member: {res["missing"]})')
                    continue
                if res['editor'] and not allow.find('editor', res['editor'][0], rel):
                    r['editor_only'].append(f'{rel}:{n} {res["editor"][0]} is only available in {res["editor"][1]}')
                if res['deprecated']:
                    r['deprecated'].append(f'{rel}:{n} {res["deprecated"]}')
        for n, code, inline in code_lines(path, text):                # tiers 3, 4 and 5
            call = BARE_CALL.match(code.strip()) if inline else None
            if call:
                name = call.group(1)
                if allow.find('absent', name + '()', rel):
                    if not negated(lines, n):
                        r['absent_misuse'].append(f'{rel}:{n} {name}() is cited as absent but used as if it existed')
                elif not (name in t.all_members or name in JS_BUILTINS or name in defined):
                    r['missing_calls'].append(f'{rel}:{n} {name}()')
                seen['calls'].add(name)
                mentions['calls'] += 1
            for m in MEMBER.finditer(code):
                recv, name = m.group(1), m.group(2)
                if recv == 'figma' or recv in receivers or name in FILE_EXT or name in foreign_members \
                        or (recv or '').isdigit():
                    if recv in receivers:
                        allow.find('receiver', recv, rel)
                    elif name in foreign_members:
                        allow.find('member', name, rel)
                    continue
                seen['members'].add(name)
                mentions['members'] += 1
                if allow.find('absent', '.' + name, rel):
                    if not negated(lines, n):
                        r['absent_misuse'].append(f'{rel}:{n} .{name} is cited as absent but used as if it existed')
                    continue
                if name in t.all_members or name in JS_BUILTINS or name in defined:
                    continue
                r['missing_members'].append(f'{rel}:{n} {recv or "<expr>"}.{name}')
            for m in LITERAL.finditer(code):
                prop, value = m.group(1), m.group(3)
                if prop in t.literals and prop not in t.literal_open:
                    mentions['literals'] += 1
                    if value not in t.literals[prop]:
                        allowed = ' | '.join(sorted(t.literals[prop]))
                        r['bad_literals'].append(f"{rel}:{n} {prop} = '{value}' not in {allowed[:140]}")
    node_members, api_members = t.members_of(NODE_TYPES), t.members_of(['PluginAPI'])
    for e in allow.entries:                                           # absent claims stay true
        if e['kind'] != 'absent':
            continue
        ident = e['id']
        if ident.startswith('figma.'):
            exists = t.resolve_chain(ident.split('.')[1:])['ok']
        else:
            name = ident.strip('.()')
            exists = name in node_members or (ident.endswith('()') and name in api_members)
        if exists:
            r['absent_stale'].append(f'{ident} now exists in the typings: update the skill text and '
                                     f'api-allowlist.txt line {e["line"]}')
    r['unused'] = [f'{e["kind"]} {e["id"]} (line {e["line"]})' for e in allow.entries if not e['used']]
    r['stats'] = {'files': len(files), 'chains': len(seen['chains']), 'chain_mentions': mentions['chains'],
                  'members': len(seen['members']), 'member_mentions': mentions['members'],
                  'calls': len(seen['calls']), 'call_mentions': mentions['calls'],
                  'literals': mentions['literals'], 'allowlist': len(allow.entries)}
    return r


ERROR_KEYS = ('missing_chains', 'editor_only', 'missing_members', 'missing_calls', 'bad_literals',
              'absent_misuse', 'absent_stale')


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--root', default=str(ROOT), help='repository root to scan (default: this repo)')
    ap.add_argument('--allowlist', default=str(ALLOWLIST), help='allowlist file (default: scripts/api-allowlist.txt)')
    ap.add_argument('--typings-dir', help=f'unpacked {PACKAGE} folder (offline)')
    ap.add_argument('--version', default=PINNED, help=f'npm version or "latest" (default {PINNED})')
    ap.add_argument('--json', action='store_true', help='print the full result as JSON')
    ap.add_argument('--strict', action='store_true', help='also fail on allowlist entries nothing uses')
    args = ap.parse_args(argv)
    try:
        t, version = load_typings(args.version, args.typings_dir)
        allow = Allowlist(Path(args.allowlist))
    except LoadError as exc:
        print(f'check_api: {exc}', file=sys.stderr)
        return 2
    r = scan(Path(args.root), t, allow)
    errors = [f'{k}: {v}' for k in ERROR_KEYS for v in r[k]]
    if args.strict:
        errors += [f'unused_allowlist: {u}' for u in r['unused']]
    s = r['stats']
    if args.json:
        print(json.dumps({'typings': version, **s, 'errors': errors,
                          'deprecated': sorted(set(r['deprecated'])), 'unused_allowlist': r['unused']}, indent=2))
    else:
        for e in errors:
            print('ERROR', e)
        for d in sorted(set(r['deprecated'])):
            print('note deprecated:', d)
        for u in ([] if args.strict else r['unused']):
            print('note unused allowlist entry:', u)
        print(f"check_api: {PACKAGE} {version}, {s['files']} files, "
              f"{s['chains']} figma.* chains ({s['chain_mentions']} mentions), "
              f"{s['members']} member names ({s['member_mentions']} mentions), "
              f"{s['calls']} bare calls ({s['call_mentions']} mentions), "
              f"{s['literals']} enum literals, {s['allowlist']} allowlist entries: "
              f"{len(errors)} error{'s' if len(errors) != 1 else ''}")
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
