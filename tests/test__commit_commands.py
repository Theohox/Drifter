"""Tests for git workflow helpers: approve + commit-msg."""

from __future__ import annotations

import subprocess
from types import SimpleNamespace

from drifter._commit_commands import _draft_message, cmd_approve, cmd_commit_msg


class TestApprove:
    def test_arms_one_time_approval(self, git_repo) -> None:
        args = SimpleNamespace(root=git_repo.path)
        assert cmd_approve(args) == 0
        assert (git_repo.path / ".git" / "approved").exists()

    def test_not_a_git_repo(self, tmp_path) -> None:
        args = SimpleNamespace(root=tmp_path)
        assert cmd_approve(args) == 1
        assert not (tmp_path / ".git").exists()


class TestCommitMsg:
    def test_nothing_staged(self, git_repo, capsys) -> None:
        args = SimpleNamespace(root=git_repo.path)
        assert cmd_commit_msg(args) == 1
        assert "Nothing staged" in capsys.readouterr().out

    def test_drafts_from_staged_changes(self, git_repo, capsys) -> None:
        (git_repo.path / "new_module.py").write_text("x = 1\n")
        (git_repo.path / "README.md").write_text("# hi\n")
        subprocess.run(["git", "add", "-A"], cwd=git_repo.path, check=True)
        args = SimpleNamespace(root=git_repo.path)
        assert cmd_commit_msg(args) == 0
        out = capsys.readouterr().out
        assert "add 2" in out
        assert "new_module.py" in out
        assert "README.md" in out
        assert "DRAFT" in out

    def test_draft_message_groups_by_area(self) -> None:
        msg = _draft_message(
            [("M", "docs/a.md"), ("M", "docs/b.md"), ("A", "src/x.py")]
        )
        assert "docs/: 2 file(s)" in msg
        assert "src/: 1 file(s)" in msg
        assert msg.startswith("chore:")

    def test_draft_message_single_area_prefix(self) -> None:
        msg = _draft_message([("M", "tests/test_a.py"), ("A", "tests/test_b.py")])
        assert msg.startswith("test:")

    def test_draft_message_caps_long_file_lists(self) -> None:
        staged = [("A", f"src/f{i}.py") for i in range(30)]
        msg = _draft_message(staged)
        assert "and 5 more" in msg
