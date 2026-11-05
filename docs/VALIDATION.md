# Local verification record

Verified on Windows with Python 3.12 and Node 24. Direct Python versions are recorded in `backend/constraints-tested.txt`; frontend packages are locked by `frontend/pnpm-lock.yaml`.

- Full offline training completed for K-Means, hierarchical clustering, DBSCAN, Random Forest cluster surrogate, GCN, GraphSAGE, GAT and hybrid recommendations.
- 38 backend tests passed in the final regression run. They cover all required read endpoints, request validation, missing IDs, maintenance training restrictions, CSV export, agent routing/evidence, score accounting, purchased-item exclusion, temporal graph isolation, feature recomputation and cold-customer segmentation.
- Next.js production build passed with Webpack, including TypeScript, prerendering and build tracing. Turbopack initially failed because the sandbox blocked its CSS subprocess; the project explicitly uses Webpack.
- Browser checks confirmed live overview data, mobile navigation, five personalized recommendation cards, exact signal components, an executed agent workflow and rendered customer/product/category graph nodes.
- All four PDF types generated successfully: segmentation, recommendations, business and evaluation. Representative segmentation and recommendation pages were rendered and visually checked after correcting an encoding defect. CSV exports retain full data; PDF previews intentionally cap rows/columns.
- MLflow created a SQLite tracking database and recorded the successful full training run, dataset fingerprint, model files and evaluation artifacts.
- PowerShell launcher parsed without syntax errors.

The local dashboard connected to port 8010 because port 8000 belongs to an unrelated application; that application was left running. Temporary QA servers are stopped at handoff. Use `scripts/start.ps1` to restart CIRP.

Docker/Compose execution, PostgreSQL connectivity, authenticated LLM rewriting, GitHub Actions execution and cloud publishing have not been tested here. No Docker executable or configured hosting credentials were available. The API is for a trusted research workspace and needs access controls before real-customer deployment.

Measured comparisons and protocol limitations are regenerated from actual artifacts into `backend/artifacts/reports/experiment-report.md` by the full pipeline.

Login update: production frontend build passed with dynamic login/logout and authenticated API proxy routes. The saved Node auth smoke test passed for dashboard redirects, invalid credentials, HttpOnly signed sessions, authenticated analytics, forged-token rejection, origin validation and sign-out. Browser sign-in/sign-out was verified, and the login page remains open in the interface.

Full Vercel deployment verified on 5 November 2026. Frontend: https://cirp-platform.vercel.app ; backend: https://cirp-api-umber.vercel.app . Production smoke checks passed for sign-in, authenticated analytics, segmentation, recommendations, graph relationships, model metrics, deterministic agents and CSV/PDF exports. The portable NPZ/JSON serving model matched original recommendations across 20 customers with both repeat modes and ran without PyArrow, PyTorch, SciPy or scikit-learn. Operational report/log history is temporary; training remains offline.
