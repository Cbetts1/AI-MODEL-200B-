"""aura/tools/timer.py — Simple countdown timer / reminder tool.

Sets a timer that counts down in the background.  Since AURA is primarily
a chat interface, the timer records the start time and can be checked later.

Usage (in chat)
---------------
    /tool timer 5           Set a 5-minute timer.
    /tool timer 0.5         Set a 30-second timer.
    /tool timer check       Check running timers.
    /tool timer clear       Clear all timers.
"""

from __future__ import annotations

import time
from typing import Dict, Tuple

from .registry import Tool


# In-memory timer store: name → (label, start_time, duration_seconds)
_timers: Dict[str, Tuple[str, float, float]] = {}
_timer_counter = 0


class TimerTool(Tool):
    """Set and check countdown timers."""

    name = "timer"
    description = "Set a timer (minutes). Usage: /tool timer <minutes> or /tool timer check"

    def run(self, args: str) -> str:
        global _timer_counter

        cmd = args.strip().lower()
        if not cmd:
            return "[timer] Usage: /tool timer <minutes> | check | clear"

        if cmd == "check":
            return self._check()

        if cmd == "clear":
            _timers.clear()
            return "⏱️ All timers cleared."

        # Try to parse as a number of minutes
        try:
            minutes = float(cmd)
        except ValueError:
            return f"[timer] '{cmd}' is not a valid number of minutes."

        if minutes <= 0:
            return "[timer] Please provide a positive number of minutes."

        _timer_counter += 1
        timer_id = f"timer_{_timer_counter}"
        seconds = minutes * 60
        _timers[timer_id] = (f"{minutes} min", time.time(), seconds)

        if minutes >= 1:
            label = f"{minutes:.0f} minute(s)" if minutes == int(minutes) else f"{minutes} minutes"
        else:
            label = f"{seconds:.0f} seconds"

        return f"⏱️ Timer set for {label}! (ID: {timer_id})\nUse `/tool timer check` to see status."

    def _check(self) -> str:
        if not _timers:
            return "⏱️ No active timers."

        lines = ["⏱️ **Active Timers:**", ""]
        finished = []
        now = time.time()
        for tid, (label, start, duration) in _timers.items():
            elapsed = now - start
            remaining = duration - elapsed
            if remaining <= 0:
                lines.append(f"  🔔 {tid} ({label}) — **DONE!** Time's up!")
                finished.append(tid)
            else:
                mins_left = remaining / 60
                if mins_left >= 1:
                    lines.append(f"  ⏳ {tid} ({label}) — {mins_left:.1f} min remaining")
                else:
                    lines.append(f"  ⏳ {tid} ({label}) — {remaining:.0f}s remaining")

        # Auto-clean finished timers
        for tid in finished:
            del _timers[tid]

        return "\n".join(lines)
