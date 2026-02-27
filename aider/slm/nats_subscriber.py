from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable

from nats.aio.client import Client as NATS


class NatsLogSubscriber:
    """Subscribe to Fly.io's internal NATS log stream.

    Fly log subjects are typically: logs.<app_name>.<region>.<machine_id>

    This subscriber expects auth via (user=org_slug, password=fly_token).
    """

    def __init__(
        self,
        *,
        nats_url: str,
        subject: str,
        user: str,
        password: str,
        on_log_line: Callable[[str], Awaitable[None]],
        queue: str | None = None,
    ):
        self.nats_url = nats_url
        self.subject = subject
        self.queue = queue
        self.user = user
        self.password = password
        self.on_log_line = on_log_line

        self._nc: NATS | None = None
        self._sub = None
        self._task: asyncio.Task | None = None

        self._q: asyncio.Queue[str] = asyncio.Queue(maxsize=2000)
        self._stop = asyncio.Event()

    async def start(self) -> None:
        self._stop.clear()
        self._nc = NATS()

        async def _disconnected_cb():
            print("slm.nats: disconnected")

        async def _reconnected_cb():
            print(f"slm.nats: reconnected to {self._nc.connected_url.netloc}")

        async def _closed_cb():
            print("slm.nats: closed")

        async def _error_cb(e: Exception):
            print(f"slm.nats: error: {e!r}")

        await self._nc.connect(
            servers=[self.nats_url],
            user=self.user,
            password=self.password,
            name="slm-log-subscriber",
            max_reconnect_attempts=-1,
            reconnect_time_wait=1,
            ping_interval=20,
            max_outstanding_pings=3,
            disconnected_cb=_disconnected_cb,
            reconnected_cb=_reconnected_cb,
            closed_cb=_closed_cb,
            error_cb=_error_cb,
        )

        async def _on_msg(msg):
            # Fly logs are usually JSON.
            try:
                raw = msg.data.decode("utf-8", errors="replace")
            except Exception:
                return

            # Attempt to extract a line-ish string for the reasoning engine.
            line = raw
            try:
                evt = json.loads(raw)
                # Common payload: {"message": "..."}
                line = evt.get("message") or evt.get("msg") or raw
            except Exception:
                pass

            try:
                self._q.put_nowait(str(line))
            except asyncio.QueueFull:
                # Drop under backpressure.
                return

        self._sub = await self._nc.subscribe(
            subject=self.subject,
            queue=self.queue,
            cb=_on_msg,
            pending_msgs_limit=1024,
            pending_bytes_limit=8 * 1024 * 1024,
        )

        self._task = asyncio.create_task(self._consumer())
        print(f"slm.nats: subscribed {self.subject} (queue={self.queue!r})")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self._sub is not None:
            try:
                await self._sub.unsubscribe()
            except Exception:
                pass

        if self._nc:
            try:
                await self._nc.drain()
            except Exception:
                pass

    async def _consumer(self) -> None:
        while not self._stop.is_set():
            line = await self._q.get()
            try:
                await self.on_log_line(line)
            except Exception as e:
                # Never let failures kill the stream.
                print(f"slm.nats: on_log_line error: {e!r}")


__all__ = ["NatsLogSubscriber"]
