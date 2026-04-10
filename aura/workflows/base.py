"""aura/workflows/base.py — Abstract Workflow base class.

A Workflow is a sequence of steps that AURA can run in order to accomplish a
multi-step goal.  Unlike single-shot Tools, Workflows may:
  - Invoke multiple Tools internally.
  - Create files/directories.
  - Report intermediate progress.
  - Pause and ask the user for confirmation (future feature).

Every Workflow must implement `run(args)` and provide a `name` and `description`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Workflow(ABC):
    """Abstract base class for all AURA workflows."""

    name: str = ""
    description: str = ""

    @abstractmethod
    def run(self, args: str) -> str:
        """Execute the workflow and return a summary string.

        Parameters
        ----------
        args:
            Raw argument string as typed by the user.

        Returns
        -------
        str
            A human-readable summary of what was done.
        """

    def __repr__(self) -> str:
        return f"<Workflow:{self.name}>"
