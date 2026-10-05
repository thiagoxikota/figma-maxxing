import contextlib
import importlib.util
import io
import os
import socket
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from email.message import Message
from pathlib import Path
from unittest import mock

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


def load_module():
    # No bytecode cache: a __pycache__ inside a skill folder is flagged by skill scanners.
    saved, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec = importlib.util.spec_from_file_location("fetch_comments", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = saved
    return module


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def read(self, n=-1):
        return self.body if n is None or n < 0 else self.body[:n]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FetchCommentsBranchTests(unittest.TestCase):
    """Error branches, run in process with urlopen replaced: no network."""

    FILE_ID = "a" * 22  # matches the fileKey pattern, low entropy on purpose
    SENTINEL = "placeholder-" + "credential-value"

    def call(self, urlopen):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "comments-raw.json")
            err = io.StringIO()
            std = io.StringIO()
            with mock.patch.dict(os.environ, {"FIGMA_ACCESS_TOKEN": self.SENTINEL}), \
                    mock.patch.object(module.urllib.request, "urlopen", urlopen), \
                    contextlib.redirect_stderr(err), contextlib.redirect_stdout(std):
                code = module.main(["fetch_comments.py", self.FILE_ID, out])
            written = os.path.exists(out)
        self.assertNotIn(self.SENTINEL, err.getvalue() + std.getvalue())
        return code, err.getvalue(), written

    def test_http_error_prints_body_preview_and_never_headers(self):
        headers = Message()
        headers["X-Header-Sentinel"] = "header-sentinel-value"
        body = b'{"status": 400, "err": "Bad request"}' + b"x" * 1000

        def urlopen(req, timeout):
            raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", headers, io.BytesIO(body))

        code, err, written = self.call(urlopen)
        self.assertEqual(code, 1)
        self.assertIn("Figma API returned 400", err)
        self.assertIn('"err": "Bad request"', err)
        self.assertNotIn("x" * 301, err)
        self.assertIn("x" * (300 - len(b'{"status": 400, "err": "Bad request"}')), err)
        self.assertNotIn("header-sentinel-value", err)
        self.assertFalse(written)

    def test_timeout_while_reading_exits_3(self):
        def urlopen(req, timeout):
            raise socket.timeout("timed out")

        code, err, written = self.call(urlopen)
        self.assertEqual(code, 3)
        self.assertIn("Timeout", err)
        self.assertFalse(written)

    def test_timeout_while_connecting_exits_3(self):
        def urlopen(req, timeout):
            raise urllib.error.URLError(TimeoutError("timed out"))

        code, err, written = self.call(urlopen)
        self.assertEqual(code, 3)
        self.assertIn("Timeout", err)
        self.assertFalse(written)

    def test_network_error_exits_3(self):
        def urlopen(req, timeout):
            raise urllib.error.URLError("nodename nor servname provided")

        code, err, written = self.call(urlopen)
        self.assertEqual(code, 3)
        self.assertIn("Network error", err)
        self.assertFalse(written)

    def test_non_json_answer_exits_4_and_writes_nothing(self):
        def urlopen(req, timeout):
            return FakeResponse(b"<html>captive portal</html>")

        code, err, written = self.call(urlopen)
        self.assertEqual(code, 4)
        self.assertIn("not a JSON object", err)
        self.assertIn("captive portal", err)
        self.assertFalse(written)

    def test_json_that_is_not_an_object_exits_4(self):
        def urlopen(req, timeout):
            return FakeResponse(b"[1, 2, 3]")

        code, err, written = self.call(urlopen)
        self.assertEqual(code, 4)
        self.assertFalse(written)

    def test_valid_answer_is_saved(self):
        def urlopen(req, timeout):
            self.assertEqual(req.full_url, f"https://api.figma.com/v1/files/{self.FILE_ID}/comments")
            return FakeResponse(b'{"comments": [{"id": "1", "resolved_at": null}, {"id": "2", "resolved_at": "x"}]}')

        code, err, written = self.call(urlopen)
        self.assertEqual(code, 0)
        self.assertTrue(written)


if __name__ == "__main__":
    unittest.main()
