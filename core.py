"""Local evidence retrieval and bounded study planning; no model or document network calls."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def stamp():
    return datetime.now(UTC).isoformat()


def chunks(text, size=600, overlap=80):
    """Offsets always refer to the exact stored text; citations are never model-generated."""
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if text[start:end].strip():
            yield start, end, text[start:end]
        if end == len(text):
            break
        start = end - overlap


class Workspace:
    def __init__(self, filename):
        self.connection = sqlite3.connect(filename)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, text TEXT NOT NULL,
                digest TEXT NOT NULL, origin TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS study_plans (
                id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS review_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, plan_id TEXT NOT NULL,
                task_id TEXT NOT NULL, rating TEXT NOT NULL, at TEXT NOT NULL);
        """)
        self.connection.commit()

    def close(self):
        self.connection.close()

    def documents(self, full=False):
        fields = "*" if full else "id,title,digest,origin,created_at,length(text) AS characters"
        return [
            dict(r)
            for r in self.connection.execute("SELECT " + fields + " FROM documents ORDER BY rowid DESC")
        ]

    def add_document(self, title, text, origin="user_notes"):
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 150:
            raise ValueError("A title of 1–150 characters is required")
        if not isinstance(text, str) or not 20 <= len(text) <= 30000 or not text.strip():
            raise ValueError("Use 20–30,000 characters of plain text")
        digest = hashlib.sha256(text.encode()).hexdigest()
        existing = self.connection.execute("SELECT id FROM documents WHERE digest=?", (digest,)).fetchone()
        if existing:
            return {"id": existing[0], "duplicate": True}
        if len(self.documents()) >= 20:
            raise ValueError("This local workspace supports up to 20 documents")
        doc_id = str(uuid4())
        self.connection.execute(
            "INSERT INTO documents VALUES(?,?,?,?,?,?)",
            (doc_id, title.strip(), text, digest, origin, stamp()),
        )
        self.connection.commit()
        return {"id": doc_id, "duplicate": False}

    def delete_document(self, doc_id):
        changed = self.connection.execute("DELETE FROM documents WHERE id=?", (doc_id,)).rowcount
        for row in self.connection.execute("SELECT id,payload FROM study_plans").fetchall():
            payload = json.loads(row["payload"])
            for task in payload["tasks"]:
                if task["citation"]["document_id"] == doc_id:
                    task["citation"]["quote"] = ""
                    task["source_available"] = False
            self.connection.execute(
                "UPDATE study_plans SET payload=? WHERE id=?", (json.dumps(payload), row["id"])
            )
        self.connection.commit()
        return bool(changed)

    def ask(self, question, limit=3):
        if not isinstance(question, str) or not 3 <= len(question.strip()) <= 1000:
            raise ValueError("Ask a question of 3–1000 characters")
        rows = []
        for document in self.documents(full=True):
            for start, end, text in chunks(document["text"]):
                rows.append(
                    {
                        "document_id": document["id"],
                        "title": document["title"],
                        "digest": document["digest"],
                        "start": start,
                        "end": end,
                        "quote": text,
                        "origin": document["origin"],
                    }
                )
        trace = [
            {"tool": "documents.read", "result_count": len(self.documents())},
            {"tool": "citations.slice", "result_count": len(rows)},
        ]
        if not rows:
            return {
                "question": question,
                "status": "no_sources",
                "citations": [],
                "trace": trace,
                "notice": "Add notes first. No answer or citation was invented.",
            }
        vectorizer = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(2, 5), max_features=30000, sublinear_tf=True
        )
        try:
            matrix = vectorizer.fit_transform([r["quote"] for r in rows])
            scores = cosine_similarity(vectorizer.transform([question]), matrix)[0]
        except ValueError:
            scores = [0.0] * len(rows)
        ranked = sorted(
            zip(scores, rows), key=lambda pair: (-pair[0], pair[1]["document_id"], pair[1]["start"])
        )
        evidence = []
        for score, row in ranked:
            if score < 0.16 or len(evidence) >= limit:
                continue
            # Avoid showing three overlapping slices of the same paragraph as independent support.
            if any(
                e["document_id"] == row["document_id"] and abs(e["start"] - row["start"]) < 600
                for e in evidence
            ):
                continue
            evidence.append({**row, "relevance": round(float(score), 4)})
        trace.append({"tool": "tfidf.retrieve", "result_count": len(evidence)})
        return {
            "question": question,
            "status": "evidence_found" if evidence else "insufficient_evidence",
            "citations": evidence,
            "trace": trace,
            "model": "scikit-learn TF-IDF character n-grams + cosine similarity",
            "notice": "Exact excerpts from your notes. Relevance measures text overlap, not factual truth or answer confidence. This app does not generate an LLM answer.",
        }

    def create_plan(self, question, minutes):
        if type(minutes) is not int or not 10 <= minutes <= 120:
            raise ValueError("Choose 10–120 minutes")
        result = self.ask(question)
        if not result["citations"]:
            raise ValueError("Not enough matching evidence to create a sourced plan")
        count = min(len(result["citations"]), minutes // 10)
        allocation = minutes // count
        tasks = []
        for citation in result["citations"][:count]:
            tasks.append(
                {
                    "id": str(uuid4()),
                    "title": "Read, recall and verify: " + citation["title"],
                    "minutes": allocation,
                    "allocation_kind": "user_budget_allocation_not_learning_outcome",
                    "citation": citation,
                    "state": "pending",
                    "rating": None,
                    "next_review_at": None,
                }
            )
        plan = {
            "id": str(uuid4()),
            "question": question,
            "minutes_available": minutes,
            "total_minutes": allocation * count,
            "tasks": tasks,
            "created_at": stamp(),
            "trace": [*result["trace"], {"tool": "time.allocate", "result_count": count}],
            "notice": "Time and review intervals are simple planning choices, not validated predictions of mastery. No work is submitted or shared.",
        }
        self.connection.execute(
            "INSERT INTO study_plans VALUES(?,?,?)", (plan["id"], json.dumps(plan), plan["created_at"])
        )
        self.connection.execute(
            "DELETE FROM study_plans WHERE rowid NOT IN (SELECT rowid FROM study_plans ORDER BY rowid DESC LIMIT 30)"
        )
        self.connection.commit()
        return self.get_plan(plan["id"])

    def get_plan(self, pid):
        row = self.connection.execute("SELECT payload FROM study_plans WHERE id=?", (pid,)).fetchone()
        if not row:
            raise KeyError("Plan not found")
        plan = json.loads(row[0])
        current = {d["id"]: d["digest"] for d in self.documents()}
        for task in plan["tasks"]:
            task["source_available"] = (
                current.get(task["citation"]["document_id"]) == task["citation"]["digest"]
            )
        return plan

    def plans(self):
        return [
            self.get_plan(row[0])
            for row in self.connection.execute("SELECT id FROM study_plans ORDER BY rowid DESC LIMIT 30")
        ]

    def review(self, pid, tid, rating):
        if rating not in ("needs_practice", "recalled"):
            raise ValueError("Choose needs_practice or recalled")
        plan = self.get_plan(pid)
        task = next((t for t in plan["tasks"] if t["id"] == tid), None)
        if not task:
            raise KeyError("Task not found")
        if not task["source_available"]:
            raise ValueError(
                "The source was removed. Add verified source material before reviewing this task."
            )
        if task["rating"] == rating:
            return plan
        task["state"], task["rating"] = "reviewed", rating
        days = 1 if rating == "needs_practice" else 3
        task["next_review_at"] = (datetime.now(UTC) + timedelta(days=days)).isoformat()
        self.connection.execute("UPDATE study_plans SET payload=? WHERE id=?", (json.dumps(plan), pid))
        self.connection.execute(
            "INSERT INTO review_events(plan_id,task_id,rating,at) VALUES(?,?,?,?)",
            (pid, tid, rating, stamp()),
        )
        self.connection.commit()
        return self.get_plan(pid)

    def stats(self):
        return {
            "documents": len(self.documents()),
            "plans": len(self.plans()),
            "review_events": self.connection.execute("SELECT count(*) FROM review_events").fetchone()[0],
            "mode": "local_only",
            "external_requests": 0,
        }
