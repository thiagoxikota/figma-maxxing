"""Structure checks: every skill is valid, every link resolves, nothing private or off-style ships."""
import json
from pathlib import Path
import re
import subprocess
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / 'skills'
EXPECTED_SKILLS = {
    'figma-canon', 'figma-bridge-doctor', 'figma-orient', 'figma-preflight', 'figma-click-flow',
    'figma-comment-fix-loop', 'figma-handoff-gate', 'figma-slop-check',
}
TEXT_SUFFIXES = {'.md', '.py', '.sh', '.js', '.mjs', '.json', '.yml', '.yaml', '.txt', '.svg', ''}


def tracked_text_files():
    listed = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard'],
                            cwd=ROOT, capture_output=True, text=True, check=True).stdout.split('\n')
    for name in filter(None, listed):
        path = ROOT / name
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            yield path


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
                self.assertLessEqual(set(meta), {'name', 'description', 'license', 'metadata'})

    def test_skill_body_size(self):
        for skill_md in SKILLS.glob('*/SKILL.md'):
            with self.subTest(skill=skill_md.parent.name):
                self.assertLessEqual(len(skill_md.read_text().split('\n')), 500)

    def test_relative_links_resolve(self):
        link = re.compile(r'\]\(([^)#\s]+)(#[^)\s]*)?\)')
        for path in tracked_text_files():
            if path.suffix != '.md':
                continue
            for target, anchor in link.findall(path.read_text()):
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
        refs = SKILLS / 'figma-canon/references'
        headings = [line for name in ('plugin-api-anomalies.md', 'field-notes.md')
                    for line in (refs / name).read_text().split('\n') if line.startswith('## ')]
        gotchas = [h for h in headings if not h.startswith(('## Research vs', '## Anti-patterns'))]
        self.assertGreater(len(gotchas), 80)
        self.assertIn('more than 80', (ROOT / 'README.md').read_text())
        self.assertIn('mais de 80', (ROOT / 'docs/README.pt-BR.md').read_text())

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
            'home path': re.compile(r'/Users/[a-z]'),
            'figma token': re.compile(r'figd_(?!YOUR_)[A-Za-z0-9_-]{20,}'),
            'figma file url': re.compile(r'figma\.com/(?:design|file|proto|board)/[A-Za-z0-9]{15,}'),
            'memory pointer': re.compile(r'\[\[[^\]]+\]\]|feedback-[a-z0-9-]+\.md|project_figma_map'),
        }
        for path in tracked_text_files():
            if path.parts[-2:] == ('tests', 'test_repo.py'):
                continue
            text = path.read_text(errors='replace')
            for label, pattern in patterns.items():
                with self.subTest(file=str(path.relative_to(ROOT)), check=label):
                    self.assertIsNone(pattern.search(text))

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

    def test_shell_scripts_parse(self):
        for path in tracked_text_files():
            if path.suffix == '.sh':
                with self.subTest(file=str(path.relative_to(ROOT))):
                    result = subprocess.run(['bash', '-n', str(path)], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
