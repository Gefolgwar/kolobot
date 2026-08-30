"""Dual-capable async API key pool with sliding RPM/RPD and 429 cooldown."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class PoolKind(str, Enum):
    GENERATE = "generate"
    EMBED = "embed"


class KeyPoolExhausted(RuntimeError):
    """No key is currently available under RPM/RPD/cooldown constraints."""


@dataclass
class _KeyState:
    key: str
    timestamps: List[float] = field(default_factory=list)
    cooldown_until: float = 0.0
    in_flight: bool = False


class KeyPool:
    """
    Deep module: select a usable key under sliding RPM/RPD, round-robin,
    per-key cooldown on 429, asyncio.Lock-safe.
    """

    def __init__(
        self,
        keys: List[str],
        kind: PoolKind,
        *,
        rpm_limit: int = 15,
        rpd_limit: int = 1500,
        cooldown_sec: int = 60,
        time_fn: Optional[Callable[[], float]] = None,
    ) -> None:
        if not keys:
            raise ValueError("KeyPool requires at least one key")
        self.kind = kind
        self.rpm_limit = rpm_limit
        self.rpd_limit = rpd_limit
        self.cooldown_sec = cooldown_sec
        self._time = time_fn or time.time
        self._states: List[_KeyState] = [_KeyState(key=k) for k in keys]
        self._rr_index = 0
        self._lock = asyncio.Lock()

    def _prune(self, state: _KeyState, now: float) -> None:
        day_ago = now - 86_400
        state.timestamps = [t for t in state.timestamps if t > day_ago]

    def _rpm_ok(self, state: _KeyState, now: float) -> bool:
        minute_ago = now - 60
        recent = sum(1 for t in state.timestamps if t > minute_ago)
        return recent < self.rpm_limit

    def _rpd_ok(self, state: _KeyState) -> bool:
        return len(state.timestamps) < self.rpd_limit

    def _is_free(self, state: _KeyState, now: float) -> bool:
        if state.in_flight:
            return False
        if state.cooldown_until > now:
            return False
        self._prune(state, now)
        return self._rpm_ok(state, now) and self._rpd_ok(state)

    def _pick_locked(self, now: float) -> Optional[str]:
        n = len(self._states)
        for offset in range(n):
            idx = (self._rr_index + offset) % n
            state = self._states[idx]
            if self._is_free(state, now):
                state.in_flight = True
                self._rr_index = (idx + 1) % n
                return state.key
        return None

    async def acquire(self, wait_sec: float = 0.0, poll_sec: float = 0.05) -> str:
        """
        Acquire a free key. If wait_sec > 0, poll until deadline.
        Raises KeyPoolExhausted when none available.
        """
        deadline = self._time() + max(0.0, wait_sec)
        while True:
            async with self._lock:
                now = self._time()
                key = self._pick_locked(now)
                if key is not None:
                    return key
            now = self._time()
            if now >= deadline:
                raise KeyPoolExhausted(f"No free keys in {self.kind.value} pool")
            await asyncio.sleep(min(poll_sec, max(0.0, deadline - now)))

    async def release(
        self,
        key: str,
        *,
        ok: bool = True,
        http_status: Optional[int] = None,
    ) -> None:
        async with self._lock:
            now = self._time()
            for state in self._states:
                if state.key != key:
                    continue
                state.in_flight = False
                state.timestamps.append(now)
                self._prune(state, now)
                if http_status in (400, 403, 429, 503):
                    cooldown = 86_400 if http_status in (400, 403) else self.cooldown_sec
                    state.cooldown_until = now + cooldown
                return
            raise KeyError(f"Unknown key for pool {self.kind.value}")

    def update_keys(self, keys: List[str], reset_cooldown: bool = False) -> None:
        """Update or refresh the key list in the pool."""
        if not keys:
            return
        existing_map = {s.key: s for s in self._states}
        new_states = []
        for k in keys:
            if k in existing_map:
                st = existing_map[k]
                if reset_cooldown:
                    st.cooldown_until = 0.0
                new_states.append(st)
            else:
                new_states.append(_KeyState(key=k))
        self._states = new_states

    @property
    def key_count(self) -> int:
        return len(self._states)

    def get_key_label(self, key: str) -> str:
        for idx, state in enumerate(self._states, start=1):
            if state.key == key:
                masked = f"…{key[-4:]}" if len(key) >= 6 else ""
                return f"Ключ #{idx}" + (f" ({masked})" if masked else "")
        masked = f"…{key[-4:]}" if len(key) >= 6 else ""
        return "Ключ" + (f" ({masked})" if masked else "")

    def get_key_status_list(self) -> List[Dict[str, Any]]:
        now = self._time()
        result = []
        for idx, state in enumerate(self._states, start=1):
            self._prune(state, now)
            minute_ago = now - 60
            rpm_used = sum(1 for t in state.timestamps if t > minute_ago)
            rpd_used = len(state.timestamps)

            is_cooling = state.cooldown_until > now
            cooldown_sec = int(state.cooldown_until - now) if is_cooling else 0
            is_available = self._is_free(state, now)

            masked = f"…{state.key[-4:]}" if len(state.key) >= 6 else ""
            label = f"Ключ #{idx}" + (f" ({masked})" if masked else "")

            if is_cooling:
                status_desc = f"❌ Cooldown ({cooldown_sec}с)"
            elif state.in_flight:
                status_desc = "⏳ В процесі"
            elif not self._rpm_ok(state, now):
                status_desc = f"⚠️ RPM ліміт ({rpm_used}/{self.rpm_limit})"
            elif not self._rpd_ok(state):
                status_desc = f"⚠️ RPD ліміт ({rpd_used}/{self.rpd_limit})"
            else:
                status_desc = f"✅ Доступний (RPM {rpm_used}/{self.rpm_limit})"

            result.append({
                "index": idx,
                "label": label,
                "is_available": is_available,
                "is_cooling": is_cooling,
                "cooldown_sec": cooldown_sec,
                "in_flight": state.in_flight,
                "rpm_used": rpm_used,
                "rpd_used": rpd_used,
                "status_desc": status_desc,
            })
        return result

    def status(self) -> Dict[str, object]:
        now = self._time()
        available = cooldown = limited = in_flight = 0
        for state in self._states:
            self._prune(state, now)
            if state.cooldown_until > now:
                cooldown += 1
            elif state.in_flight:
                in_flight += 1
            elif self._rpm_ok(state, now) and self._rpd_ok(state):
                available += 1
            else:
                limited += 1
        return {
            "kind": self.kind.value,
            "total": len(self._states),
            "available": available,
            "cooldown": cooldown,
            "in_flight": in_flight,
            "limited": limited,
        }
