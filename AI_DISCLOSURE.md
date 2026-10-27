# AI assistance and prior work

StudyTrace was designed, coded, tested and documented with substantial assistance from the current Codex conversation on 2026-10-27. The participant must review and take responsibility for the final work; this draft does not assert they manually authored all of it.

AI assistance produced application code, synthetic demo notes, tests, UI copy and draft submission materials. Tests were executed locally; passing tests do not independently prove originality, legal eligibility or usefulness to learners.

Reused components: Python/SQLite, FastAPI/Starlette/Pydantic, uvicorn, scikit-learn/NumPy/SciPy and httpx test tooling. The parent PrizeHunter project already contained the isolated test runner, persistent development jobs, evidence storage and ZIP packaging. Those are infrastructure, not new StudyTrace innovations. No external model API is used by the application at runtime.

The offline retrieval-and-planning application, its interface, exact citation handling, review workflow and tests were newly assembled in this session. Any later additions, reuse in another competition or manual contributions must be reflected in this disclosure before submission.
