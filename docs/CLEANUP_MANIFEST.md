# Repository cleanup manifest

Current simplification audit: September 11, 2026. This section supersedes the historical counts below. No commit or push was made. The earlier uncommitted runtime reliability changes were preserved.

## 1–3. Original architecture, problems and duplication

The original runtime already used a compact FastAPI entry point, SQLAlchemy/SQLite persistence, one provider module, event intelligence, RF training/inference, security, and a single Next.js workspace. There were no duplicate FIRMS parsers, clustering implementations, training pipelines or competing copilot services worth merging. Main owns orchestration and transaction boundaries; splitting it further would add coupling during a reliability-sensitive cleanup.

Found: one obsolete shell copy, one fragmented 16-line review guard, overlapping data documentation, stale README setup/status claims, and generated duplicate frontend dependency/type directories. Additional copied frontend test/config files appeared during the audit; their creator is unknown. No package dependencies were removed: all declared packages serve runtime, geometry, build, typing or tests. Installed dependency directories were reconstructed from the unchanged frontend lockfile, not counted as source cleanup.

## 4–5. Merges and individually verified deletions

| Deleted file | Canonical destination / reason deletion was safe |
|---|---|
| `backend/app/review_validation.py` | Its complete source-reference syntax guard now lives in `backend/app/ml.py`, alongside eligibility checks. Updated the two direct external imports (review_common and acquisition tests); no route registered by the removed file. All 143 backend tests pass. |
| `docs/DATA.md` | Unique provenance, geometry, satellite, demo and review policy moved into `docs/ARCHITECTURE.md`; acquisition report references updated. Corrected satellite window and distinguished optional heuristic review assistance. |
| `review_next_5.shTAB` | Compared line by line with retained `review_next_5.sh`: only whitespace and an older loop-variable name differ. Identical five event/group pairs, no unique labels or evidence; no runtime/test/document reference. |
| `frontend/tests/api.test 2.mjs` (untracked copy appearing during audit) | Exactly matches retained `frontend/tests/api.test.mjs` after the intentional localhost-to-127.0.0.1 change. No unique test or reference. |
| `frontend/.env 2.example` (ignored copy appearing during audit) | Exactly matches retained `.env.example` after the same URL substitution; no secret or unique setting, no references. |

49 regenerable cache files removed from Python bytecode, pytest cache and `frontend/.next/cache`. The production build output remains because it serves the running application. `npm ci --ignore-scripts --offline` replaced generated node_modules, including duplicate `@types/* 2` directories. No database, WAL/SHM sidecar, dataset, review packet or model was deleted. The two incidental copies were absent from the original inventory, so are not counted as baseline source reduction.

## 6. Actual usage map and deliberate retention

| Files / family | Status and evidence |
|---|---|
| `backend/app/main.py` | USED: FastAPI app, auth/admin/event/model/review/analytics/copilot routes; imports provider, intelligence, persistence and ML functions; tested directly. |
| `backend/app/config.py`, `database.py`, `security.py` | USED: settings imported by app/providers/intelligence/security; ORM/session used by routes and review CLIs; password/JWT/authorization used by auth routes. |
| `backend/app/providers.py`, `intelligence.py`, `ml.py` | USED: one provider integration layer; clustering/features/risk; source eligibility, grouped RF training and inference. No parallel experimental classifier. |
| `backend/app/bootstrap.py` | USED: documented interactive real administrator creation CLI. |
| `backend/review_common.py` | USED: CSV validation, atomic replacement and review-field preservation imported by exporters, preparation and finalization. |
| `backend/export_review_candidates.py`, `validate_review_candidates.py`, `finalize_reviewed_labels.py`, `prepare_review_row.py` | USED: documented, test-covered canonical review workflow with distinct export/validate/publish/manual-edit responsibilities. |
| `backend/review_event_summary.py`, `review_progress.py`, `review_queue.py`, `candidate_inventory.py`, `export_review_packets.py`, `acquire_review_candidates.py` | USED: neutral evidence, progress, queue, inventory, packets, bounded acquisition; CLI and cross-import references. Similar output is not duplicate behavior: validation has different exit semantics from progress. |
| `backend/assisted_review.py` | PARTIALLY USED / optional manual helper: heuristic suggestions require two human confirmations. Retained rather than silently changing reviewer workflow; Pandas is not a declared dependency. Prefer canonical neutral evidence review. Suggestions do not establish truth. |
| `backend/batch_review_insert.py` | REVIEW PROVENANCE / optional one-off: contains 16 explicit event/class/group decisions and calls canonical preparation. Retained because deleting unique decision history is outside safe cleanup. Not run. |
| `backend/export_remaining_evidence.pyTAB` | OPTIONAL GENERATOR: produces retained remaining_review_evidence.txt through canonical prepare_review_row.py; not a duplicate of packet export format. Preserved with its evidence; requires undeclared Pandas. Not run. |
| `review_next_5.sh`, `review_until_ready.sh` | OPTIONAL HUMAN WORKFLOW: explicit input/confirmation wrappers around canonical review tools; first preserves five specific event/group mappings. Retained; machine-specific path and hardcoded reviewer make them unsuitable as general setup commands. |
| `backend/tests/test_system.py`, `test_candidate_acquisition.py`, `test_review_workflow.py`, `test_runtime_reliability.py` | USED: pytest regression suite covering runtime, auth, review/training, acquisition and transaction/provider reliability. |
| `frontend/app/page.tsx`, `layout.tsx`, `globals.css` | USED: single workspace, global layout and styles; login, evidence, status, map, alerts, copilot preserved. Strict unused-local/parameter TypeScript check passes. No proven dead CSS deleted based on static guessing. |
| `frontend/components/MapView.tsx`, `lib/api.ts` | USED: dynamically imported client-only map and centralized absolute URL/auth/error client; API tested independently. |
| `frontend/tests/api.test.mjs` | USED: 12 URL, auth, network/HTTP and timeout checks. |
| `frontend/next.config.ts`, `postcss.config.mjs`, `tsconfig.json`, `next-env.d.ts`, `package.json`, `package-lock.json` | USED / FRAMEWORK GENERATED: rewrites/build/style/types/npm dependency contract. Keep Next generated type declarations. |
| `backend/requirements.txt`, `.gitignore`, both `.env.example` files | USED: reproducible dependencies, ignored private/runtime artifacts and safe setup templates. |
| local `.env` / `.env.local`, `.venv`, `frontend/node_modules`, built `.next` | REQUIRED LOCAL OPERATION, ignored: credentials/config, active Python environment, JS dependencies and currently served production build. Deleting them would stop the working local app. |
| `data/review_candidates.csv`, `reviewed_labels.csv` | REVIEW / TRAINING REQUIRED: 33 eligible rows each. No edits; metadata authenticity still requires human verification. |
| `data/backups/*` (43 CSVs) | REVIEW HISTORY: retained, not treated as disposable duplicates; preserving intermediate review decisions is more valuable than reducing file count. No new backups created. |
| `data/review_packets/*`, `remaining_review_evidence.txt` | REVIEW EVIDENCE: stored evidence snapshots retained even where reproducible output may be stale. |
| `data/review_acquisition_plan.json`, `.example.json`, `review_acquisition_last_run.json` | CONFIG / PROVENANCE: bounded acquisition inputs, safe example and last-run trace. |
| `data/templates/reviewed_labels.csv`, `data/demo/detections.csv` | TEMPLATE / DEMO ONLY: training schema and explicitly separated fixture. |
| `models/classifier.joblib`, `metadata.json` | RUNTIME REQUIRED: existing model and metrics/version metadata, byte-for-byte preserved; no retraining. |
| root `thermaguard.db` and SQLite sidecars | RUNTIME REQUIRED: real and demo records coexist with mode filtering. Never deleted or relocated. |
| `README.md`, `docs/ARCHITECTURE.md`, `MODEL.md`, `REVIEW_ACQUISITION.md` | USED: setup/overview, architecture+data policy, training/review contract and acquisition workflow. |
| `docs/REVIEW_ACQUISITION_REPORT.md`, `RUNTIME_RELIABILITY.md`, this manifest | HISTORICAL / AUDIT: distinct acquisition provenance, measured reliability and cleanup decisions retained; historical counts are explicitly scoped. |
| `docs/workflow.png` | USED: preserved architecture visual referenced in architecture documentation. |
| `.freebuff/project-id` | UNKNOWN integration metadata: retained because its external consumer cannot be established from repository imports. |

## 7–8. Dependencies and final architecture

Removed dependencies: **0** (13 backend requirements, 7 frontend runtime + 7 development dependencies unchanged). Two retained optional Pandas helpers are not supported by those requirements; no new dependency was added merely to support one-off scripts.

Final runtime remains FastAPI → SQLite + provider/context + intelligence + ML + security; review syntax validation now belongs to ML. Frontend remains one workspace/map/API client. Clustering groups detections, Random Forest classifies, deterministic risk scores separately, Ollama explains only. No new folder, abstraction, training run or model version was created.

## 9–14. Validation and current real-mode smoke

- `./.venv/bin/python -m pip check`: no broken requirements.
- `./.venv/bin/python -m py_compile backend/app/*.py`: pass.
- `PYTHONPATH=backend ./.venv/bin/pytest backend/tests -q`: **143 passed**, two upstream Starlette/AnyIO deprecation warnings; passed both after merge and at final verification.
- `node --test frontend/tests/api.test.mjs`: **12 passed**.
- `npm --prefix frontend run typecheck`: pass after clean lockfile install.
- `npm --prefix frontend run build`: pass, Next.js 15.5.25 production build.
- Additional TypeScript `--noUnusedLocals --noUnusedParameters`: pass. No standalone lint script exists.
- Runtime malformed Markdown URL scan: zero occurrences. Authorization, 401 vs network failures, health URL and login URL regression tests pass.
- Real mode: `/health`, authenticated login, `/auth/me`, `/model/status`, `/events`, `/firms/status`, `/alerts`: **200**. Real event list: **33**, alert list: **0**.
- `POST /firms/sync`: **503, provider unavailable**, because current `FIRMS_MAP_KEY` is empty. Existing events remain readable. Current live sync success cannot be claimed; prior successful runs remain documented separately in RUNTIME_RELIABILITY.md.
- `POST /copilot/chat`: **200, mode=ollama**, nonempty answer, events unchanged after request. Installed `llama3.2:3b` served locally; no deterministic fallback mistaken for Ollama success.
- Frontend production server running at 127.0.0.1:3000, backend at 127.0.0.1:8000, Ollama at 127.0.0.1:11434.

## 15–17. Integrity and security

All **86 protected data/model files** have unchanged SHA-256 hashes. Database IDs unchanged: **131 detections / 37 events total**, including 10 fixture detections / 4 demo events; real API returns 33 events. SQLite integrity_check is `ok`. No review/source/group cell altered, no model bytes changed, no training run. This verifies preservation, not scientific label correctness.

Local `.env` had empty JWT/provider credentials at this audit. Generated a fresh cryptographically random JWT signing secret in the ignored local file without displaying it; existing JWTs require re-login. Set requested real-mode/Ollama options and plain frontend 127.0.0.1 URLs. Provider credentials remain empty and were requested from the user via local-file restoration, not chat. Both local frontend origins are allowed without wildcard CORS. Secret fields in examples remain empty, and local environment files remain git-ignored. Auth/scope logic and reliability protections were not weakened. No broad secret audit of historical Git objects is claimed.

## 18. Before / after (same inventory exclusions)

| Metric | Before | After |
|---|---:|---:|
| Meaningful files (includes retained operational data/config/DB sidecars) | 147 | 144 |
| Backend source files, excluding tests | 22 | 21 |
| Frontend source files, excluding tests | 7 | 7 |
| Test files | 5 | 5 |
| Documentation files, excluding generated evidence packets | 8 | 7 |
| Python/TS/TSX/MJS/CSS source lines, excluding next-env.d.ts | 12,646 | 12,644 |

One module merged; one document merged; one baseline duplicate script removed; two incidental copies removed; 49 cache files removed. Source-line reduction is deliberately small: preserving tested behavior and review history takes priority over cosmetic compression. Excludes `.git`, `.venv`, node_modules, `.next`, Python/pytest caches, __MACOSX, coverage, dist and build.

## 19–20. Review and remaining limitations

Tracked diff snapshot before inserting this stat into the report:

```text
 .gitignore                                  |   3 +
 README.md                                   |  51 ++-
 backend/.env.example                        |  11 +-
 backend/app/config.py                       |  21 +-
 backend/app/database.py                     |  29 +-
 backend/app/main.py                         | 657 +++++++++++-----------------
 backend/app/ml.py                           |  16 +-
 backend/app/providers.py                    | 252 +++--------
 backend/app/review_validation.py            |  16 -
 backend/review_common.py                    |   2 +-
 backend/tests/test_candidate_acquisition.py |   2 +-
 docs/ARCHITECTURE.md                        |  27 +-
 docs/CLEANUP_MANIFEST.md                    | 103 +++++
 docs/DATA.md                                |  22 -
 docs/REVIEW_ACQUISITION_REPORT.md           |   4 +-
 frontend/.env.example                       |   4 +-
 frontend/lib/api.ts                         |   8 +-
 frontend/tests/api.test.mjs                 |   8 +-
 review_next_5.shTAB                         | 107 -----
 19 files changed, 555 insertions(+), 788 deletions(-)
```


The final Git stat below includes earlier uncommitted reliability changes, so it must not be interpreted as this cleanup's isolated delta. Untracked reliability tests/report are also listed separately by git status. No commit or push.

Live FIRMS/Copernicus validation remains blocked by empty credentials. User was asked to restore them directly in backend/.env. Ollama works; SMTP is unconfigured. An empty alert list is not proof of real email delivery; isolated tests cover notification behavior. Single-process ingestion guard, O(n²) clustering, deferred-context scheduling and non-durable pending email remain documented limitations. Optional one-off review helpers remain due to provenance/workflow concerns, not as recommended training automation. Duplicate generated files appeared during work; investigate the external copy/sync process if they recur. No claims of production readiness or validated high model accuracy.


# Earlier cleanup audit (historical)

Audit date: September 11, 2026. Baseline verified immediately before cleanup:
**115 backend tests passed**, frontend typecheck passed, frontend production build
passed, `git status` clean (no untracked, unignored files), 33 review candidates,
1 reviewed/eligible row (`TG-firms-12a727a697efdb9146a2`), `training_ready=false`,
no model artifacts.

Nothing was deleted without a verified dependency check. Nothing classified
UNSURE was deleted.

## Deleted

| Path | Classification | Reason | Evidence | Regeneratable? |
|---|---|---|---|---|
| `data/backups/` (20 tracked files) | DUPLICATE / TEMPORARY | All 14 `review_candidates.*.csv` backups contain **zero human-review fields absent from the current file** (compared per-event; the single reviewed row's split_group/label/reviewer/source_reference are fully present in the current CSV). The 3 `reviewed_snapshot.*.json` files are byte-identical to each other (1 distinct content). `review_acquisition_pass2.json` is byte-identical to the retained `data/review_acquisition_last_run.json`. `pass1`/`sandbox_attempt` are intermediate acquisition-pass records already summarized (with request/row counts) in `docs/REVIEW_ACQUISITION_REPORT.md`; no workflow step reads the backups directory. | sha256 comparison + per-row human-field diff script run before deletion | Yes — scripts recreate the directory (`review_common.py`, `acquire_review_candidates.py`); new backups are written on every CSV replacement |
| `backend/thermaguard.db` (untracked) | GENERATED_REBUILDABLE | CWD-relative leftover from running the server inside `backend/`. Contains 4 demo events, 0 real events, 2 demo fixture users only. The live database is the repo-root `thermaguard.db` (33 real events, 131 detections). | sqlite table dumps compared before deletion | Yes — recreated on demo-mode boot |
| `backend/__pycache__/`, `backend/app/__pycache__/`, `backend/tests/__pycache__/` (incl. stray `* 2.pyc` duplicates) | CACHE | Python bytecode caches | Regenerated on every run | Yes |
| `.pytest_cache/` | CACHE | pytest cache | Regenerated on every test run | Yes |
| `frontend/.next/` | GENERATED_REBUILDABLE | Next.js build output | Regenerated by `npm run build` (verified during post-cleanup validation) | Yes |

## Moved

| From | To | Reason |
|---|---|---|
| `workFlow.png` (repo root) | `docs/workflow.png` | 1.5 MB architecture workflow diagram, referenced only by `docs/ARCHITECTURE.md` ("The supplied workflow image is preserved at the project root") — moved to keep the root minimal; reference updated in the same change |

## Kept (classification summary)

| Entry | Classification |
|---|---|
| `backend/app/` (incl. `review_validation.py`), `backend/tests/` (3 files, 115 tests) | REQUIRED_RUNTIME / REQUIRED_TEST |
| `backend/` review CLIs: `export_review_candidates.py`, `validate_review_candidates.py`, `finalize_reviewed_labels.py`, `review_event_summary.py`, `review_progress.py`, `prepare_review_row.py`, `acquire_review_candidates.py`, `export_review_packets.py`, `candidate_inventory.py`, `review_queue.py`, `review_common.py` | REQUIRED_RUNTIME (verified cross-imported and test-covered) |
| `data/review_candidates.csv` (33 rows, 1 reviewed) | REVIEW_REQUIRED — protected |
| `data/review_packets/` (33 packets + index) | REVIEW_REQUIRED — protected |
| `data/templates/reviewed_labels.csv` | REVIEW_REQUIRED — protected |
| `data/review_acquisition_plan.json` (+ `.example.json`) | REQUIRED_DATA — reproducibility manifest / config template |
| `data/review_acquisition_last_run.json` | REQUIRED_DATA — provenance record of the last acquisition |
| `data/demo/detections.csv` | DEMO_REQUIRED — offline demo fixture |
| `thermaguard.db` (repo root) | REQUIRED_DATA — live database with all 33 real events |
| `docs/` (ARCHITECTURE, DATA, MODEL, REVIEW_ACQUISITION, REVIEW_ACQUISITION_REPORT, workflow.png), `README.md`, `backend/.env.example` | REQUIRED_DOCUMENTATION |
| `frontend/` app/components/lib/config + `package.json`/`package-lock.json` | REQUIRED_RUNTIME / REQUIRED_DEVELOPMENT |
| `.gitignore`, `backend/requirements.txt` | REQUIRED_DEVELOPMENT |

## Secret audit

Tracked-file scan for map keys, client secrets, passwords, tokens and
authorization headers found **no committed secrets**: all matches are code
identifiers, empty `.env.example` placeholders, or the documented demo-fixture
credential (`admin@demo.thermaguard.local`), which only exists in local demo
databases. `backend/.env` is git-ignored (verified with `git check-ignore`).

## .gitignore hardening

Added: `*.py[cod]`, `.coverage`, `coverage.xml`, `htmlcov/`,
`playwright-report/`, `test-results/`, `*.egg-info/`. No real project data is
ignored; `*.db`/`models/` artifacts and `.env` remain ignored as before.

## Verification gates

Deletion proceeded only after the baseline gates above passed, and the full
gate set (115 tests, typecheck, build, review CLIs, candidate counts) was
re-run after deletion and recorded in the final cleanup report.

## Post-manifest note (same day)

While cleanup verification ran, a second human review was saved concurrently
through `review_next_5.sh` (`TG-firms-2e2dcb121765f0c09958` →
`industrial_fire`, reviewer `PRAGYAX_review`): `data/review_candidates.csv`
now holds **33 candidates / 2 reviewed / 2 eligible**, and the atomic-replace
backup mechanism created one new `data/backups/review_candidates.*.csv`
snapshot. All preserved review info is present in the current file. These
changes are the reviewer's work and were deliberately kept out of the
cleanup deletions.
