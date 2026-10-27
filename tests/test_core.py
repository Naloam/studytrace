import hashlib
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from core import Workspace, chunks

SEARCH = "Binary search needs a sorted collection. It halves the search interval after each comparison. Its comparison complexity is O(log n)."
TRANSACTIONS = "A database transaction is atomic: operations either all commit or all roll back. Isolation governs concurrent observations."


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.filename = Path(self.temp.name) / "study.db"
        self.workspace = Workspace(self.filename)

    def tearDown(self):
        self.workspace.close()
        self.temp.cleanup()

    def add_search(self):
        return self.workspace.add_document("Searching", SEARCH)["id"]

    def make_plan(self, minutes=25):
        self.add_search()
        return self.workspace.create_plan("binary search comparison", minutes)

    def test_empty_shelf_abstains_and_does_not_create_plan(self):
        self.assertEqual(self.workspace.ask("binary search")["status"], "no_sources")
        with self.assertRaises(ValueError):
            self.workspace.create_plan("binary search", 25)
        self.assertEqual(self.workspace.plans(), [])

    def test_dedup_and_persistence_without_exposing_raw_notes_in_index(self):
        doc_id = self.add_search()
        self.assertEqual(self.workspace.add_document("Renamed", SEARCH), {"id": doc_id, "duplicate": True})
        self.workspace.close()
        self.workspace = Workspace(self.filename)
        metadata = self.workspace.documents()[0]
        self.assertNotIn("text", metadata)
        self.assertEqual(metadata["digest"], hashlib.sha256(SEARCH.encode()).hexdigest())
        self.assertEqual(metadata["characters"], len(SEARCH))

    def test_exact_citation_offsets_and_ranking(self):
        doc_id = self.add_search()
        self.workspace.add_document("Transactions", TRANSACTIONS)
        result = self.workspace.ask("binary search comparison")
        self.assertEqual(result["status"], "evidence_found")
        self.assertEqual(result["citations"][0]["document_id"], doc_id)
        notes = {d["id"]: d["text"] for d in self.workspace.documents(full=True)}
        for c in result["citations"]:
            self.assertEqual(c["quote"], notes[c["document_id"]][c["start"] : c["end"]])
        self.assertIn("not factual truth", result["notice"])
        self.assertEqual(result["trace"][-1]["tool"], "tfidf.retrieve")

    def test_unrelated_query_abstains(self):
        self.add_search()
        self.assertEqual(self.workspace.ask("量子引力与宇宙膨胀")["status"], "insufficient_evidence")

    def test_chinese_notes_and_offsets(self):
        text = "数据库事务：原子性保证所有操作一起提交或一起回滚。隔离性控制并发事务如何观察彼此的修改。"
        self.workspace.add_document("事务笔记", text)
        c = self.workspace.ask("事务原子性提交回滚")["citations"][0]
        self.assertEqual(c["quote"], text[c["start"] : c["end"]])

    def test_chunk_coverage_and_overlap_without_triple_counting(self):
        text = "binary search sorted collection comparison halves interval. " * 45
        pieces = list(chunks(text))
        self.assertEqual(pieces[0][0], 0)
        self.assertEqual(pieces[-1][1], len(text))
        for start, end, quote in pieces:
            self.assertEqual(quote, text[start:end])
        self.workspace.add_document("Long note", text)
        citations = self.workspace.ask("binary search sorted")["citations"]
        self.assertLessEqual(len(citations), 3)
        self.assertTrue(
            all(
                abs(a["start"] - b["start"]) >= 600
                for i, a in enumerate(citations)
                for b in citations[i + 1 :]
            )
        )

    def test_plan_budget_is_bounded_and_not_a_prediction(self):
        self.add_search()
        self.workspace.add_document(
            "Second source",
            "Binary search comparison of sorted arrays uses logarithmic comparisons and halves intervals repeatedly.",
        )
        for minutes in (10, 25, 120):
            plan = self.workspace.create_plan("binary search", minutes)
            self.assertGreater(len(plan["tasks"]), 0)
            self.assertLessEqual(sum(t["minutes"] for t in plan["tasks"]), minutes)
            self.assertIn("not validated predictions", plan["notice"])
            self.assertTrue(all(t["source_available"] for t in plan["tasks"]))

    def test_review_is_persistent_idempotent_and_uses_declared_interval(self):
        plan = self.make_plan()
        task = plan["tasks"][0]
        after = self.workspace.review(plan["id"], task["id"], "needs_practice")
        due = datetime.fromisoformat(after["tasks"][0]["next_review_at"])
        self.assertAlmostEqual((due - datetime.now(timezone.utc)).total_seconds() / 86400, 1, places=3)
        self.workspace.review(plan["id"], task["id"], "needs_practice")
        self.assertEqual(self.workspace.stats()["review_events"], 1)
        self.workspace.review(plan["id"], task["id"], "recalled")
        self.assertEqual(self.workspace.stats()["review_events"], 2)
        self.assertEqual(self.workspace.get_plan(plan["id"])["tasks"][0]["rating"], "recalled")

    def test_delete_purges_saved_quotes_and_prevents_review(self):
        plan = self.make_plan()
        task = plan["tasks"][0]
        self.assertTrue(self.workspace.delete_document(task["citation"]["document_id"]))
        after = self.workspace.get_plan(plan["id"])
        self.assertEqual(after["tasks"][0]["citation"]["quote"], "")
        self.assertFalse(after["tasks"][0]["source_available"])
        with self.assertRaises(ValueError):
            self.workspace.review(plan["id"], task["id"], "recalled")
        self.assertNotIn(
            SEARCH, self.workspace.connection.execute("SELECT payload FROM study_plans").fetchone()[0]
        )

    def test_notes_limit_still_permits_dedup(self):
        for n in range(20):
            self.workspace.add_document(str(n), SEARCH + str(n))
        self.assertTrue(self.workspace.add_document("same", SEARCH + "0")["duplicate"])
        with self.assertRaises(ValueError):
            self.workspace.add_document("21", SEARCH + "extra")

    def test_plan_history_is_bounded(self):
        self.add_search()
        first = self.workspace.create_plan("binary search", 10)["id"]
        for _ in range(30):
            self.workspace.create_plan("binary search", 10)
        self.assertEqual(len(self.workspace.plans()), 30)
        with self.assertRaises(KeyError):
            self.workspace.get_plan(first)

    def test_invalid_questions_budgets_and_reviews(self):
        for question in ("", "  ", 5, "x" * 1001):
            with self.assertRaises(ValueError):
                self.workspace.ask(question)
        for minutes in (True, "25", 9, 121, 20.0):
            with self.assertRaises(ValueError):
                self.workspace.create_plan("binary search", minutes)
        plan = self.make_plan()
        with self.assertRaises(ValueError):
            self.workspace.review(plan["id"], plan["tasks"][0]["id"], "mastered")
        with self.assertRaises(KeyError):
            self.workspace.review(plan["id"], "missing", "recalled")

    def test_invalid_notes_do_not_persist(self):
        for title, text in (
            (" ", SEARCH),
            ("x" * 151, SEARCH),
            ("ok", "short"),
            ("ok", " " * 20),
            ("ok", "a" * 30001),
        ):
            with self.assertRaises(ValueError):
                self.workspace.add_document(title, text)
        self.assertEqual(self.workspace.documents(), [])


if __name__ == "__main__":
    unittest.main()
