"""The lock, the hook and the installer, exercised as a user would run them. No network."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'skills/figma-preflight/scripts/figma_lock.py'
HOOK = ROOT / 'hooks/figma-canon-precheck.py'
INSTALL = ROOT / 'install.py'


def run(script, *args, stdin=None, env=None):
    merged = {k: v for k, v in os.environ.items() if not k.startswith('FIGMA_')}
    merged.update(env or {})
    return subprocess.run([sys.executable, str(script), *args], input=stdin,
                          capture_output=True, text=True, env=merged)


class LockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = {'FIGMA_LOCK_DIR': self.tmp.name}

    def tearDown(self):
        self.tmp.cleanup()

    def lock(self, *args):
        result = run(LOCK, *args, env=self.env)
        return result.returncode, json.loads(result.stdout)

    def test_check_never_reserves(self):
        self.assertEqual(self.lock('check', 'fileA'), (0, {'held': False}))
        self.assertEqual(self.lock('check', 'fileA'), (0, {'held': False}))

    def test_claim_conflict_release(self):
        code, out = self.lock('claim', 'fileA', '--agent', 'one', '--task', 't1')
        self.assertEqual((code, out['claimed'], out['renewed']), (0, True, False))
        code, out = self.lock('claim', 'fileA', '--agent', 'two', '--task', 't2')
        self.assertEqual((code, out['claimed'], out['agent'], out['task']), (1, False, 'one', 't1'))
        code, out = self.lock('release', 'fileA', '--agent', 'two', '--task', 't2')
        self.assertEqual((code, out['released']), (1, False))
        code, out = self.lock('release', 'fileA', '--agent', 'one', '--task', 't1')
        self.assertEqual((code, out['released']), (0, True))
        self.assertEqual(self.lock('check', 'fileA'), (0, {'held': False}))

    def test_same_holder_renews(self):
        self.lock('claim', 'fileA', '--agent', 'one', '--task', 't1')
        code, out = self.lock('claim', 'fileA', '--agent', 'one', '--task', 't1')
        self.assertEqual((code, out['renewed']), (0, True))

    def test_files_are_independent(self):
        self.lock('claim', 'fileA', '--agent', 'one', '--task', 't1')
        code, out = self.lock('claim', 'fileB', '--agent', 'two', '--task', 't2')
        self.assertEqual((code, out['claimed']), (0, True))

    def test_expired_lock_is_free_and_swept(self):
        path = Path(self.tmp.name) / 'fileA.json'
        path.write_text(json.dumps({'agent': 'old', 'task': 't0', 'claimed_at': 'x',
                                    'expires_at': 'x', 'expires_epoch': 1}))
        self.assertEqual(self.lock('check', 'fileA'), (0, {'held': False}))
        self.assertEqual(self.lock('sweep'), (0, {'swept': 1}))
        self.assertFalse(path.exists())

    def test_corrupt_lock_file_is_free(self):
        (Path(self.tmp.name) / 'fileA.json').write_text('not json')
        code, out = self.lock('claim', 'fileA', '--agent', 'one', '--task', 't1')
        self.assertEqual((code, out['claimed']), (0, True))

    def test_force_release_is_for_the_human(self):
        self.lock('claim', 'fileA', '--agent', 'one', '--task', 't1')
        code, out = self.lock('release', 'fileA', '--force')
        self.assertEqual((code, out['released']), (0, True))

    def test_claim_without_task_returns_generated_id(self):
        code, out = self.lock('claim', 'fileA', '--agent', 'one')
        self.assertEqual(code, 0)
        self.assertTrue(out['task'].startswith('adhoc-'))

    def test_rejects_path_like_keys_and_bad_ttl(self):
        for args in (['claim', '../escape', '--task', 't'], ['check', 'a/b'],
                     ['claim', 'fileA', '--task', 't', '--ttl', '0'],
                     ['claim', 'fileA', '--task', 't', '--ttl', '1800000'], ['claim', 'abc\n', '--task', 't']):
            self.assertEqual(run(LOCK, *args, env=self.env).returncode, 2, args)
        self.assertEqual(run(LOCK, 'release', 'fileA', env=self.env).returncode, 2)


class HookTests(unittest.TestCase):
    def hook(self, code, mode=None, raw=None, extra=None):
        env = {'FIGMA_PRECHECK_BRIDGE': '0', 'FIGMA_PRECHECK_LOG': '', **(extra or {})}
        env['FIGMA_PRECHECK_MODE'] = mode or 'warn'
        payload = raw if raw is not None else json.dumps({'tool_input': {'code': code}})
        result = run(HOOK, stdin=payload, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)['hookSpecificOutput'] if result.stdout.strip() else None

    def test_clean_script_is_silent(self):
        self.assertIsNone(self.hook('const n = await figma.getNodeByIdAsync("1:2"); return n.id'))

    def test_bad_input_is_silent(self):
        self.assertIsNone(self.hook('', raw='not json'))
        self.assertIsNone(self.hook('', raw='[]'))
        self.assertIsNone(self.hook('', raw=json.dumps({'tool_input': {'code': 42}})))

    def test_warn_mode_never_decides(self):
        out = self.hook('figma.currentPage = page')
        self.assertNotIn('permissionDecision', out)
        self.assertIn('setCurrentPageAsync', out['additionalContext'])

    def test_block_mode_denies_only_block_findings(self):
        out = self.hook('figma.currentPage = page', mode='block')
        self.assertEqual(out['permissionDecision'], 'deny')
        self.assertIn('setCurrentPageAsync', out['permissionDecisionReason'])
        out = self.hook('console.log("x")', mode='block')
        self.assertNotIn('permissionDecision', out)

    def test_each_pattern_fires(self):
        cases = {
            'figma.createConnector()': 'FigJam',
            'figma.loadFontAsync({family: "Inter", style: "Regular"});': 'loadFontAsync',
            'figma.setCurrentPageAsync(p)': 'setCurrentPageAsync',
            'figma.importComponentByKeyAsync(k)': 'importComponentByKeyAsync',
            'figma.notify("done")': 'notify',
            'node.setPluginData("k", "v")': 'setSharedPluginData',
            'const fill = "#FF0000"': 'Hex literal',
            'figma.createRectangle()': 'createRectangle',
            'child.layoutSizingHorizontal = "FILL"': 'appendChild',
            'console.log(1)': 'console.log',
            'v.scopes = ["ALL_SCOPES"]': 'ALL_SCOPES',
        }
        for code, expected in cases.items():
            out = self.hook(code)
            self.assertIsNotNone(out, code)
            self.assertIn(expected, out['additionalContext'], code)

    def test_correct_forms_do_not_fire(self):
        for code in ('await figma.loadFontAsync(f)', 'await figma.setCurrentPageAsync(p)',
                     'node.setSharedPluginData("ns", "k", "v")', 'const url = "https://x.y/#abc123"',
                     'await figma.importComponentByKeyAsync(k)'):
            self.assertIsNone(self.hook(code), code)

    def test_recommended_fixes_pass_in_block_mode(self):
        for code in ('await Promise.all(fonts.map(f => figma.loadFontAsync(f)));',
                     'const page = figma.root.children[0];\nawait figma.setCurrentPageAsync(page);',
                     '// never write figma.currentPage = page; use the async setter\nawait figma.setCurrentPageAsync(p)',
                     'return { tip: "figma.currentPage = x is sync and fails" }'):
            out = self.hook(code, mode='block')
            self.assertTrue(out is None or 'permissionDecision' not in out, code)

    def test_bare_async_call_still_blocks(self):
        out = self.hook('const f = {family: "Inter", style: "Regular"};\nfigma.loadFontAsync(f);', mode='block')
        self.assertEqual(out['permissionDecision'], 'deny')

    def test_hex_helpers_warn(self):
        for code in ("node.fills = [figma.util.solidPaint('#FF0000')]", "const textColor = '#ff0000'"):
            self.assertIn('Hex', self.hook(code)['additionalContext'], code)

    def test_long_script_warns(self):
        out = self.hook('return 1;' + ' ' * 20001)
        self.assertIn('20 KB', out['additionalContext'])

    def test_log_is_opt_in_and_omits_the_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'log.jsonl'
            self.hook('console.log("secret-marker")', extra={'FIGMA_PRECHECK_LOG': str(target)})
            text = target.read_text()
            self.assertEqual(json.loads(text)['decision'], 'warn')
            self.assertNotIn('secret-marker', text)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def install(self, *args):
        return run(INSTALL, '--project', str(self.project), *args)

    def test_list_matches_skills_directory(self):
        listed = run(INSTALL, '--list').stdout.split()
        on_disk = sorted(p.parent.name for p in (ROOT / 'skills').glob('*/SKILL.md'))
        self.assertEqual(listed, on_disk)
        self.assertIn('figma-canon', listed)

    def test_dry_run_writes_nothing(self):
        result = self.install('--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Would copy', result.stdout)
        self.assertEqual(list(self.project.iterdir()), [])

    def test_install_then_refuse_overwrite(self):
        for target, folder in (('claude', '.claude'), ('agents', '.agents')):
            result = self.install('--target', target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((self.project / folder / 'skills/figma-canon/SKILL.md').is_file())
            self.assertTrue((self.project / folder / 'skills/figma-preflight/scripts/figma_lock.py').is_file())
            again = self.install('--target', target)
            self.assertEqual(again.returncode, 2)
            self.assertIn('Already exists', again.stderr)

    def test_subset_and_skip_existing(self):
        self.assertEqual(self.install('--skills', 'figma-canon').returncode, 0)
        result = self.install('--skip-existing')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Skipped (already exists)', result.stdout)
        self.assertTrue((self.project / '.claude/skills/figma-preflight/SKILL.md').is_file())

    def test_unknown_skill_is_an_error(self):
        self.assertEqual(self.install('--skills', 'nope').returncode, 2)


if __name__ == '__main__':
    unittest.main()
