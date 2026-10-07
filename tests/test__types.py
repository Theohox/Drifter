"""Tests for shared enforcement types."""

from drifter._types import Classification


class TestClassification:
    def test_defaults(self) -> None:
        c = Classification(action="allow", reason="ok")
        assert c.action == "allow"
        assert c.reason == "ok"
        assert c.matched_pattern is None

    def test_frozen(self) -> None:
        import dataclasses

        c = Classification(action="block", reason="nope", matched_pattern="rm -rf /")
        assert dataclasses.is_dataclass(c)
        try:
            c.action = "allow"  # type: ignore[misc]
            raised = False
        except dataclasses.FrozenInstanceError:
            raised = True
        assert raised

    def test_importable_from_shell_guard_and_errors(self) -> None:
        # Backward-compatible import paths must keep working
        from drifter.errors import Classification as FromErrors
        from drifter.shell_guard import Classification as FromGuard

        assert FromErrors is Classification
        assert FromGuard is Classification
