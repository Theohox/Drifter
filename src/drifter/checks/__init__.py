"""Drift check registry."""

from __future__ import annotations

from drifter.checks._base import Check, Issue
from drifter.checks.agent_behavior import AgentSelfAuditCheck, GitCommitApprovalCheck
from drifter.checks.behavioral import (
    DriftCheckAfterWriteCheck,
    NoRushCheck,
    ReadBeforeWriteCheck,
    TestAfterWriteCheck,
)
from drifter.checks.code_quality import (
    DeadCodeCheck,
    HardcodedPathCheck,
    TestCoverageCheck,
    TomllibCompatibilityCheck,
)
from drifter.checks.docs import (
    ArchiveIntegrityCheck,
    CrossDocConsistencyCheck,
    DigestStalenessCheck,
    StaleReferenceCheck,
    TimestampStalenessCheck,
)
from drifter.checks.project import (
    ConductorContentCheck,
    ConductorHealthCheck,
    PipelineIntegrityCheck,
)
from drifter.checks.security import (
    CredentialLeakCheck,
    DangerousPatternsCheck,
    GitSafetyCheck,
    GitignoreCheck,
)
from drifter.checks.config_sync import ConfigSyncCheck
from drifter.checks.structure import ClaimSyncCheck, FileSizeCheck, ManifestSyncCheck, TreeIntegrityCheck
from drifter.checks.sync import (
    ArchitectureDocSyncCheck,
    AuditCoverageCheck,
    CliOutputCheck,
    PreFlightSyncCheck,
    ReadmeCompletenessCheck,
    ReporterCompletenessCheck,
)

BUILTIN_CHECKS: dict[str, type[Check]] = {
    "stale_reference": StaleReferenceCheck,
    "hardcoded_path": HardcodedPathCheck,
    "digest_staleness": DigestStalenessCheck,
    "conductor_health": ConductorHealthCheck,
    "cross_doc_consistency": CrossDocConsistencyCheck,
    "git_safety": GitSafetyCheck,
    "dangerous_patterns": DangerousPatternsCheck,
    "timestamp_staleness": TimestampStalenessCheck,
    "conductor_content": ConductorContentCheck,
    "architecture_doc_sync": ArchitectureDocSyncCheck,
    "readme_completeness": ReadmeCompletenessCheck,
    "pre_flight_sync": PreFlightSyncCheck,
    "credential_leak": CredentialLeakCheck,
    "dead_code": DeadCodeCheck,
    "test_coverage": TestCoverageCheck,
    "cli_output": CliOutputCheck,
    "gitignore": GitignoreCheck,
    "pipeline_integrity": PipelineIntegrityCheck,
    "archive_integrity": ArchiveIntegrityCheck,
    "tomllib_compatibility": TomllibCompatibilityCheck,
    "audit_coverage": AuditCoverageCheck,
    "reporter_completeness": ReporterCompletenessCheck,
    "agent_self_audit": AgentSelfAuditCheck,
    "git_commit_approval": GitCommitApprovalCheck,
    "tree_integrity": TreeIntegrityCheck,
    "file_size": FileSizeCheck,
    "manifest_sync": ManifestSyncCheck,
    "claim_sync": ClaimSyncCheck,
    "read_before_write": ReadBeforeWriteCheck,
    "test_after_write": TestAfterWriteCheck,
    "drift_check_after_write": DriftCheckAfterWriteCheck,
    "no_rush": NoRushCheck,
    "config_sync": ConfigSyncCheck,
}
