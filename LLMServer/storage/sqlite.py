"""
对话记录的持久化层 (SQLite, 单文件)。

- 表 conversations: 一行 = 一段会话, 含 sid / title / system_prompt / 最新 response_id
- 表 messages:      一行 = 一条消息, 关联 sid, 区分 role=user/assistant

接口都是 async, 用 aiosqlite, 不阻塞事件循环。
启动时调一次 init_db() 自动建表。
"""

import os
import time
from typing import Optional

import aiosqlite

# data 目录跟 LLMServer 同级, 改路径只需要改这里
_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "data", "conversations.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    sid                 TEXT PRIMARY KEY,
    title               TEXT NOT NULL DEFAULT '新会话',
    system_prompt       TEXT NOT NULL DEFAULT '',
    latest_response_id  TEXT NOT NULL DEFAULT '',
    created_at          INTEGER NOT NULL,
    updated_at          INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sid          TEXT NOT NULL,
    role         TEXT NOT NULL,
    content      TEXT NOT NULL,
    response_id  TEXT NOT NULL DEFAULT '',
    created_at   INTEGER NOT NULL,
    FOREIGN KEY (sid) REFERENCES conversations(sid) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_sid_id ON messages(sid, id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC);
"""


def _now() -> int:
    return int(time.time())


async def init_db() -> None:
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.executescript(_SCHEMA)
        await db.commit()


# ---------------- conversations ----------------

async def insert_conversation(sid: str, system_prompt: str) -> None:
    ts = _now()
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO conversations (sid, title, system_prompt, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (sid, "新会话", system_prompt, ts, ts),
        )
        await db.commit()


async def get_conversation(sid: str) -> Optional[dict]:
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT sid, title, system_prompt, latest_response_id, created_at, updated_at "
            "FROM conversations WHERE sid = ?",
            (sid,),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def list_conversations(limit: int = 100) -> list[dict]:
    """按 updated_at 倒序; 每条带最后一条消息的预览, 便于侧栏展示。"""
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT c.sid, c.title, c.created_at, c.updated_at,
                   (SELECT content FROM messages m
                    WHERE m.sid = c.sid ORDER BY m.id DESC LIMIT 1) AS last_message
            FROM conversations c
            ORDER BY c.updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def update_latest_response_id(sid: str, response_id: str) -> None:
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            "UPDATE conversations SET latest_response_id = ?, updated_at = ? WHERE sid = ?",
            (response_id, _now(), sid),
        )
        await db.commit()


async def update_title_if_default(sid: str, title: str) -> None:
    """只在标题还是默认值时改, 避免覆盖用户手动改过的。"""
    title = (title or "").strip()[:30] or "新会话"
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            "UPDATE conversations SET title = ?, updated_at = ? "
            "WHERE sid = ? AND (title = '' OR title = '新会话')",
            (title, _now(), sid),
        )
        await db.commit()


async def delete_conversation(sid: str) -> None:
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute("DELETE FROM messages WHERE sid = ?", (sid,))
        await db.execute("DELETE FROM conversations WHERE sid = ?", (sid,))
        await db.commit()


# ---------------- messages ----------------

async def insert_message(sid: str, role: str, content: str, response_id: str = "") -> int:
    async with aiosqlite.connect(_DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO messages (sid, role, content, response_id, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (sid, role, content, response_id, _now()),
        )
        await db.commit()
        return cur.lastrowid


async def list_messages(sid: str) -> list[dict]:
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, role, content, response_id, created_at FROM messages "
            "WHERE sid = ? ORDER BY id ASC",
            (sid,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def count_messages(sid: str) -> int:
    async with aiosqlite.connect(_DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM messages WHERE sid = ?", (sid,)
        ) as cur:
            row = await cur.fetchone()
            return int(row[0]) if row else 0
