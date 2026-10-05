"""Structure checks: every skill is valid, every link resolves, nothing private or off-style ships."""
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / 'skills'
sys.path.insert(0, str(ROOT / 'scripts'))
import count_claims  # noqa: E402  (scripts/ is not a package)
import release_notes  # noqa: E402

# Frontmatter keys the Agent Skills spec (agentskills.io/specification) allows.
SPEC_KEYS = {'name', 'description', 'license', 'compatibility', 'metadata', 'allowed-tools'}
EXPECTED_SKILLS = {
    'figma-canon', 'figma-bridge-doctor', 'figma-orient', 'figma-preflight', 'figma-click-flow',
    'figma-comment-fix-loop', 'figma-handoff-gate', 'figma-slop-check',
}
TEXT_SUFFIXES = {'.md', '.py', '.sh', '.js', '.mjs', '.json', '.yml', '.yaml', '.txt', '.svg', '.cff', '.toml',
                 '.html', '.template', ''}


def tracked_text_files():
    listed = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard'],
                            cwd=ROOT, capture_output=True, text=True, check=True).stdout.split('\n')
    for name in filter(None, listed):
        path = ROOT / name
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            yield path


def _shipped_files(pattern: str) -> list:
    """Tracked and untracked, not ignored, files that match a git pathspec such as '*.gif'."""
    listed = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard', pattern],
                            cwd=ROOT, capture_output=True, text=True, check=True).stdout.split('\n')
    return [name for name in listed if name and (ROOT / name).is_file()]


def frontmatter(path: Path) -> dict:
    text = path.read_text()
    match = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    assert match, f'{path}: missing frontmatter'
    return yaml.safe_load(match.group(1))


def slug(heading: str) -> str:
    """GitHub heading anchor: lowercase, drop punctuation, spaces become hyphens."""
    text = re.sub(r'[`*]', '', heading.strip().lower())
    text = re.sub(r'[^\w\- ]', '', text)
    return text.replace(' ', '-')


def anchors(path: Path) -> set:
    found, in_code = set(), False
    for line in path.read_text().split('\n'):
        if line.startswith('```'):
            in_code = not in_code
        elif not in_code and re.match(r'^#{1,6} ', line):
            found.add(slug(line.lstrip('#')))
    return found


class SkillTests(unittest.TestCase):
    def test_expected_skills_exist(self):
        on_disk = {p.parent.name for p in SKILLS.glob('*/SKILL.md')}
        self.assertEqual(on_disk, EXPECTED_SKILLS)

    def test_frontmatter(self):
        for skill_md in SKILLS.glob('*/SKILL.md'):
            with self.subTest(skill=skill_md.parent.name):
                meta = frontmatter(skill_md)
                self.assertEqual(meta['name'], skill_md.parent.name)
                self.assertRegex(meta['name'], r'^[a-z0-9]+(-[a-z0-9]+)*$')
                self.assertLessEqual(len(meta['name']), 64)
                self.assertIsInstance(meta['description'], str)
                self.assertGreaterEqual(len(meta['description']), 120)
                self.assertLessEqual(len(meta['description']), 1024)
                self.assertNotRegex(meta['description'], r'[<>]')
                self.assertEqual(meta['license'], 'MIT')
                self.assertLessEqual(set(meta), SPEC_KEYS, 'keys outside the agentskills.io spec')
                if 'compatibility' in meta:
                    self.assertIsInstance(meta['compatibility'], str)
                    self.assertTrue(1 <= len(meta['compatibility']) <= 500)
                if 'metadata' in meta:
                    self.assertIsInstance(meta['metadata'], dict)
                    for key, value in meta['metadata'].items():
                        self.assertIsInstance(key, str)
                        self.assertIsInstance(value, str, f'metadata.{key} must be a string')
                if 'allowed-tools' in meta:
                    self.assertIsInstance(meta['allowed-tools'], str)

    def test_versions_match(self):
        """Every version field equals .claude-plugin/plugin.json (SKILL.md, CITATION.cff, JSON manifests)."""
        expected = json.loads((ROOT / '.claude-plugin/plugin.json').read_text())['version']
        found = dict(release_notes.versions())
        for path in tracked_text_files():
            if path.suffix == '.json' and 'tests' not in path.parts:
                data = json.loads(path.read_text())
                if isinstance(data, dict) and isinstance(data.get('version'), str):
                    found[str(path.relative_to(ROOT))] = data['version']
        self.assertEqual(len([k for k in found if k.endswith('SKILL.md')]), len(EXPECTED_SKILLS))
        for where, version in found.items():
            with self.subTest(file=where):
                self.assertEqual(version, expected)

    def test_skill_body_size(self):
        for skill_md in SKILLS.glob('*/SKILL.md'):
            with self.subTest(skill=skill_md.parent.name):
                self.assertLessEqual(len(skill_md.read_text().split('\n')), 500)

    def test_relative_links_resolve(self):
        """Markdown links, reference definitions and HTML src/srcset/href attributes."""
        link = re.compile(r'\]\(([^)#\s]+)(#[^)\s]*)?\)|^\[[^\]]+\]:\s+([^#\s]+)(#\S*)?'
                          r'|\b(?:src|srcset|href)="([^"#\s]+)(#[^"]*)?"', re.M)
        for path in tracked_text_files():
            if path.suffix != '.md':
                continue
            for groups in link.findall(path.read_text()):
                target, anchor = next((groups[i], groups[i + 1]) for i in (0, 2, 4) if groups[i])
                if re.match(r'^[a-z]+:', target):
                    continue
                resolved = (path.parent / target).resolve()
                with self.subTest(file=str(path.relative_to(ROOT)), link=target):
                    self.assertTrue(resolved.exists(), f'broken link {target}')
                    if anchor and resolved.suffix == '.md':
                        self.assertIn(anchor[1:], anchors(resolved), f'broken anchor {target}{anchor}')

    def test_reference_mentions_resolve(self):
        mention = re.compile(r'`?(?:([a-z0-9-]+)/)?references/([a-z0-9-]+\.(?:md|js))')
        for path in SKILLS.rglob('*.md'):
            skill = path.relative_to(SKILLS).parts[0]
            for other, name in mention.findall(path.read_text()):
                with self.subTest(file=str(path.relative_to(ROOT)), ref=name):
                    self.assertTrue((SKILLS / (other or skill) / 'references' / name).is_file(),
                                    f'{other or skill}/references/{name} does not exist')

    def test_cross_skill_names_exist(self):
        named = re.compile(r'`(figma-[a-z-]+)`')
        allowed = EXPECTED_SKILLS | {'figma-console', 'figma-console-mcp', 'figma-canon-precheck',
                                     'figma-maxxing', 'figma-status', 'figma-map', 'figma-developer-mcp',
                                     'figma-mcp-direct'}
        for path in SKILLS.rglob('*.md'):
            for name in named.findall(path.read_text()):
                with self.subTest(file=str(path.relative_to(ROOT)), name=name):
                    self.assertIn(name, allowed)

    def test_gotcha_count_claim(self):
        """Both READMEs cite the gotcha count, and what they cite is true (scripts/count_claims.py)."""
        total = count_claims.counts()['gotchas']
        self.assertGreater(total, 80)
        for name in ('README.md', 'docs/README.pt-BR.md'):
            text = (ROOT / name).read_text()
            cited = [c for c in count_claims.claims(text) if c[0] in ('gotchas', 'gotchas_floor')]
            with self.subTest(file=name):
                self.assertTrue(cited, f'{name} does not cite the gotcha count')
                self.assertEqual(count_claims.check_text(text, count_claims.counts()), [])

    def test_hook_references_resolve(self):
        text = (ROOT / 'hooks/figma-canon-precheck.py').read_text()
        refs = re.findall(r"'([a-z-]+\.md)#([^']+)'", text)
        self.assertGreaterEqual(len(refs), 10)
        for name, anchor in refs:
            with self.subTest(ref=f'{name}#{anchor}'):
                target = SKILLS / 'figma-canon/references' / name
                self.assertTrue(target.is_file())
                self.assertIn(anchor, anchors(target))


class HygieneTests(unittest.TestCase):
    """Generic patterns only. Anything that names a real project never belongs in a public test."""

    def test_no_private_paths_keys_or_tokens(self):
        patterns = {
            'home path': re.compile(r'/Users/[A-Za-z]|/home/[a-z][a-z0-9_-]*/|\b[A-Za-z]:\\+Users\\'),
            'figma token': re.compile(r'figd_(?!YOUR_)[A-Za-z0-9_-]{20,}'),
            'figma file url': re.compile(r'figma\.com/(?:design|file|proto|board|slides|make)/[A-Za-z0-9]{15,}'),
            'figma REST file path': re.compile(r'/v1/files/[A-Za-z0-9]{15,}'),
            'github token': re.compile(r'\bgh[pousr]_[A-Za-z0-9]{36}\b|\bgithub_pat_[A-Za-z0-9_]{50,}'),
            'anthropic key': re.compile(r'\bsk-ant-[A-Za-z0-9_-]{20,}'),
            'openai key': re.compile(r'\bsk-(?:proj-)?[A-Za-z0-9]{32,}'),
            'slack token': re.compile(r'\bxox[abprs]-[A-Za-z0-9-]{10,}'),
            'aws key id': re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
            'private key': re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
            'memory pointer': re.compile(r'\[\[[^\]]+\]\]|feedback-[a-z0-9-]+\.md|project_figma_map'),
        }
        for path in tracked_text_files():
            if path.parts[-2:] == ('tests', 'test_repo.py'):
                continue
            text = path.read_text(errors='replace')
            for label, pattern in patterns.items():
                with self.subTest(file=str(path.relative_to(ROOT)), check=label):
                    hit = pattern.search(text)
                    self.assertIsNone(hit, f'{label} at line {text.count(chr(10), 0, hit.start()) + 1}' if hit else '')

    def test_no_file_key_shaped_strings(self):
        """Figma file keys are 22 letters and digits. Any such mixed-case token is suspect."""
        token = re.compile(r'(?<![A-Za-z0-9_/+=.-])[A-Za-z0-9]{22}(?![A-Za-z0-9_/+=-])')
        placeholder = re.compile(r'YOUR|EXAMPLE|Example|example|abc123|xxxx|XXXX|0000')
        for path in tracked_text_files():
            text = path.read_text(errors='replace')
            hits = [t for t in token.findall(text) if re.search(r'[A-Z]', t) and re.search(r'[a-z]', t)
                    and re.search(r'\d', t) and not placeholder.search(t)]
            with self.subTest(file=str(path.relative_to(ROOT))):
                self.assertEqual([h[:4] + '...' for h in hits], [])

    def test_images_carry_no_text_metadata(self):
        """PNG text and EXIF chunks can hold a username, a path or a tool's prompt."""
        for name in _shipped_files('*.png'):
            data = (ROOT / name).read_bytes()
            self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n', name)
            chunks, i = [], 8
            while i + 8 <= len(data):
                length, kind = struct.unpack('>I4s', data[i:i + 8])
                chunks.append(kind.decode('latin-1'))
                i += 12 + length
            with self.subTest(file=name):
                self.assertEqual([c for c in chunks if c in ('tEXt', 'zTXt', 'iTXt', 'eXIf')], [])

    def test_gifs_carry_no_text_metadata(self):
        """A GIF comment, plain text or XMP extension can hold a username, a path or a prompt.
        Only the NETSCAPE2.0 loop extension and graphic control blocks are allowed."""
        for name in _shipped_files('*.gif'):
            data = (ROOT / name).read_bytes()
            self.assertIn(data[:6], (b'GIF87a', b'GIF89a'), name)
            found, i = [], 13
            if data[10] & 0x80:
                i += 3 * 2 ** ((data[10] & 7) + 1)
            while i < len(data) and data[i] != 0x3B:
                if data[i] == 0x21:
                    label, i = data[i + 1], i + 2
                    if label == 0xFF and data[i + 1:i + 12] != b'NETSCAPE2.0':
                        found.append('application ' + data[i + 1:i + 12].decode('latin-1'))
                    elif label in (0xFE, 0x01):
                        found.append({0xFE: 'comment', 0x01: 'plain text'}[label])
                elif data[i] == 0x2C:
                    packed, i = data[i + 9], i + 10
                    if packed & 0x80:
                        i += 3 * 2 ** ((packed & 7) + 1)
                    i += 1  # LZW minimum code size
                else:
                    self.fail(f'{name}: unexpected GIF block 0x{data[i]:02x} at offset {i}')
                while data[i]:  # data sub-blocks until the zero terminator
                    i += data[i] + 1
                i += 1
            with self.subTest(file=name):
                self.assertEqual(found, [])

    def test_videos_carry_no_metadata_tags(self):
        """MP4 tags can hold a location, a device, an author or a creation tool.
        Only the encoder tag ffmpeg writes (©too) is allowed."""
        containers = {'moov', 'trak', 'mdia', 'minf', 'udta', 'meta', 'ilst'}
        for name in _shipped_files('*.mp4'):
            data = (ROOT / name).read_bytes()
            found = []

            def walk(start, end, parent):
                i = start
                while i + 8 <= end:
                    size, kind = struct.unpack('>I4s', data[i:i + 8])
                    header = 8
                    if size == 1:
                        size, header = struct.unpack('>Q', data[i + 8:i + 16])[0], 16
                    elif size == 0:
                        size = end - i
                    if size < header:
                        break
                    atom = kind.decode('latin-1')
                    if parent == 'ilst' and atom != chr(0xA9) + 'too':
                        found.append('ilst/' + atom)
                    elif atom in (chr(0xA9) + 'xyz', 'loci', 'keys', 'XMP_', 'uuid'):
                        found.append(atom)
                    if atom in containers:
                        inner = i + header
                        if atom == 'meta' and data[inner:inner + 4] == b'\x00\x00\x00\x00':
                            inner += 4  # ISO meta is a full box; QuickTime meta is not
                        walk(inner, i + size, atom)
                    i += size

            walk(0, len(data), '')
            with self.subTest(file=name):
                self.assertEqual(found, [])

    def test_house_style(self):
        dash = re.compile('[' + chr(0x2014) + chr(0x2013) + ']')
        curly = re.compile('[' + ''.join(map(chr, (0x2018, 0x2019, 0x201C, 0x201D))) + ']')
        emoji = re.compile('[' + chr(0x1F300) + '-' + chr(0x1FAFF) + ''.join(map(chr, (0x2705, 0x274C, 0x26A0, 0x2B50, 0x2728))) + ']')
        for path in tracked_text_files():
            text = path.read_text(errors='replace')
            rel = str(path.relative_to(ROOT))
            for label, pattern in (('dash', dash), ('emoji', emoji)):
                with self.subTest(file=rel, check=label):
                    hit = pattern.search(text)
                    self.assertIsNone(hit, f'{label} at offset {hit.start() if hit else 0}')
            if path.suffix == '.md' and 'skills' in path.parts:
                lines = [l for l in text.split('\n') if curly.search(l) and '`' not in l and 'includes(' not in l]
                with self.subTest(file=rel, check='curly quotes'):
                    self.assertEqual(lines, [])

    def test_plugin_manifests(self):
        plugin = json.loads((ROOT / '.claude-plugin/plugin.json').read_text())
        market = json.loads((ROOT / '.claude-plugin/marketplace.json').read_text())
        self.assertEqual(plugin['name'], 'figma-maxxing')
        self.assertEqual(plugin['license'], 'MIT')
        entry = market['plugins'][0]
        self.assertEqual(entry['name'], plugin['name'])
        self.assertNotIn('version', entry)
        self.assertRegex(plugin['version'], r'^\d+\.\d+\.\d+$')

    def test_workflows_pin_actions_and_permissions(self):
        """Every action is pinned to a full commit SHA with a version comment; every workflow
        declares its token permissions and never asks for write-all."""
        workflows = sorted((ROOT / '.github/workflows').glob('*.yml'))
        self.assertTrue(workflows)
        pinned = re.compile(r'^\s*(?:-\s+)?uses:\s+[\w.-]+/[\w./-]+@[0-9a-f]{40} # v\d+(\.\d+)*\s*$')
        for path in workflows:
            text = path.read_text()
            with self.subTest(workflow=path.name):
                self.assertIn('permissions', yaml.safe_load(text))
                self.assertNotIn('write-all', text)
                for line in text.split('\n'):
                    if re.match(r'^\s*(?:-\s+)?uses:', line):
                        self.assertRegex(line, pinned)

    def test_shell_scripts_parse(self):
        for path in tracked_text_files():
            if path.suffix == '.sh':
                with self.subTest(file=str(path.relative_to(ROOT))):
                    result = subprocess.run(['bash', '-n', str(path)], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
