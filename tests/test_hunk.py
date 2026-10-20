import os
import pty
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

  def status_tty(self, *args):
    master, slave = pty.openpty()
    try:
      result = subprocess.run([str(ROOT / "bin/git-hunk"), "status", *args],
                              cwd=self.repo, env=self.env, stdout=slave,
                              stderr=subprocess.PIPE)
      os.close(slave)
      slave = None
      chunks = []
      while True:
        try:
          chunk = os.read(master, 65536)
        except OSError:
          break
        if not chunk:
          break
        chunks.append(chunk)
      return result.returncode, b"".join(chunks).replace(b"\r\n", b"\n")
    finally:
      os.close(master)
      if slave is not None:
        os.close(slave)

  def test_status_colors_preserve_git_columns_and_paths(self):
    (self.repo / "added file.txt").write_text("new\n")
    self.run_cmd("git", "add", "added file.txt")
    # An addition in the index and deletion in the worktree need separate colors.
    (self.repo / "added file.txt").unlink()
    (self.repo / "untracked\nname.txt").write_text("new\n")
    code, actual = self.status_tty("--short")
    self.assertEqual(code, 0)
    expected = self.run_cmd("git", "-c", "color.status=false", "status", "--short").stdout
    self.assertEqual(re.sub(rb"\x1b\[[0-9;]*m", b"", actual).decode(), expected)
    self.assertIn(b"\x1b[94mM\x1b[m", actual)
    self.assertIn(b"\x1b[32mA\x1b[m\x1b[31mD\x1b[m", actual)
    self.assertIn(b'\x1b[31m"added file.txt"\x1b[m', actual)
    self.assertIn(b'\x1b[97m"untracked\\nname.txt"\x1b[m', actual)

  def test_status_rename_theme_and_override(self):
    self.run_cmd("git", "restore", "sample.txt")
    self.run_cmd("git", "mv", "sample.txt", "renamed.txt")
    self.run_cmd("git", "config", "hunk.theme", "railscasts")
    code, actual = self.status_tty("--short")
    self.assertEqual(code, 0)
    self.assertIn(b"\x1b[38;2;109;156;190mR", actual)
    self.assertIn(b"sample.txt -> renamed.txt", actual)
    self.env["HUNK_THEME"] = "default"
    self.assertIn(b"\x1b[94mR", self.status_tty("--short")[1])

  def test_status_machine_output_and_redirect(self):
    for args in ((), ("--porcelain",), ("--porcelain=v2",), ("-bz",), ("--long",)):
      expected = self.run_cmd("git", "-c", "color.status=false", "status", *args)
      actual = self.run_cmd(str(ROOT / "bin/git-hunk"), "status", *args)
      self.assertEqual(actual.stdout, expected.stdout)
      if args:
        code, output = self.status_tty(*args)
        self.assertEqual(code, 0)
        self.assertEqual(re.sub(rb"\x1b\[[0-9;]*m", b"", output).decode(), expected.stdout)

  def test_status_default_preserves_long_sections_and_colors(self):
    (self.repo / "added.txt").write_text("new\n")
    self.run_cmd("git", "add", "added.txt")
    (self.repo / "untracked.txt").write_text("untracked\n")
    code, actual = self.status_tty("--long")
    self.assertEqual(code, 0)
    expected = self.run_cmd("git", "-c", "color.status=false", "status", "--long").stdout
    self.assertEqual(re.sub(rb"\x1b\[[0-9;]*m", b"", actual).decode(), expected)
    for heading in (b"On branch", b"Changes to be committed:",
                    b"Changes not staged for commit:", b"Untracked files:"):
      self.assertIn(heading, actual)
    self.assertIn(b"\x1b[32mnew file:", actual)
    self.assertIn(b"\x1b[94mmodified:", actual)
    self.assertIn(b"\t\x1b[97muntracked.txt\x1b[m\n", actual)
    self.assertNotIn(b"\x1b[97m", actual.split(b"Untracked files:", 1)[0])

  def test_status_reports_git_errors(self):
    code, output = self.status_tty()
    self.assertEqual(code, 0)
    self.assertIn("Unstaged · 1".encode(), output)
    self.assertNotIn(b"git add", output)
    self.assertIn(b"git add", self.status_tty("--hints")[1])
    code, output = self.status_tty("--invalid-option")
    self.assertNotEqual(code, 0)
    self.assertEqual(output, b"")

  def test_status_merge_conflicts_and_resolution(self):
    self.run_cmd("git", "restore", "sample.txt")
    (self.repo / "deleted.txt").write_text("base\n")
    self.run_cmd("git", "add", ".")
    self.run_cmd("git", "commit", "-qm", "merge base")
    branch = self.run_cmd("git", "branch", "--show-current").stdout.strip()
    self.run_cmd("git", "checkout", "-qb", "incoming")
    for name in ("sample.txt", "added.txt", "deleted.txt"):
      (self.repo / name).write_text("theirs\n")
    self.run_cmd("git", "add", ".")
    self.run_cmd("git", "commit", "-qm", "incoming changes")
    self.run_cmd("git", "checkout", "-q", branch)
    for name in ("sample.txt", "added.txt"):
      (self.repo / name).write_text("ours\n")
    self.run_cmd("git", "rm", "deleted.txt")
    self.run_cmd("git", "add", ".")
    self.run_cmd("git", "commit", "-qm", "local changes")
    self.assertEqual(self.run_cmd("git", "merge", "incoming", check=False).returncode, 1)

    for theme, red in (("default", b"31"), ("railscasts", b"38;2;218;73;57")):
      self.env["HUNK_THEME"] = theme
      code, actual = self.status_tty("--long")
      self.assertEqual(code, 0)
      expected = self.run_cmd("git", "-c", "color.status=false", "status").stdout
      self.assertEqual(re.sub(rb"\x1b\[[0-9;]*m", b"", actual).decode(), expected)
      self.assertIn(b"Unmerged paths:", actual)
      for label in (b"both modified:", b"both added:", b"deleted by us:"):
        self.assertIn(b"\t\x1b[" + red + b"m" + label, actual)
      short = self.status_tty("--short")[1]
      for x, y in ((b"U", b"U"), (b"A", b"A"), (b"D", b"U")):
        self.assertIn(b"\x1b[" + red + b"m" + x + b"\x1b[m"
                      + b"\x1b[" + red + b"m" + y + b"\x1b[m", short)

    (self.repo / "sample.txt").write_text("resolved\n")
    self.run_cmd("git", "add", "sample.txt")
    self.env["HUNK_THEME"] = "default"
    actual = self.status_tty("--long")[1]
    self.assertIn(b"Changes to be committed:", actual)
    self.assertIn(b"\x1b[94mmodified:   sample.txt", actual)
    self.assertIn(b"Unmerged paths:", actual)

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
    (self.repo / "src").mkdir()
    self.run_cmd("git", "mv", "sample.txt", "src/sample.txt")
    patch = self.run_cmd("git", "diff", "--cached").stdout
    result = self.run_cmd(str(ROOT / "bin/hunk-pager"), "--paging=never", input=patch)
    self.assertIn("\x1b[2msrc/\x1b[22m\x1b[1msample.txt", result.stdout)
    self.run_cmd("git", "reset", "--hard", "HEAD")
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
