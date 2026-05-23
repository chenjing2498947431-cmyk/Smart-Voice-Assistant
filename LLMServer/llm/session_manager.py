"""
会话状态管理 (sid -> latest_response_id + system_prompt)。

为什么需要它:
火山 Responses API 的对话历史是靠 previous_response_id 一轮一轮串起来的,
每轮服务端返回一个新的 response.id, 下一轮要拿这个 id 当 previous。
而 RTC / 前端只能存一个稳定的 sid, 不可能跟着每轮换。
所以服务端必须维护 sid -> 最新 response_id 的映射。

存储: 内存 dict 做热缓存, miss 时回落 SQLite 拉; 写时双写 (内存 + DB)。
服务重启后内存丢, 但 DB 还在, 用户拿旧 sid 进来仍能续聊。
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Optional

from storage import sqlite as storage


@dataclass
class SessionState:
    system_prompt: str
    latest_response_id: str = ""
    created_at: float = field(default_factory=lambda: 0.0)


class SessionManager:
    def __init__(self):
        self._map: dict[str, SessionState] = {}
        self._lock = asyncio.Lock()

    async def new_session(self, system_prompt: str) -> str:
        sid = "sess-" + uuid.uuid4().hex[:20]
        st = SessionState(system_prompt=system_prompt)
        async with self._lock:
            self._map[sid] = st
        # 同步写 DB, 拿到 sid 之前对外不返回
        await storage.insert_conversation(sid, system_prompt)
        return sid

    async def get(self, sid: str) -> Optional[SessionState]:
        async with self._lock:
            st = self._map.get(sid)
        if st is not None:
            return st
        # 内存 miss: 去 DB 拉
        row = await storage.get_conversation(sid)
        if row is None:
            return None
        st = SessionState(
            system_prompt=row.get("system_prompt") or "",
            latest_response_id=row.get("latest_response_id") or "",
            created_at=float(row.get("created_at") or 0),
        )
        async with self._lock:
            self._map[sid] = st
        return st

    async def update_latest(self, sid: str, response_id: str) -> None:
        async with self._lock:
            st = self._map.get(sid)
            if st is not None:
                st.latest_response_id = response_id
        await storage.update_latest_response_id(sid, response_id)

    async def drop(self, sid: str) -> None:
        async with self._lock:
            self._map.pop(sid, None)
        await storage.delete_conversation(sid)


_manager: Optional[SessionManager] = None


def get_manager() -> SessionManager:
    global _manager
    if _manager is None:
        _manager = SessionManager()
    return _manager
