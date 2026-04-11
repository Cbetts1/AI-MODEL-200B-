"""aura/cloud/virtual_cpu.py — AURA Virtual CPU (vCPU).

The VirtualCPU is an in-process task scheduler backed by a
``concurrent.futures.ThreadPoolExecutor``.  It exposes:

  • submit(fn, *args, **kwargs)  — schedule a callable, returns a Future
  • expand(n)                    — add *n* worker threads at runtime
  • shrink(n)                    — gracefully remove *n* idle threads
  • stats()                      — real-time metrics dict
  • shutdown()                   — drain pending work and stop

The vCPU is deliberately independent of the host OS process scheduler —
it manages its own thread-pool lifecycle and maintains counters for all
task lifecycle events (queued → running → done / failed).

Usage
-----
    from aura.cloud.virtual_cpu import VirtualCPU
    cpu = VirtualCPU(workers=4)
    future = cpu.submit(some_function, arg1, kwarg=val)
    result = future.result()
    print(cpu.stats())
    cpu.shutdown()
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Dict


class VirtualCPU:
    """In-process thread-pool task scheduler acting as a virtual CPU.

    Parameters
    ----------
    workers:
        Initial number of concurrent worker threads.
    name:
        Human-readable identifier for this vCPU instance.
    """

    def __init__(self, workers: int = 4, name: str = "vcpu-0") -> None:
        if workers < 1:
            raise ValueError("workers must be >= 1")
        self.name = name
        self._workers = workers
        self._lock = threading.Lock()
        self._executor: ThreadPoolExecutor = ThreadPoolExecutor(
            max_workers=workers, thread_name_prefix=f"aura-{name}"
        )
        self._queued: int = 0
        self._running: int = 0
        self._completed: int = 0
        self._failed: int = 0
        self._started_at: float = time.time()
        self._shutdown_flag: bool = False

    # ── public API ─────────────────────────────────────────────────────────────

    def submit(self, fn: Callable, *args: Any, **kwargs: Any) -> Future:
        """Schedule *fn* for execution.  Returns a :class:`Future`."""
        if self._shutdown_flag:
            raise RuntimeError(f"VirtualCPU '{self.name}' has been shut down")
        with self._lock:
            self._queued += 1

        def _wrapper(*a: Any, **kw: Any) -> Any:
            with self._lock:
                self._queued -= 1
                self._running += 1
            try:
                result = fn(*a, **kw)
                with self._lock:
                    self._completed += 1
                return result
            except Exception:
                with self._lock:
                    self._failed += 1
                raise
            finally:
                with self._lock:
                    self._running -= 1

        return self._executor.submit(_wrapper, *args, **kwargs)

    def expand(self, n: int = 1) -> int:
        """Add *n* worker threads.  Returns the new total worker count."""
        if n < 1:
            raise ValueError("n must be >= 1")
        # ThreadPoolExecutor doesn't natively support dynamic resize;
        # we replace the executor while draining the old one.
        with self._lock:
            new_workers = self._workers + n
            old_executor = self._executor
            self._executor = ThreadPoolExecutor(
                max_workers=new_workers,
                thread_name_prefix=f"aura-{self.name}",
            )
            self._workers = new_workers
        # Shut down old executor without waiting (allow queued tasks to drain)
        old_executor.shutdown(wait=False, cancel_futures=False)
        return new_workers

    def shrink(self, n: int = 1) -> int:
        """Remove *n* worker threads (minimum 1 retained).  Returns new count."""
        if n < 1:
            raise ValueError("n must be >= 1")
        with self._lock:
            new_workers = max(1, self._workers - n)
            old_executor = self._executor
            self._executor = ThreadPoolExecutor(
                max_workers=new_workers,
                thread_name_prefix=f"aura-{self.name}",
            )
            self._workers = new_workers
        old_executor.shutdown(wait=False, cancel_futures=False)
        return new_workers

    def stats(self) -> Dict[str, Any]:
        """Return a real-time snapshot of vCPU metrics."""
        with self._lock:
            return {
                "name": self.name,
                "workers": self._workers,
                "queued": self._queued,
                "running": self._running,
                "completed": self._completed,
                "failed": self._failed,
                "uptime_seconds": round(time.time() - self._started_at, 2),
                "active": not self._shutdown_flag,
            }

    def shutdown(self, wait: bool = True) -> None:
        """Drain pending work and shut down the vCPU."""
        self._shutdown_flag = True
        self._executor.shutdown(wait=wait, cancel_futures=False)
