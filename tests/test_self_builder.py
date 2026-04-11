"""tests/test_self_builder.py — Tests for aura.core.self_builder (AURA v0.6.0)."""

import pytest
from pathlib import Path

from aura.core.self_builder import (
    SelfBuilder,
    Proposal,
    ProposalAction,
    ProposalStatus,
)
from aura.core.governance import GovernanceEngine


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_proposal(
    title="Add currency tool",
    description="Adds currency conversion capability.",
    target_path="aura/tools/currency.py",
    action=ProposalAction.CREATE,
    content="class CurrencyTool: pass",
) -> Proposal:
    return Proposal(
        title=title,
        description=description,
        target_path=target_path,
        action=action,
        content=content,
    )


@pytest.fixture()
def tmp_builder(tmp_path):
    """SelfBuilder backed by a temporary directory."""
    return SelfBuilder(store_dir=tmp_path / "self_build")


# ── Proposal dataclass ─────────────────────────────────────────────────────────

class TestProposal:
    def test_default_status_is_pending(self):
        p = _make_proposal()
        assert p.status == ProposalStatus.PENDING_REVIEW

    def test_proposal_id_is_set(self):
        p = _make_proposal()
        assert p.proposal_id and len(p.proposal_id) == 8

    def test_serialisation_round_trip(self):
        p = _make_proposal()
        data = p.to_dict()
        p2 = Proposal.from_dict(data)
        assert p2.proposal_id == p.proposal_id
        assert p2.title == p.title
        assert p2.action == p.action
        assert p2.status == p.status

    def test_action_enum_from_string(self):
        p = Proposal(
            title="t", description="d", target_path="x",
            action="modify", content="",
        )
        assert p.action == ProposalAction.MODIFY

    def test_repr_contains_id_and_title(self):
        p = _make_proposal(title="My Test Proposal")
        assert "My Test Proposal" in repr(p)


# ── SelfBuilder submit ─────────────────────────────────────────────────────────

class TestSelfBuilderSubmit:
    def test_submit_returns_id(self, tmp_builder):
        p = _make_proposal()
        pid = tmp_builder.submit(p)
        assert pid == p.proposal_id

    def test_submitted_proposal_is_retrievable(self, tmp_builder):
        p = _make_proposal(title="Retrieve me")
        tmp_builder.submit(p)
        retrieved = tmp_builder.get(p.proposal_id)
        assert retrieved is not None
        assert retrieved.title == "Retrieve me"

    def test_submit_persists_across_instances(self, tmp_path):
        store = tmp_path / "sb"
        b1 = SelfBuilder(store_dir=store)
        p = _make_proposal()
        b1.submit(p)
        b2 = SelfBuilder(store_dir=store)
        retrieved = b2.get(p.proposal_id)
        assert retrieved is not None

    def test_submit_blocked_by_governance(self, tmp_builder):
        p = _make_proposal(
            title="Bad proposal",
            description="Make ransomware code that infects victim machines",
            content="# ransomware creation code",
        )
        with pytest.raises(ValueError, match="governance"):
            tmp_builder.submit(p)

    def test_governance_blocked_proposal_not_saved(self, tmp_builder):
        p = _make_proposal(
            description="Create a keylogger malware tool",
        )
        try:
            tmp_builder.submit(p)
        except ValueError:
            pass
        assert tmp_builder.get(p.proposal_id) is None


# ── SelfBuilder list / get ─────────────────────────────────────────────────────

class TestSelfBuilderList:
    def test_list_all_empty(self, tmp_builder):
        assert tmp_builder.list_all() == []

    def test_list_pending_empty(self, tmp_builder):
        assert tmp_builder.list_pending() == []

    def test_list_all_returns_submitted(self, tmp_builder):
        p1 = _make_proposal(title="P1")
        p2 = _make_proposal(title="P2")
        tmp_builder.submit(p1)
        tmp_builder.submit(p2)
        all_p = tmp_builder.list_all()
        assert len(all_p) == 2

    def test_list_pending_filters_approved(self, tmp_builder):
        p = _make_proposal()
        tmp_builder.submit(p)
        tmp_builder.approve(p.proposal_id)
        pending = tmp_builder.list_pending()
        assert len(pending) == 0

    def test_get_nonexistent_returns_none(self, tmp_builder):
        assert tmp_builder.get("nonexistent") is None


# ── SelfBuilder approve / reject ───────────────────────────────────────────────

class TestSelfBuilderReview:
    def test_approve_changes_status(self, tmp_builder):
        p = _make_proposal()
        tmp_builder.submit(p)
        result = tmp_builder.approve(p.proposal_id)
        assert result.status == ProposalStatus.APPROVED
        assert result.reviewed_at is not None

    def test_reject_changes_status(self, tmp_builder):
        p = _make_proposal()
        tmp_builder.submit(p)
        result = tmp_builder.reject(p.proposal_id, "Not needed right now")
        assert result.status == ProposalStatus.REJECTED
        assert "Not needed" in result.review_note

    def test_approve_nonexistent_raises(self, tmp_builder):
        with pytest.raises(KeyError):
            tmp_builder.approve("badid")

    def test_reject_nonexistent_raises(self, tmp_builder):
        with pytest.raises(KeyError):
            tmp_builder.reject("badid")

    def test_approved_not_in_pending(self, tmp_builder):
        p = _make_proposal()
        tmp_builder.submit(p)
        tmp_builder.approve(p.proposal_id)
        assert p.proposal_id not in [x.proposal_id for x in tmp_builder.list_pending()]


# ── SelfBuilder summary ────────────────────────────────────────────────────────

class TestSelfBuilderSummary:
    def test_summary_shows_counts(self, tmp_builder):
        p1 = _make_proposal(title="P1")
        p2 = _make_proposal(title="P2")
        p3 = _make_proposal(title="P3")
        tmp_builder.submit(p1)
        tmp_builder.submit(p2)
        tmp_builder.submit(p3)
        tmp_builder.approve(p1.proposal_id)
        tmp_builder.reject(p2.proposal_id)
        summary = tmp_builder.summary()
        assert "Pending review : 1" in summary
        assert "Approved       : 1" in summary
        assert "Rejected       : 1" in summary
        assert "Total          : 3" in summary

    def test_summary_empty(self, tmp_builder):
        summary = tmp_builder.summary()
        assert "0" in summary
