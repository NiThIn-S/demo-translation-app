import pytest

from app.core.concurrency import InferenceLimiter
from app.core.exceptions import ProviderUnavailableError


@pytest.mark.asyncio
async def test_limiter_allows_one_inference():
    limiter = InferenceLimiter(max_inflight=1)

    async with limiter.slot():
        assert limiter.inflight == 1

    assert limiter.inflight == 0


@pytest.mark.asyncio
async def test_limiter_rejects_when_busy():
    limiter = InferenceLimiter(max_inflight=1)

    async with limiter.slot():
        with pytest.raises(ProviderUnavailableError) as exc_info:
            async with limiter.slot():
                pass

    assert exc_info.value.details["reason"] == "inference_capacity_exceeded"


@pytest.mark.asyncio
async def test_limiter_releases_after_exception():
    limiter = InferenceLimiter(max_inflight=1)

    with pytest.raises(RuntimeError):
        async with limiter.slot():
            raise RuntimeError("boom")

    assert limiter.inflight == 0

    async with limiter.slot():
        assert limiter.inflight == 1
