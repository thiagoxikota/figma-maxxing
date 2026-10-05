"""The scripts in scripts/, exercised offline: the API checker, the release build, the claim counter."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


check_api = load('check_api')
build_dist = load('build_dist')
count_claims = load('count_claims')
release_notes = load('release_notes')

# A tiny stand-in for @figma/plugin-typings, shaped like the real plugin-api.d.ts.
TYPINGS = """
interface PluginAPI {
  readonly annotations: AnnotationsAPI
  readonly currentPage: PageNode
  getNodeByIdAsync(id: string): Promise<BaseNode | null>
  /**
   * @deprecated Use getNodeByIdAsync instead.
   */
  getNodeById(id: string): BaseNode | null
  /**
   * Note: This API is only available in FigJam
   */
  createConnector(): ConnectorNode
  createFrame(): FrameNode
}
interface AnnotationsAPI {
  getAnnotationCategoriesAsync(): Promise<AnnotationCategory[]>
}
interface AnnotationCategory {
  readonly id: string
}
interface BaseNodeMixin {
  readonly id: string
  name: string
  remove(): void
}
interface LayoutMixin {
  layoutSizingHorizontal: 'FIXED' | 'HUG' | 'FILL'
}
interface AnnotationsMixin {
  annotations: ReadonlyArray<Annotation>
}
interface Annotation {
  readonly label?: string
}
interface FrameNode extends BaseNodeMixin, LayoutMixin, AnnotationsMixin {
  readonly type: 'FRAME'
  appendChild(child: SceneNode): void
}
interface PageNode extends BaseNodeMixin {
  readonly type: 'PAGE'
  selection: ReadonlyArray<SceneNode>
}
interface ConnectorNode extends BaseNodeMixin {
  readonly type: 'CONNECTOR'
}
type BaseNode = PageNode | SceneNode
type SceneNode = FrameNode | ConnectorNode
"""

CLEAN_SKILL = """---
name: demo
---
# Demo

Read with `figma.getNodeByIdAsync(id)`, then `figma.currentPage.selection`.

```javascript
const frame = figma.createFrame();
frame.layoutSizingHorizontal = 'FILL';
frame.annotations = [{ label: 'x' }];
const page = figma.currentPage;
return page.selection.map(n => n.id);
```
"""


class ApiCheckTests(unittest.TestCase):
    """Synthetic typings and skill trees: each tier must catch its kind of mistake."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.typings = base / 'typings'
        self.typings.mkdir()
        (self.typings / 'plugin-api.d.ts').write_text(TYPINGS)
        (self.typings / 'index.d.ts').write_text('declare const figma: PluginAPI\n')
        (self.typings / 'package.json').write_text('{"version": "0.0.0-test"}')
        self.root = base / 'repo'
        (self.root / 'skills/demo').mkdir(parents=True)
        (self.root / 'hooks').mkdir()
        self.allowlist = base / 'allow.txt'
        self.allowlist.write_text('')

    def tearDown(self):
        self.tmp.cleanup()

    def run_check(self, skill_text, allow='', hook=None, strict=False):
        (self.root / 'skills/demo/SKILL.md').write_text(skill_text)
        if hook is not None:
            (self.root / 'hooks/precheck.py').write_text(hook)
        self.allowlist.write_text(allow)
        args = ['--root', str(self.root), '--typings-dir', str(self.typings),
                '--allowlist', str(self.allowlist), '--json'] + (['--strict'] if strict else [])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check_api.main(args)
        return code, json.loads(out.getvalue())

    def assert_error(self, result, kind, fragment):
        code, data = result
        self.assertEqual(code, 1, data)
        self.assertTrue(any(e.startswith(kind) and fragment in e for e in data['errors']), data['errors'])

    def test_clean_tree_passes(self):
        code, data = self.run_check(CLEAN_SKILL)
        self.assertEqual((code, data['errors']), (0, []))
        self.assertGreater(data['chain_mentions'], 0)
        self.assertGreater(data['literals'], 0)

    def test_chain_typo(self):
        self.assert_error(self.run_check('Call `figma.getNodeByIdAsyn(id)`.'), 'missing_chains', 'getNodeByIdAsyn')

    def test_invented_member_in_code(self):
        text = '```js\nconst f = figma.createFrame();\nf.fooBarBaz = 1;\n```\n'
        self.assert_error(self.run_check(text), 'missing_members', 'fooBarBaz')

    def test_bad_enum_literal(self):
        text = "```js\nframe.layoutSizingHorizontal = 'STRETCH';\n```\n"
        self.assert_error(self.run_check(text), 'bad_literals', 'STRETCH')

    def test_editor_only_member_needs_an_allowlist_entry(self):
        text = 'In FigJam, `figma.createConnector()` draws arrows.'
        self.assert_error(self.run_check(text), 'editor_only', 'figma.createConnector')
        allow = 'editor figma.createConnector FigJam only, cited on purpose\n'
        self.assertEqual(self.run_check(text, allow)[0], 0)

    def test_bare_call_must_exist(self):
        self.assert_error(self.run_check('Read them with `getAnnotations()`.'), 'missing_calls', 'getAnnotations')
        self.assertEqual(self.run_check('Use `getAnnotationCategoriesAsync()`.')[0], 0)

    def test_absent_name_needs_a_negating_line(self):
        allow = 'absent getAnnotations() no such method in the typings\n'
        self.assertEqual(self.run_check('There is no `getAnnotations()` method.', allow)[0], 0)
        self.assert_error(self.run_check('Read them with `getAnnotations()`.', allow), 'absent_misuse', 'getAnnotations')

    def test_absent_claim_must_stay_true(self):
        allow = 'absent figma.createFrame claimed missing by mistake here\n'
        code, data = self.run_check('`figma.createFrame` does not exist.', allow)
        self.assert_error((code, data), 'absent_stale', 'figma.createFrame')

    def test_the_bugs_fixed_in_1dca321_are_caught(self):
        # The shape of plugin-api-data.md before commit 1dca321. The first line contains "not",
        # which must not excuse figma.setAnnotations: only the bare-call form is allowlisted.
        text = ('Annotations stored via `figma.setAnnotations(...)` will not appear reliably.\n\n'
                '```javascript\nconst node = await figma.getNodeByIdAsync("1:2");\n'
                'const annotations = node.getAnnotations();\n```\n')
        allow = ('absent getAnnotations() no such method in the typings\n'
                 'absent setAnnotations() no such method in the typings\n')
        code, data = self.run_check(text, allow)
        self.assertEqual(code, 1)
        self.assertTrue(any('figma.setAnnotations' in e for e in data['errors']), data['errors'])
        self.assertTrue(any('node.getAnnotations' in e for e in data['errors']), data['errors'])

    def test_deprecated_is_a_note_not_an_error(self):
        code, data = self.run_check('Prefer async over `figma.getNodeById(id)`, which is deprecated.')
        self.assertEqual(code, 0, data['errors'])
        self.assertTrue(any('figma.getNodeById' in d for d in data['deprecated']))

    def test_hook_files_are_scanned(self):
        hook = "MESSAGE = 'Use `figma.getNodeByIdAsync(id)`, never `figma.getNodeByIdz(id)`.'\n"
        self.assert_error(self.run_check(CLEAN_SKILL, hook=hook), 'missing_chains', 'getNodeByIdz')

    def test_unused_entries_fail_only_in_strict_mode(self):
        allow = 'receiver someObject outside payload never referenced\n'
        self.assertEqual(self.run_check(CLEAN_SKILL, allow)[0], 0)
        self.assert_error(self.run_check(CLEAN_SKILL, allow, strict=True), 'unused_allowlist', 'someObject')

    def test_allowlist_entries_need_a_kind_and_a_reason(self):
        for bad in ('absent figma.x\n', 'absent figma.x too short\n', 'unknown figma.x some long reason here\n'):
            self.allowlist.write_text(bad)
            with self.assertRaises(check_api.LoadError, msg=bad):
                check_api.Allowlist(self.allowlist)
        self.allowlist.write_text('# comment\n\nglobal figma.connect in=*code-connect* Code Connect figma import\n')
        entry = check_api.Allowlist(self.allowlist).entries[0]
        self.assertEqual((entry['id'], entry['scope']), ('figma.connect', '*code-connect*'))

    def test_bad_allowlist_exits_2(self):
        self.allowlist.write_text('absent figma.x\n')
        with contextlib.redirect_stderr(io.StringIO()):
            code = check_api.main(['--root', str(self.root), '--typings-dir', str(self.typings),
                                   '--allowlist', str(self.allowlist)])
        self.assertEqual(code, 2)

    def test_every_allowlist_entry_has_a_reason(self):
        allow = check_api.Allowlist(check_api.ALLOWLIST)
        self.assertGreater(len(allow.entries), 0)
        for e in allow.entries:
            with self.subTest(entry=e['id']):
                self.assertGreaterEqual(len(e['reason'].split()), 3)


class RealTypingsTests(unittest.TestCase):
    """The repository against the pinned typings, when they are available without a download."""

    def test_repository_is_clean_against_pinned_typings(self):
        directory = os.environ.get('FIGMA_TYPINGS_DIR')
        cached = check_api.cache_dir() / f'plugin-typings-{check_api.PINNED}.tgz'
        if not directory and not cached.is_file():
            self.skipTest('pinned typings not cached; run python3 scripts/check_api.py once (CI runs it as its own job)')
        args = ['--strict', '--json'] + (['--typings-dir', directory] if directory else [])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check_api.main(args)
        data = json.loads(out.getvalue())
        self.assertEqual((code, data['errors']), (0, []))


def git_head():
    try:
        return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


@unittest.skipUnless(git_head(), 'needs a git checkout')
class BuildDistTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / 'a'
        cls.built = build_dist.build('HEAD', cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_same_commit_same_bytes(self):
        again = build_dist.build('HEAD', Path(self.tmp.name) / 'b')
        self.assertEqual([p.read_bytes() for p in self.built], [p.read_bytes() for p in again])

    def test_one_zip_per_skill_with_skill_md_at_the_root(self):
        listed = build_dist.git('ls-tree', '-r', '--name-only', 'HEAD', 'skills').decode().split('\n')
        skills = sorted({p.split('/')[1] for p in listed if re.fullmatch(r'skills/[^/]+/SKILL\.md', p)})
        per_skill = [p for p in self.built if not p.name.startswith('figma-maxxing-')]
        self.assertEqual(len(per_skill), len(skills))
        for path in per_skill:
            with self.subTest(zip=path.name), zipfile.ZipFile(path) as z:
                names = z.namelist()
                skill = names[0].split('/')[0]
                self.assertIn(skill, skills)
                self.assertTrue(all(n.startswith(skill + '/') for n in names))
                self.assertIn(f'{skill}/SKILL.md', names)
                self.assertIn(f'{skill}/LICENSE', names)
                self.assertFalse([n for n in names if '__pycache__' in n or n.endswith('.pyc')])
                head = z.read(f'{skill}/SKILL.md').decode()
                self.assertRegex(head, rf'(?m)^name:\s*{re.escape(skill)}\s*$')

    def test_bundle_installs_offline(self):
        bundle = next(p for p in self.built if p.name.startswith('figma-maxxing-'))
        with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(bundle) as z:
            z.extractall(tmp)
            top = Path(tmp) / bundle.stem
            self.assertTrue((top / '.claude-plugin/plugin.json').is_file())
            listed = subprocess.run([sys.executable, str(top / 'install.py'), '--list'],
                                    capture_output=True, text=True, check=True).stdout.split()
            self.assertEqual(listed, sorted(p.parent.name for p in (top / 'skills').glob('*/SKILL.md')))

    def test_checksums_match(self):
        lines = (self.out / 'SHA256SUMS').read_text().strip().split('\n')
        self.assertEqual(len(lines), len(self.built))
        for line in lines:
            digest, name = line.split('  ')
            self.assertEqual(hashlib.sha256((self.out / name).read_bytes()).hexdigest(), digest)


class ClaimTests(unittest.TestCase):
    def test_counts_come_from_the_files(self):
        c = count_claims.counts()
        self.assertEqual(c['skills'], len(list((ROOT / 'skills').glob('*/SKILL.md'))))
        self.assertEqual(c['gotchas'], c['gotchas_anomalies'] + c['gotchas_field_notes'])
        for key in ('gotchas', 'handoff_checks', 'preflight_checks', 'hook_patterns'):
            self.assertGreater(c[key], 0, key)

    def test_every_numeric_claim_matches_the_counts(self):
        """README.md, docs/README.pt-BR.md, llms.txt, docs/*.md and every SKILL.md."""
        self.assertEqual(count_claims.check(), {})

    def test_readme_and_its_translation_cite_the_same_numbers(self):
        en = {(m, n) for m, n, _, _ in count_claims.claims((ROOT / 'README.md').read_text())}
        pt = {(m, n) for m, n, _, _ in count_claims.claims((ROOT / 'docs/README.pt-BR.md').read_text())}
        self.assertTrue(en, 'README.md cites no checked number')
        self.assertEqual(en, pt)

    def test_mismatches_are_caught(self):
        c = {'skills': 8, 'gotchas': 90, 'handoff_checks': 17, 'preflight_checks': 8, 'slop_checks': 8}
        for text, gate in (('Install all seven skills.', None), ('It ships 89 gotchas.', None),
                           ('more than 90 notes', None), ('mais de 95 notas', None),
                           ('figma-preflight runs 7 checks; figma-handoff-gate runs 17 checks.', None),
                           ('**figma-handoff-gate**\n- Same as figma-slop-check.\n- The 16 checks by hand.', None),
                           ('The 9-check gate', 'preflight')):
            with self.subTest(text=text):
                self.assertEqual(len(count_claims.check_text(text, c, gate)), 1)
        for text in ('02 check before with figma-preflight', 'Instance manipulation: three gotchas',
                     'more than 80 notes', 'oito skills'):
            with self.subTest(text=text):
                self.assertEqual(count_claims.check_text(text, c), [])


class ReleaseNotesTests(unittest.TestCase):
    def test_section_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'CHANGELOG.md').write_text('# Changelog\n\n## [Unreleased]\n\n## [1.2.0] - 2026-01-01\n\n'
                                               '### Added\n\n- A thing.\n\n## [1.1.0] - 2025-12-01\n\n- Old.\n')
            self.assertEqual(release_notes.section('1.2.0', root), '### Added\n\n- A thing.')
            self.assertEqual(release_notes.section('1.1.0', root), '- Old.')
            self.assertEqual(release_notes.section('9.9.9', root), '')

    def test_versions_cover_every_manifest(self):
        found = release_notes.versions()
        for where in ('.claude-plugin/plugin.json', '.codex-plugin/plugin.json', '.cursor-plugin/plugin.json',
                      'plugin.json', 'gemini-extension.json', 'CITATION.cff', 'llms.txt'):
            self.assertIn(where, found)
        self.assertNotIn('.claude-plugin/marketplace.json', found)  # carries no version on purpose
        self.assertEqual(len([k for k in found if k.endswith('SKILL.md')]),
                         len(list((ROOT / 'skills').glob('*/SKILL.md'))))

    def test_versions_flag_a_stale_json_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '.claude-plugin').mkdir()
            (root / '.claude-plugin/plugin.json').write_text('{"version": "2.0.0"}')
            (root / '.cursor-plugin').mkdir()
            (root / '.cursor-plugin/plugin.json').write_text('{"version": "1.9.0"}')
            (root / '.git').mkdir()
            (root / '.git/ignored.json').write_text('{"version": "0.0.1"}')
            (root / 'skills.sh.json').write_text('{"groupings": []}')
            (root / 'llms.txt').write_text('> Skills. Version 2.0.0. MIT.\n')
            found = release_notes.versions(root)
            self.assertEqual(found['.cursor-plugin/plugin.json'], '1.9.0')
            self.assertEqual(found['llms.txt'], '2.0.0')
            self.assertNotIn('.git/ignored.json', found)
            self.assertNotIn('skills.sh.json', found)


if __name__ == '__main__':
    unittest.main()
