"""End-to-end tests using the echo backend (no model, no network).

Run:  python -m unittest discover tests -v
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agent.config import Config
from agent.core import Agent
from agent.skills import load_skills
from agent.tools import dispatch, get_registry, load_builtin_tools


def make_agent(workdir: Path) -> Agent:
    cfg = Config(backend="echo", workdir=workdir, confirm_shell=False)
    return Agent(cfg)


class AgentLoopTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.agent = make_agent(self.dir)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_plain_reply(self):
        reply = self.agent.run_turn("hello")
        self.assertEqual(reply, "[echo] hello")

    def test_tool_roundtrip_write_then_read(self):
        self.agent.run_turn('!tool write_file {"path": "a.txt", "content": "hi"}')
        self.assertEqual((self.dir / "a.txt").read_text(), "hi")
        reply = self.agent.run_turn('!tool read_file {"path": "a.txt"}')
        self.assertIn("hi", reply)

    def test_unknown_tool_reports_error(self):
        reply = self.agent.run_turn('!tool nope {}')
        self.assertIn("unknown tool", reply)

    def test_session_persists(self):
        self.agent.run_turn("hello")
        sessions = list((self.dir / ".agent" / "sessions").glob("*.json"))
        self.assertEqual(len(sessions), 1)
        msgs = json.loads(sessions[0].read_text())
        self.assertEqual(msgs[-1]["role"], "assistant")

    def test_path_escape_rejected(self):
        reply = self.agent.run_turn('!tool read_file {"path": "../../etc/passwd"}')
        self.assertIn("ERROR", reply)


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.agent = make_agent(self.dir)
        self.ctx = self.agent.ctx

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_registry_has_core_tools(self):
        load_builtin_tools()
        names = set(get_registry())
        for expected in ("read_file", "write_file", "edit_file", "grep", "run_shell",
                         "remember", "recall", "task_add", "note_create", "journal"):
            self.assertIn(expected, names)

    def test_edit_requires_unique_match(self):
        (self.dir / "f.txt").write_text("aa aa")
        out = dispatch(self.ctx, "edit_file", {"path": "f.txt", "old_string": "aa", "new_string": "b"})
        self.assertIn("2 times", out)

    def test_memory_roundtrip(self):
        dispatch(self.ctx, "remember", {"fact": "the deploy branch is main"})
        out = dispatch(self.ctx, "recall", {"query": "deploy"})
        self.assertIn("deploy branch", out)
        dispatch(self.ctx, "forget", {"substring": "deploy"})
        self.assertIn("empty", dispatch(self.ctx, "recall", {}) + "(memory is empty)")

    def test_tasks_lifecycle(self):
        dispatch(self.ctx, "task_add", {"title": "step one"})
        out = dispatch(self.ctx, "task_update", {"number": 1, "state": "completed"})
        self.assertIn("[x] 1. step one", out)

    def test_grep_finds_content(self):
        (self.dir / "x.py").write_text("def hello():\n    pass\n")
        out = dispatch(self.ctx, "grep", {"pattern": "def hello"})
        self.assertIn("x.py:1", out)


class BrainTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.agent = make_agent(self.dir)
        self.ctx = self.agent.ctx

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_note_create_read_and_backlinks(self):
        dispatch(self.ctx, "note_create", {"title": "Python Tips", "content": "Use pathlib.", "tags": "resource"})
        dispatch(self.ctx, "note_create", {"title": "Project Ideas", "content": "See [[Python Tips]]."})
        out = dispatch(self.ctx, "note_read", {"title": "Python Tips"})
        self.assertIn("Use pathlib.", out)
        self.assertIn("Backlinks: project-ideas", out)

    def test_note_search_by_text_and_tag(self):
        dispatch(self.ctx, "note_create", {"title": "Meeting", "content": "Discussed roadmap.", "tags": "work"})
        self.assertIn("meeting.md", dispatch(self.ctx, "note_search", {"query": "roadmap"}))
        self.assertIn("meeting.md", dispatch(self.ctx, "note_search", {"query": "", "tag": "work"}))

    def test_journal_appends(self):
        dispatch(self.ctx, "journal", {"entry": "shipped the agent"})
        files = list((self.dir / "brain" / "journal").glob("*.md"))
        self.assertEqual(len(files), 1)
        self.assertIn("shipped the agent", files[0].read_text())

    def test_overview(self):
        dispatch(self.ctx, "note_create", {"title": "Solo", "content": "unlinked", "tags": "idea"})
        out = dispatch(self.ctx, "brain_overview", {})
        self.assertIn("1 notes", out)
        self.assertIn("idea(1)", out)


class SkillTests(unittest.TestCase):
    def test_repo_skills_load(self):
        cfg = Config(backend="echo", workdir=Path(__file__).resolve().parent.parent)
        skills = load_skills(cfg)
        self.assertIn("code-review", skills)
        self.assertIn("second-brain", skills)
        self.assertTrue(skills["second-brain"].description)

    def test_use_skill_injects_instructions(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            sdir = root / "skills" / "greet"
            sdir.mkdir(parents=True)
            (sdir / "SKILL.md").write_text("---\nname: greet\ndescription: greets\n---\nAlways say hi.")
            agent = make_agent(root)
            self.assertEqual(agent.use_skill("greet"), "loaded skill greet")
            self.assertIn("Always say hi.", agent.messages[-1]["content"])
            self.assertIn("unknown skill", agent.use_skill("nope"))


if __name__ == "__main__":
    unittest.main()
