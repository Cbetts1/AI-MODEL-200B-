"""aura/core/self_builder.py — AURA Self-Build Proposal System.

AURA v0.6.0 introduces a self-build capability that lets AURA propose changes
to herself — new tools, configuration updates, documentation additions — and
queue them for *human review* before anything is applied.

Design Principles
-----------------
1. **Human-in-the-loop always**: AURA never auto-applies changes.  Every
   proposal is saved as a pending item that a maintainer must approve.
2. **Smallest possible steps**: Proposals are atomic (one file change at a
   time) so they are easy to review.
3. **Transparent audit trail**: All proposals, approvals, and rejections are
   logged to ``~/.aura/self_build/proposals.json``.
4. **Governance-gated**: A ``GovernanceEngine`` check is run before any
   proposal is accepted.  Proposals that would introduce illegal behaviour
   are rejected outright.

Proposal lifecycle
------------------
  DRAFT → PENDING_REVIEW → APPROVED | REJECTED

Usage
-----
    from aura.core.self_builder import SelfBuilder, Proposal

    builder = SelfBuilder()
    proposal = Proposal(
        title="Add currency-converter tool",
        description="Adds /tool currency to convert between currencies.",
        target_path="aura/tools/currency_converter.py",
        action="create",
        content="<python source>",
    )
    ref = builder.submit(proposal)  # returns a proposal_id string
    builder.list_pending()          # returns list[Proposal]
    builder.approve(ref)            # maintainer approves
    builder.reject(ref, "Not needed")  # maintainer rejects
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

_STORE_DIR = Path.home() / ".aura" / "self_build"
_PROPOSALS_FILE = _STORE_DIR / "proposals.json"

AURA_VERSION = "0.6.0"


# ── Enums & dataclasses ────────────────────────────────────────────────────────

class ProposalAction(str, Enum):
    CREATE = "create"        # Create a new file
    MODIFY = "modify"        # Modify an existing file
    DELETE = "delete"        # Delete a file
    CONFIG = "config"        # Update a config value


class ProposalStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class Proposal:
    """A single self-build proposal."""

    def __init__(
        self,
        title: str,
        description: str,
        target_path: str,
        action: ProposalAction | str,
        content: str = "",
        old_content: str = "",
        proposed_by: str = "aura",
    ) -> None:
        self.proposal_id: str = str(uuid.uuid4())[:8]
        self.title = title
        self.description = description
        self.target_path = target_path
        self.action = ProposalAction(action)
        self.content = content
        self.old_content = old_content
        self.proposed_by = proposed_by
        self.status = ProposalStatus.PENDING_REVIEW
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.reviewed_at: Optional[str] = None
        self.review_note: str = ""

    # ── serialisation ──────────────────────────────────────────────────────────

    def to_dict(self) -> Dict:
        return {
            "proposal_id": self.proposal_id,
            "title": self.title,
            "description": self.description,
            "target_path": self.target_path,
            "action": self.action.value,
            "content": self.content,
            "old_content": self.old_content,
            "proposed_by": self.proposed_by,
            "status": self.status.value,
            "created_at": self.created_at,
            "reviewed_at": self.reviewed_at,
            "review_note": self.review_note,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Proposal":
        p = cls(
            title=data["title"],
            description=data["description"],
            target_path=data["target_path"],
            action=data["action"],
            content=data.get("content", ""),
            old_content=data.get("old_content", ""),
            proposed_by=data.get("proposed_by", "aura"),
        )
        p.proposal_id = data["proposal_id"]
        p.status = ProposalStatus(data["status"])
        p.created_at = data["created_at"]
        p.reviewed_at = data.get("reviewed_at")
        p.review_note = data.get("review_note", "")
        return p

    def __repr__(self) -> str:
        return (
            f"Proposal(id={self.proposal_id!r}, title={self.title!r}, "
            f"status={self.status.value!r})"
        )


# ── SelfBuilder ────────────────────────────────────────────────────────────────

class SelfBuilder:
    """Manages the lifecycle of self-build proposals.

    Parameters
    ----------
    store_dir:
        Directory where proposal JSON is persisted.  Defaults to
        ``~/.aura/self_build/``.
    governance:
        Optional GovernanceEngine to screen proposals.  If None, a default
        engine is used.
    """

    def __init__(
        self,
        store_dir: Optional[Path] = None,
        governance=None,
    ) -> None:
        self._dir = store_dir or _STORE_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._file = self._dir / "proposals.json"

        if governance is None:
            from .governance import GovernanceEngine  # noqa: PLC0415
            governance = GovernanceEngine()
        self._governance = governance

    # ── public API ─────────────────────────────────────────────────────────────

    def submit(self, proposal: Proposal) -> str:
        """Submit a proposal for human review.

        Governance is checked on the combined proposal content.  If blocked,
        a ``ValueError`` is raised instead of persisting the proposal.

        Returns
        -------
        str
            The ``proposal_id`` of the saved proposal.
        """
        # Governance screen
        screen_text = f"{proposal.title}\n{proposal.description}\n{proposal.content}"
        gov_result = self._governance.check(screen_text)
        if gov_result.blocked:
            raise ValueError(
                f"Proposal blocked by governance rule '{gov_result.rule_name}': "
                f"{gov_result.reason}"
            )

        proposals = self._load()
        proposals[proposal.proposal_id] = proposal.to_dict()
        self._save(proposals)
        log.info("Self-build proposal submitted: %s (%s)", proposal.proposal_id, proposal.title)
        return proposal.proposal_id

    def get(self, proposal_id: str) -> Optional[Proposal]:
        """Retrieve a proposal by ID."""
        proposals = self._load()
        data = proposals.get(proposal_id)
        return Proposal.from_dict(data) if data else None

    def list_all(self) -> List[Proposal]:
        """Return all proposals in reverse-chronological order."""
        proposals = self._load()
        items = [Proposal.from_dict(v) for v in proposals.values()]
        items.sort(key=lambda p: p.created_at, reverse=True)
        return items

    def list_pending(self) -> List[Proposal]:
        """Return proposals awaiting review."""
        return [p for p in self.list_all() if p.status == ProposalStatus.PENDING_REVIEW]

    def approve(self, proposal_id: str) -> Proposal:
        """Mark a proposal as approved (human maintainer action).

        This does *not* automatically apply the change — it simply updates
        the status.  Actual application is done by a separate deployment step
        (e.g., a CI/CD pipeline or a human with ``git`` access).
        """
        return self._update_status(
            proposal_id,
            ProposalStatus.APPROVED,
            note="Approved by maintainer.",
        )

    def reject(self, proposal_id: str, reason: str = "") -> Proposal:
        """Mark a proposal as rejected."""
        return self._update_status(
            proposal_id,
            ProposalStatus.REJECTED,
            note=reason or "Rejected by maintainer.",
        )

    def summary(self) -> str:
        """Return a human-readable summary of proposal counts."""
        all_proposals = self.list_all()
        counts: Dict[str, int] = {}
        for p in all_proposals:
            counts[p.status.value] = counts.get(p.status.value, 0) + 1
        pending = counts.get("pending_review", 0)
        approved = counts.get("approved", 0)
        rejected = counts.get("rejected", 0)
        return (
            f"🔧 Self-Build Proposals — AURA v{AURA_VERSION}\n"
            f"  Pending review : {pending}\n"
            f"  Approved       : {approved}\n"
            f"  Rejected       : {rejected}\n"
            f"  Total          : {len(all_proposals)}"
        )

    # ── private ────────────────────────────────────────────────────────────────

    def _update_status(
        self,
        proposal_id: str,
        status: ProposalStatus,
        note: str,
    ) -> Proposal:
        proposals = self._load()
        if proposal_id not in proposals:
            raise KeyError(f"No proposal with id '{proposal_id}'")
        proposals[proposal_id]["status"] = status.value
        proposals[proposal_id]["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        proposals[proposal_id]["review_note"] = note
        self._save(proposals)
        return Proposal.from_dict(proposals[proposal_id])

    def _load(self) -> Dict[str, Dict]:
        if self._file.exists():
            try:
                return json.loads(self._file.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                return {}
        return {}

    def _save(self, proposals: Dict[str, Dict]) -> None:
        self._file.write_text(
            json.dumps(proposals, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
