import os
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "skills" / "figma-comment-fix-loop" / "scripts" / "fetch_comments.py"


def run(args, env_value=None):
    env = {k: v for k, v in os.environ.items() if k != "FIGMA_ACCESS_TOKEN"}
    if env_value is not None:
        env["FIGMA_ACCESS_TOKEN"] = env_value
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env, timeout=30)


class FetchCommentsTests(unittest.TestCase):
    def test_missing_token_exits_2_without_network(self):
        r = run(["abcdefghij1234567890ab"])
        self.assertEqual(r.returncode, 2)
        self.assertIn("FIGMA_ACCESS_TOKEN is not set", r.stderr)

    def test_rejects_malformed_file_key(self):
        placeholder = "placeholder-" + "value"
        r = run(["not a key"], placeholder)
        self.assertEqual(r.returncode, 2)
        self.assertNotIn(placeholder, r.stdout + r.stderr)

    def test_never_echoes_the_token(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for pattern in ("{token}", "print(token", "write(token", "token)", "%s\" % token"):
            self.assertNotIn(pattern, source)

if __name__ == "__main__":
    unittest.main()
