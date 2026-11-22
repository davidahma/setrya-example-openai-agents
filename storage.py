"""Support answers backed by a native OpenAI Agents SQLiteSession."""
import asyncio
from contextlib import closing, contextmanager
import sqlite3

from agents import SQLiteSession
import yaml

STACK = "openai-agents"


class SupportSession:
    def __init__(self, path):
        self.path = path

    def answer(self, question):
        session = SQLiteSession("ticket-204", str(self.path))
        try:
            items = asyncio.run(session.get_items())
        finally:
            session.close()
        expected = "Thursday" if question == "When is dispatch?" else "Harbor-17"
        return next((item["content"] for item in items if item.get("content") == expected), "No matching note.")

    def erase(self):
        # The application recorded row 1 when it seeded this disposable customer's note.
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("DELETE FROM agent_messages WHERE session_id=? AND id=?", ("ticket-204", 1))
            db.commit()

    def configure_case(self, path):
        case = yaml.safe_load(path.read_text())
        case["stores"]["memory"]["artifacts"]["2"] = "preserve"
        case["facts"]["target"]["stored"] = {"absent": [{"role": "user", "content": "Thursday"}]}
        path.write_text(yaml.safe_dump(case, sort_keys=False))


@contextmanager
def open_fixture(root, env):
    path = root / "session.sqlite"
    session = SQLiteSession("ticket-204", str(path))
    try:
        asyncio.run(session.add_items([{"role": "user", "content": text} for text in ("Harbor-17", "Thursday")]))
    finally:
        session.close()
    env["SETRYA_TEST_AGENTS_DB"] = str(path)
    yield SupportSession(path)
