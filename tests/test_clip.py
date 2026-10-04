"""End-to-end tests: real clipd HTTP server with a fake clipboard, driven by the real `clip` shell script."""

import importlib.machinery
import importlib.util
import os
import subprocess
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PNG = b"\x89PNG\r\n\x1a\n" + b"fake-image-bytes"


def load_clipd():
    loader = importlib.machinery.SourceFileLoader("clipd", str(ROOT / "bin" / "clipd"))
    spec = importlib.util.spec_from_loader("clipd", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


clipd = load_clipd()


class FakeClipboard:
    def __init__(self):
        self.png = None
        self.text = None

    def read_png(self):
        return self.png

    def read_text(self):
        return self.text

    def write_text(self, text):
        self.text = text


class ClipTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "config"
        self.home.mkdir()
        self.token = "test-token"
        (self.home / "token").write_text(self.token + "\n")

        self.clipboard = FakeClipboard()
        self.server = clipd.ClipServer(0, self.token, self.clipboard)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def clip(self, *args, stdin=None, token_home=None):
        env = {
            **os.environ,
            "CLIP_OVER_SSH_PORT": str(self.port),
            "CLIP_OVER_SSH_HOME": str(token_home or self.home),
            "CLIP_OVER_SSH_DIR": str(Path(self.tmp.name) / "out"),
        }
        return subprocess.run(
            ["sh", str(ROOT / "bin" / "clip"), *args], input=stdin, capture_output=True, env=env, timeout=20
        )

    def test_pulls_the_clipboard_image_to_a_png_file(self):
        self.clipboard.png = PNG

        result = self.clip()

        self.assertEqual(result.returncode, 0, result.stderr)
        path = Path(result.stdout.decode().strip())
        self.assertEqual(path.read_bytes(), PNG)
        self.assertTrue(path.name.startswith("clip-") and path.suffix == ".png")

    def test_reports_an_empty_clipboard_with_exit_code_2(self):
        result = self.clip("png")

        self.assertEqual(result.returncode, 2)
        self.assertIn(b"no image", result.stderr)
        self.assertEqual(list((Path(self.tmp.name) / "out").glob("*.png")), [])

    def test_prints_clipboard_text(self):
        self.clipboard.text = "hola, ñandú ✓"

        result = self.clip("text")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.decode(), "hola, ñandú ✓")

    def test_copies_stdin_to_the_mac_clipboard(self):
        result = self.clip("copy", stdin="desde el servidor\n".encode())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.clipboard.text, "desde el servidor\n")

    def test_status_confirms_the_tunnel(self):
        result = self.clip("status")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"ok", result.stdout)

    def test_rejects_a_wrong_token(self):
        other = Path(self.tmp.name) / "other"
        other.mkdir()
        (other / "token").write_text("wrong\n")
        self.clipboard.png = PNG

        result = self.clip("png", token_home=other)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"token rejected", result.stderr)

    def test_server_refuses_requests_without_a_token(self):
        self.clipboard.text = "secret"

        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(f"http://127.0.0.1:{self.port}/text", timeout=5)

        self.assertEqual(error.exception.code, 401)
        error.exception.close()

    def test_server_only_listens_on_loopback(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_fails_clearly_when_the_tunnel_is_down(self):
        self.server.shutdown()
        self.server.server_close()

        result = self.clip("status")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"no tunnel", result.stderr)
        self.server = clipd.ClipServer(0, self.token, self.clipboard)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()


class TokenTest(unittest.TestCase):
    def test_creates_a_private_token_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            clipd.CONFIG_DIR = Path(tmp) / "cfg"
            clipd.TOKEN_FILE = clipd.CONFIG_DIR / "token"

            first = clipd.load_token()
            second = clipd.load_token()

            self.assertEqual(first, second)
            self.assertGreaterEqual(len(first), 32)
            self.assertEqual(clipd.TOKEN_FILE.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
