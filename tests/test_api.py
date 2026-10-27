import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from fastapi.testclient import TestClient

TEXT = "Binary search works on a sorted collection. It halves the search interval on each comparison."


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = create_app(Path(self.temp.name) / "local.db")
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def add(self):
        response = self.client.post("/api/documents", json={"title": "Searching", "text": TEXT})
        self.assertEqual(response.status_code, 201)
        return response.json()["id"]

    def plan(self):
        self.add()
        r = self.client.post("/api/plans", json={"question": "binary search sorted", "minutes": 25})
        self.assertEqual(r.status_code, 201)
        return r.json()

    def test_browser_assets_have_self_only_policy(self):
        for path in ("/", "/app.js", "/style.css"):
            r = self.client.get(path)
            self.assertEqual(r.status_code, 200)
            self.assertIn("default-src 'self'", r.headers["content-security-policy"])
            self.assertEqual(r.headers["cache-control"], "no-store")

    def test_full_evidence_plan_review_export_and_deletion_flow(self):
        p = self.plan()
        task = p["tasks"][0]
        r = self.client.post(f"/api/plans/{p['id']}/tasks/{task['id']}/review", json={"rating": "recalled"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["tasks"][0]["state"], "reviewed")
        export = self.client.get(f"/api/plans/{p['id']}/export")
        self.assertIn("attachment", export.headers["content-disposition"])
        self.assertEqual(export.json()["tasks"][0]["citation"]["quote"], TEXT)
        deleted = self.client.request("DELETE", "/api/documents/" + task["citation"]["document_id"], json={})
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(
            self.client.get(f"/api/plans/{p['id']}/export").json()["tasks"][0]["citation"]["quote"], ""
        )
        self.assertEqual(self.client.get("/api/stats").json()["external_requests"], 0)

    def test_no_matching_evidence_does_not_save_a_plan(self):
        self.add()
        r = self.client.post("/api/ask", json={"question": "天体物理学相对论"})
        self.assertEqual(r.json()["status"], "insufficient_evidence")
        r = self.client.post("/api/plans", json={"question": "天体物理学相对论", "minutes": 25})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.client.get("/api/plans").json(), [])

    def test_invalid_host_and_cross_origin_writes_rejected(self):
        self.assertEqual(self.client.get("/api/stats", headers={"Host": "attacker.example"}).status_code, 400)
        r = self.client.post(
            "/api/documents",
            json={"title": "X", "text": TEXT},
            headers={"Origin": "https://attacker.example"},
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.client.get("/api/documents").json(), [])

    def test_same_origin_write_works(self):
        r = self.client.post(
            "/api/documents", json={"title": "X", "text": TEXT}, headers={"Origin": "http://testserver"}
        )
        self.assertEqual(r.status_code, 201)

    def test_json_required_and_actual_body_bounded_without_length(self):
        self.assertEqual(self.client.post("/api/ask", content="question=hello").status_code, 415)
        r = self.client.post(
            "/api/documents",
            content=iter([b"x" * 80001, b"y" * 80001]),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(r.status_code, 413)

    def test_malformed_json_wrong_shapes_and_unknown_fields(self):
        for body in ("{", "[]", '{"question":"binary", "unknown":true}'):
            r = self.client.post("/api/ask", content=body, headers={"Content-Type": "application/json"})
            self.assertEqual(r.status_code, 422)
        r = self.client.post("/api/plans", json={"question": "binary", "minutes": True})
        self.assertEqual(r.status_code, 422)

    def test_fixed_asset_paths_ignore_path_query_and_traversal(self):
        script = self.client.get("/app.js?filename=../core.py").text
        self.assertIn("load-demo", script)
        self.assertNotIn("class Workspace", script)
        for path in ("/core.py", "/local-data/studytrace.db", "/%2e%2e/core.py", "/.env"):
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_missing_resource_and_invalid_review_are_explicit(self):
        self.assertEqual(self.client.get("/api/plans/missing").status_code, 404)
        p = self.plan()
        r = self.client.post(
            f"/api/plans/{p['id']}/tasks/{p['tasks'][0]['id']}/review", json={"rating": "mastered"}
        )
        self.assertEqual(r.status_code, 400)

    def test_unexpected_exception_does_not_expose_private_text(self):
        with patch("app.Workspace.stats", side_effect=RuntimeError("private marker")):
            r = self.client.get("/api/stats")
        self.assertEqual(r.status_code, 500)
        self.assertNotIn("private marker", r.text)


if __name__ == "__main__":
    unittest.main()
