import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HunkIntegration(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory(prefix="hunk-test-")
    self.addCleanup(self.temp.cleanup)
    self.repo = Path(self.temp.name) / "repo"
    self.repo.mkdir()
    self.env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull,
                    GIT_CONFIG_NOSYSTEM="1", DELTA_FEATURES="", HUNK_THEME="")
    self.run_cmd("git", "init", "-q")
    self.run_cmd("git", "config", "user.name", "Test")
    self.run_cmd("git", "config", "user.email", "test@example.com")
    (self.repo / "sample.txt").write_text("before\ncontext\n")
    self.run_cmd("git", "add", ".")
    self.run_cmd("git", "commit", "-qm", "initial")
    (self.repo / "sample.txt").write_text("after\ncontext\n")

  def run_cmd(self, *args, input=None, check=True):
    return subprocess.run(args, cwd=self.repo, env=self.env, input=input,
                          text=True, capture_output=True, check=check)

  def test_redirect_preserves_patch_and_exit_status(self):
    expected = self.run_cmd("git", "diff", "-U2").stdout
    actual = self.run_cmd(str(ROOT / "bin/git-hunk"), "--exit-code", check=False)
    self.assertEqual(actual.returncode, 1)
    self.assertEqual(actual.stdout, expected)
    self.assertNotIn("\x1b", actual.stdout)
    self.run_cmd("git", "add", ".")
    staged = self.run_cmd(str(ROOT / "bin/git-hunk"), "--cached").stdout
    self.assertEqual(staged, expected)

  def test_renderer_preserves_file_metadata(self):
    self.run_cmd("git", "mv", "sample.txt", "renamed file.txt")
    (self.repo / "new.txt").write_text("added\n")
    (self.repo / "binary.bin").write_bytes(b"\x00\x01\x02")
    (self.repo / "renamed file.txt").chmod(0o755)
    self.run_cmd("git", "add", ".")
    patch = self.run_cmd("git", "diff", "--cached", "-M20%").stdout
    result = self.run_cmd(str(ROOT / "bin/hunk-pager"), "--paging=never", input=patch)
    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    for text in ("added: new.txt", "binary.bin (binary file)",
                 "renamed file.txt", "sample.txt", "mode +x"):
      self.assertIn(text, plain)
    self.assertIn("+after", plain)
    self.assertIn("-before", plain)
    self.assertNotIn("diff --git", plain)
    self.assertNotIn("index ", plain)

  def test_renderer_labels_removed_files(self):
    self.run_cmd("git", "rm", "-f", "sample.txt")
    patch = self.run_cmd("git", "diff", "--cached").stdout
    result = self.run_cmd(str(ROOT / "bin/hunk-pager"), "--paging=never", input=patch)
    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    self.assertIn("removed: sample.txt", plain)
    self.assertIn("-before", plain)
    self.assertIn("-context", plain)
    self.assertNotIn("diff --git", plain)

  def test_renderer_labels_copied_files(self):
    (self.repo / "copy.txt").write_text("before\ncontext\n")
    self.run_cmd("git", "add", "copy.txt")
    patch = self.run_cmd("git", "diff", "--cached", "--find-copies-harder").stdout
    result = self.run_cmd(str(ROOT / "bin/hunk-pager"), "--paging=never", input=patch)
    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    self.assertIn("copied: sample.txt", plain)
    self.assertIn("copy.txt", plain)
    self.assertNotIn("diff --git", plain)

  def test_renderer_preserves_no_newline_marker(self):
    path = self.repo / "no-newline.txt"
    path.write_bytes(b"before")
    self.run_cmd("git", "add", "no-newline.txt")
    self.run_cmd("git", "commit", "-qm", "add no-newline file")
    path.write_bytes(b"after")
    patch = self.run_cmd("git", "diff").stdout
    result = self.run_cmd(str(ROOT / "bin/hunk-pager"), "--paging=never", input=patch)
    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    self.assertIn("no-newline.txt", plain)
    self.assertIn("-before", plain)
    self.assertIn("+after", plain)
    self.assertEqual(plain.count("No newline at end of file"), 2)

  def test_install_is_relocatable(self):
    prefix = Path(self.temp.name) / "prefix with spaces"
    subprocess.run(["make", "-C", str(ROOT), "install", f"PREFIX={prefix}"],
                   check=True, capture_output=True)
    patch = self.run_cmd("git", "diff").stdout
    result = self.run_cmd(str(prefix / "bin/hunk-pager"), "--paging=never", input=patch)
    self.assertIn("sample.txt", result.stdout)
    self.assertIn("after", result.stdout)

  def test_railscasts_theme_and_environment_override(self):
    (self.repo / "sample.txt").write_text("color = red\ncontext\n")
    self.run_cmd("git", "add", "sample.txt")
    self.run_cmd("git", "commit", "-qm", "add shared deletion context")
    (self.repo / "sample.txt").write_text("color = orange\ncontext\n")
    self.run_cmd("git", "config", "hunk.theme", "railscasts")
    patch = self.run_cmd("git", "diff").stdout
    args = (str(ROOT / "bin/hunk-pager"), "--paging=never", "--true-color=always")
    themed = self.run_cmd(*args, input=patch).stdout
    self.assertIn("38;2;135;175;95", themed)  # Railscasts DiffAdd
    self.assertIn("38;2;204;120;51", themed)  # Railscasts dark_orange line
    self.assertIn("38;2;218;73;57", themed)  # Railscasts DiffDelete
    self.env["HUNK_THEME"] = "default"
    default = self.run_cmd(*args, input=patch).stdout
    self.assertNotIn("38;2;135;175;95", default)
    strip = lambda text: re.sub(r"\x1b\[[0-9;]*m", "", text)
    self.assertEqual(strip(themed), strip(default))
