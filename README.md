# StudyTrace

Turn your own notes into a short, sourced study session. Local retrieval, exact quotations, a visible tool trace, persistent review feedback, and JSON export. No API key or model service is needed.

This is a working local prototype developed on 2026-10-27 as a proposed LaunchPad Hacks entry. The participant completed registration and approved publishing the source under the MIT license. A project description and synthetic demo screenshots are saved on Devpost. Formal submission remains pending participant confirmation; no award is claimed.

## Run

Python 3.13 was tested on macOS arm64. Install once with internet access; the application then runs locally without outbound calls or downloaded models.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8766 --no-access-log
```

Open http://127.0.0.1:8766. Load the clearly labeled synthetic demo notes or paste notes you have permission to use. Ask about binary search, inspect the original excerpt and its checksum, choose a time budget, create a plan, record a review, reload the session and export it.

The SQLite database is `local-data/studytrace.db`; set `ST_DB_PATH` to choose a different local file. Nothing from `local-data/` belongs in a source archive. This is a single-user local app without public hosting authentication; bind to loopback. No server purchase is needed for this local build. A public deployment would require separate access control, storage isolation and user approval.

## What actually runs

- FastAPI validates bounded plain-text notes and questions. SQLite persists documents, the latest 30 study plans and review events.
- scikit-learn character n-gram TF-IDF and cosine similarity rank exact 600-character slices, with an overlap of 80 characters. At most 3 non-overlapping matches above a fixed 0.16 text-similarity threshold are shown.
- A fixed workflow reads notes, retrieves evidence and allocates the user's time to reading/recall tasks. This is deterministic tool orchestration, not an autonomous LLM agent. It does not write a model-generated answer, assess source truth or predict mastery.
- Citations contain the original document ID, SHA-256, character offsets and original excerpt. Relevance is textual overlap, not confidence. Chinese and English retrieval cases are tested; semantic accuracy is not benchmarked.
- No sources or inadequate overlap produces an explicit abstention. Review feedback suggests 1 day for “needs practice” or 3 days for “recalled”; these are planning choices, not validated learning recommendations.
- Removing a document deletes its stored text and clears its quotations from saved plans. IDs, titles, checksums and review history remain as historical metadata. Existing user-downloaded exports and backups cannot be revoked; SQLite deletion is not a secure-erasure guarantee.

Limits: 20 documents, 30,000 characters each, 160,000-byte write requests, 10–120-minute plans. No OCR, PDF parsing, generative explanations, accounts, cloud sync, remote URL fetching or sponsor API. The small demo notes are synthetic examples, not user course materials or benchmark results.

## Test

```sh
.venv/bin/python -B -m unittest discover -s tests -v
```

Tests cover citation offsets, unrelated-query abstention, Chinese notes, persistence, deduplication, time limits, idempotent reviews, deleted-source redaction, bounded history, Host/Origin protection, input limits, fixed asset paths and private error handling. Browser tests live in the parent PrizeHunter project's `frontend/e2e/studytrace.spec.ts`.

The parent runner can copy actual sources from this conversation into an isolated workspace, execute the tests with network disabled, and create a SHA-256 manifest and source ZIP. This does not claim the standalone Codex CLI generated this project.

## Entry materials

Read `SUBMISSION.md`, `DEMO_SCRIPT.md`, `AI_DISCLOSURE.md`, `RULE_REVIEW.md` and `REVIEW_REQUIRED.md` before final submission. `LICENSE` contains the participant-approved MIT license for this project's source. `THIRD_PARTY.md` records reused dependencies, whose licenses remain their owners' licenses. No user notes, private database, credentials or installed dependencies are included.
