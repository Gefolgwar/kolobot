"""KeyPool behaviors: RR, RPM/RPD, cooldown, exhaustion, concurrent acquire."""

from __future__ import annotations

import asyncio

import pytest

from kolobot.key_pool import KeyPool, KeyPoolExhausted, PoolKind


class FakeClock:
    def __init__(self, start: float = 1_000.0) -> None:
        self.t = start

    def time(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


@pytest.mark.asyncio
async def test_round_robin_among_free_keys():
    clock = FakeClock()
    pool = KeyPool(
        keys=["a", "b", "c"],
        kind=PoolKind.GENERATE,
        rpm_limit=15,
        rpd_limit=1500,
        cooldown_sec=60,
        time_fn=clock.time,
    )

    k1 = await pool.acquire()
    await pool.release(k1, ok=True)
    k2 = await pool.acquire()
    await pool.release(k2, ok=True)
    k3 = await pool.acquire()
    await pool.release(k3, ok=True)
    k4 = await pool.acquire()
    await pool.release(k4, ok=True)

    assert [k1, k2, k3, k4] == ["a", "b", "c", "a"]


@pytest.mark.asyncio
async def test_rpm_blocks_key_until_window_slides():
    clock = FakeClock()
    pool = KeyPool(
        keys=["only"],
        kind=PoolKind.GENERATE,
        rpm_limit=2,
        rpd_limit=1500,
        cooldown_sec=60,
        time_fn=clock.time,
    )

    a = await pool.acquire()
    await pool.release(a, ok=True)
    b = await pool.acquire()
    await pool.release(b, ok=True)

    with pytest.raises(KeyPoolExhausted):
        await pool.acquire(wait_sec=0)

    clock.advance(61)
    c = await pool.acquire(wait_sec=0)
    assert c == "only"


@pytest.mark.asyncio
async def test_rpd_blocks_for_day_window():
    clock = FakeClock()
    pool = KeyPool(
        keys=["only"],
        kind=PoolKind.EMBED,
        rpm_limit=100,
        rpd_limit=2,
        cooldown_sec=60,
        time_fn=clock.time,
    )
    for _ in range(2):
        k = await pool.acquire()
        await pool.release(k, ok=True)

    with pytest.raises(KeyPoolExhausted):
        await pool.acquire(wait_sec=0)

    clock.advance(86_400)
    k = await pool.acquire(wait_sec=0)
    assert k == "only"


@pytest.mark.asyncio
async def test_429_puts_key_in_cooldown():
    clock = FakeClock()
    pool = KeyPool(
        keys=["a", "b"],
        kind=PoolKind.GENERATE,
        rpm_limit=15,
        rpd_limit=1500,
        cooldown_sec=60,
        time_fn=clock.time,
    )
    a = await pool.acquire()
    assert a == "a"
    await pool.release(a, ok=False, http_status=429)

    b = await pool.acquire()
    assert b == "b"

    # still cooling; only b free for another acquire after release
    await pool.release(b, ok=True)
    again = await pool.acquire()
    assert again == "b"

    clock.advance(60)
    after = await pool.acquire()
    await pool.release(after, ok=True)
    assert after == "a"


@pytest.mark.asyncio
async def test_exhaustion_when_all_keys_unavailable():
    clock = FakeClock()
    pool = KeyPool(
        keys=["a"],
        kind=PoolKind.GENERATE,
        rpm_limit=1,
        rpd_limit=1,
        cooldown_sec=60,
        time_fn=clock.time,
    )
    k = await pool.acquire()
    await pool.release(k, ok=False, http_status=429)
    with pytest.raises(KeyPoolExhausted):
        await pool.acquire(wait_sec=0)


@pytest.mark.asyncio
async def test_concurrent_acquire_does_not_hand_same_slot_unsafely():
    clock = FakeClock()
    pool = KeyPool(
        keys=["a", "b"],
        kind=PoolKind.GENERATE,
        rpm_limit=15,
        rpd_limit=1500,
        cooldown_sec=60,
        time_fn=clock.time,
    )

    results = await asyncio.gather(pool.acquire(), pool.acquire())
    assert sorted(results) == ["a", "b"]


@pytest.mark.asyncio
async def test_status_counts_without_exposing_keys():
    clock = FakeClock()
    pool = KeyPool(
        keys=["secret-one", "secret-two"],
        kind=PoolKind.EMBED,
        rpm_limit=15,
        rpd_limit=1500,
        cooldown_sec=60,
        time_fn=clock.time,
    )
    k = await pool.acquire()
    await pool.release(k, ok=False, http_status=429)
    snap = pool.status()
    blob = str(snap)
    assert "secret-one" not in blob
    assert "secret-two" not in blob
    assert snap["total"] == 2
    assert snap["cooldown"] == 1
    assert snap["available"] == 1
    assert snap["kind"] == "embed"


@pytest.mark.asyncio
async def test_overlap_keys_tracked_per_pool_instance():
    """Same physical key string may appear in two pools with independent trackers."""
    clock = FakeClock()
    gen = KeyPool(
        keys=["shared"],
        kind=PoolKind.GENERATE,
        rpm_limit=1,
        rpd_limit=10,
        cooldown_sec=60,
        time_fn=clock.time,
    )
    emb = KeyPool(
        keys=["shared"],
        kind=PoolKind.EMBED,
        rpm_limit=15,
        rpd_limit=10,
        cooldown_sec=60,
        time_fn=clock.time,
    )
    g = await gen.acquire()
    await gen.release(g, ok=False, http_status=429)
    # generate cooled; embed still free for same string
    e = await emb.acquire(wait_sec=0)
    assert e == "shared"


@pytest.mark.asyncio
async def test_400_invalid_key_puts_key_in_long_cooldown():
    clock = FakeClock()
    pool = KeyPool(
        keys=["bad_key", "good_key"],
        kind=PoolKind.EMBED,
        rpm_limit=15,
        rpd_limit=1500,
        cooldown_sec=60,
        time_fn=clock.time,
    )
    k1 = await pool.acquire()
    assert k1 == "bad_key"
    await pool.release(k1, ok=False, http_status=400)

    # Next acquire picks good_key
    k2 = await pool.acquire()
    assert k2 == "good_key"

    # bad_key is in long cooldown (86400s)
    clock.advance(3600)  # 1 hour later
    await pool.release(k2, ok=True)
    next_key = await pool.acquire()
    assert next_key == "good_key"  # bad_key still in cooldown
