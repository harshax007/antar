"""
Antar — Agent Task Queue & Scaling Worker
=================================================
Provides an asynchronous task queue for decoupling heavy multi-agent
reasoning from the HTTP request loop.
"""

import asyncio
from typing import Callable
import uuid

class TaskWorker:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.results = {}
        self._worker_task = None

    async def start(self):
        """Starts the background worker loop."""
        if not self._worker_task:
            self._worker_task = asyncio.create_task(self._run_loop())

    async def stop(self):
        """Stops the background worker loop."""
        if self._worker_task:
            self._worker_task.cancel()
            self._worker_task = None

    async def _run_loop(self):
        while True:
            try:
                task_id, func, args, kwargs = await self.queue.get()
                try:
                    res = await func(*args, **kwargs)
                    self.results[task_id] = {"status": "DONE", "result": res}
                except Exception as e:
                    from app.core.security import public_error
                    self.results[task_id] = {"status": "ERROR", **public_error(e, "job")}
                finally:
                    self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Worker loop error: {e}")

    async def submit_task(self, func: Callable, *args, **kwargs) -> str:
        """Submit an async function to run in the background."""
        task_id = f"TASK-{uuid.uuid4().hex[:8].upper()}"
        self.results[task_id] = {"status": "PENDING"}
        await self.queue.put((task_id, func, args, kwargs))
        return task_id

    def get_result(self, task_id: str) -> dict:
        return self.results.get(task_id, {"status": "NOT_FOUND"})

# Global worker instance
worker = TaskWorker()
