# StudyTrace — draft project story

**Tagline:** A study session you can trace back to your own notes.

## Inspiration

Students often have limited time and a folder of scattered notes. An answer without a source can be hard to check, while a list of search results does not help decide what to review next. StudyTrace connects a question, its original evidence and a manageable study session in one local workspace. This is a proposed problem to explore; no user study or measured learning improvement is claimed.

## What it does

Paste permitted plain-text notes, ask a question and inspect exact excerpts with source offsets and checksums. If no adequate match exists, the app says so. Choose a time budget to create sourced reading-and-recall tasks, record what needs practice and resume the saved session later. Export the plan locally. Delete a source to remove its stored text and saved quotations.

## How we built it

FastAPI and SQLite provide a small persistent backend; scikit-learn TF-IDF and cosine similarity provide local text retrieval. A deterministic workflow coordinates retrieval, bounded time allocation and review feedback. The frontend uses plain HTML, CSS and JavaScript with no external assets or model calls. This is a retrieval-and-planning tool, not a generative tutor or autonomous LLM agent.

## Challenges and choices

Citation offsets must survive multilingual text and chunking. Saved plans must not retain quotations after the source is deleted. Review retries must not double-count feedback, and time allocation must respect the student's budget. Tests exercise these behaviors alongside browser-facing input and local-access protections.

## What is new

The application source, tests, synthetic example notes, interface and draft materials were created in the current Codex conversation on 2026-10-27, within the published LaunchPad build window. FastAPI, SQLite, scikit-learn, Python, browser tooling and the parent PrizeHunter verification/packaging infrastructure predate this project and are credited. No competitor submission was used as source material. AI assistance contributed substantially; see `AI_DISCLOSURE.md`.

## Limitations and next steps

Text similarity can miss paraphrases or surface irrelevant passages; the threshold is a prototype heuristic. A match does not prove a fact. Review intervals and time allocation are not learning-outcome predictions. There is no PDF import, account system or multi-user deployment. Next steps would be user testing, retrieval evaluation on permission-cleared notes and accessible document import before considering an optional generative model.

## Entry materials and review status

- Demo: downloadable Python source runs locally using the README; no hosted multi-user service.
- Source: participant-approved public release under MIT; consult the repository containing this file.
- Project description and screenshots: https://devpost.com/software/studytrace . Synthetic demo materials have been saved to the project.
- Video: a recording script is prepared; no video recorded or uploaded.
- Team identity: entered only by the participant during approved registration.

The participant registered and approved publication of these materials and the source. The contest submission remains a draft awaiting separate final confirmation. Published materials do not establish eligibility or guarantee an award.
