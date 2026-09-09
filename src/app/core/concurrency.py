import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.core.exceptions import ProviderUnavailableError


class InferenceLimiter:
    """
    Non-blocking concurrency limiter for ML inference.

    If all inference slots are occupied, a new request is rejected
    immediately instead of waiting.
    """

    def __init__(
        self,
        *,
        max_inflight: int,
    ) -> None:
        if max_inflight < 1:
            raise ValueError(
                "max_inflight must be at least 1."
            )

        self._max_inflight = max_inflight
        self._inflight = 0
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        async with self._lock:
            if self._inflight >= self._max_inflight:
                raise ProviderUnavailableError(
                    "Inference is currently busy. Please try again shortly.",
                    details={
                        "reason": "inference_capacity_exceeded",
                        "max_inflight": self._max_inflight,
                        "inflight": self._inflight,
                    },
                )

            self._inflight += 1

        try:
            yield
        finally:
            async with self._lock:
                self._inflight -= 1

    @property
    def inflight(self) -> int:
        return self._inflight

    @property
    def max_inflight(self) -> int:
        return self._max_inflight
