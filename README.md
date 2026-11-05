# Customer Intelligence & Recommendation Platform

A runnable research application for **A Graph-Augmented Agentic AI Framework for Customer Segmentation and Cross-Selling Recommendation**. Python 3.12 / FastAPI, Next.js / React / TypeScript, SQLAlchemy, PyTorch Geometric and LangGraph.

All included data and reported experiments are **synthetic**. This is a research deployment with production-style configuration, not a validated production decision system.

**Live application:** [cirp-platform.vercel.app](https://cirp-platform.vercel.app). Choose **Use demo account**, then sign in. The frontend and API are hosted on Vercel. See [deployment details](docs/VERCEL.md). Runtime report/log history is temporary; model training remains offline.

## Start locally

Run from this repository's root. Python 3.12 and Node 22+ are required.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python -m backend.pipeline --epochs 40 --regenerate
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open [dashboard](http://localhost:3000) and [interactive API documentation](http://localhost:8000/docs). The frontend defaults to `http://localhost:8000`; set `NEXT_PUBLIC_API_URL` in `frontend/.env.local` if you select another port. Public frontend environment variables are embedded at build time.

**This workspace's verified preview uses API port 8010** because port 8000 already belongs to another project. Its ignored `frontend/.env.local` points to `http://localhost:8010`. Start the API on 8010 to reuse that preview configuration.

Once dependencies and models exist, Windows users can start both services with `.\scripts\start.ps1`. The script opens no terminal windows, prints process IDs and writes logs in the project root. Custom ports are accepted with `-ApiPort` and `-DashboardPort`.

Dependencies downloaded for this Codex session live in ignored `.deps/`. To reuse them in PowerShell: `$env:PYTHONPATH=(Join-Path $PWD '.deps')`. A clean virtual environment using requirements is recommended for regular development.

The exact direct dependency versions exercised here are in `backend/constraints-tested.txt`. To reproduce them, install with `python -m pip install -r backend/requirements.txt -c backend/constraints-tested.txt`. Frontend versions are recorded in `frontend/pnpm-lock.yaml`.

## Sign in

The dashboard redirects signed-out visitors to `/login`. During local development, choose **Use demo account**, then **Sign in to your workspace**. Demo credentials are `analyst@cirp.local` / `CIRP-Demo-2026`. The demo is explicitly disabled in production.

Sessions use signed, expiring HttpOnly cookies; production cookies require HTTPS. Dashboard rendering and the same-origin analytics proxy both validate the session. Password checks run on the server. Sign out clears the browser session. Credentials never enter browser storage. This is a single-workspace account, not multi-user registration or password recovery. Failed sign-in attempts are limited in process; distributed deployments should use a managed identity provider and shared rate limiting.

For production, set `AUTH_EMAIL`, `AUTH_PASSWORD`, `AUTH_SECRET` (at least 32 random characters), `BACKEND_URL` and `BACKEND_API_KEY` on the frontend server. Set the same `BACKEND_API_KEY` on the backend: it rejects direct unauthenticated `/api/*` requests when configured. Production sign-in fails closed if credentials, session secret or the service key are absent. Local development keeps the trusted local backend accessible when no service key is configured.

Run the auth integration check against the running local app with `node frontend/scripts/test-auth.mjs`. It checks redirects, invalid credentials, protected data, cookie flags, forged sessions, cross-origin sign-in and sign-out.

## Docker

Copy `.env.example` to `.env` and populate `AUTH_EMAIL`, `AUTH_PASSWORD`, `AUTH_SECRET` and `BACKEND_API_KEY` before starting the production-mode containers. Use different random values for the session secret and service key. Compose passes the backend service URL internally; authentication secrets stay on the servers.

```sh
docker compose up --build
```

The trainer finishes before the API starts. Named volumes persist data, models and SQLite. The first image build downloads PyTorch and can be large. Default ports are 3000 and 8000; adjust host mappings and the frontend build argument together if occupied. Docker configuration has been supplied; container execution has not been verified in this environment.

## What works

- Seeded behavioral simulator: 1,000 customers, 120 products, 8,000 baskets and complementary basket items; consistent keys and repeat purchases.
- Validation, cleaning, date conversion, RFM, tenure, discount association, diversity, basket size, CLV proxy, log transforms and scaling.
- K-Means selection by silhouette across k=2…7 among purchasing customers; explicit no-purchase cohort; elbow diagnostics; Ward hierarchy and DBSCAN comparison; behavior-derived segment names. A Random Forest surrogate reports held-out assignment fidelity and global feature importance.
- Typed customer/product/category NetworkX graph, training-only purchase and co-purchase edges, nearest customer relationships, tensors and ID mapping.
- Actual two-layer GCN, GraphSAGE and GAT models trained with PyG, BCE link prediction, sampled negatives, Adam, early stopping and checkpoints.
- Hybrid ranking with collaborative, content, graph, co-purchase and segment signals; inspectable contributions and supporting historical products; configurable repeats.
- LangGraph supervisor, five tool agents and report generation; conditional routes, shared state, retries, execution logs, evidence validation and optional provider integration.
- Ten dashboard sections: overview, EDA, segmentation, graph, customer explorer, recommendations, agents, business intelligence, evaluation and reports.
- Paginated API, validation, 404/503 handling, CORS, SQLite persistence, PostgreSQL connection support, CSV/PDF export, OpenAPI documentation.
- MLflow experiment tracking in `backend/artifacts/mlflow.db`, dataset fingerprint, versioned model snapshots, metrics and charts.

## Research protocol

Transactions split at global date boundaries: earliest 70% of distinct days for training, next 15% validation, final 15% test. All baskets on a day stay together. Customer features, category preferences, popularity, associations, clustering and graph edges use the training window. The dashboard's overview/history use all dates and are labeled separately.

Graph link evaluation assigns a distinct customer-product pair to its earliest split, removing previously observed pairs from validation/test positives. Negatives exclude all known positives, including future positives; this is evaluation-label filtering, not training-graph enrichment. Classification uses balanced positive/negative samples, so AUC and accuracy do not describe real purchase prevalence. The cohort and catalog are transductive: customer/product identities and static catalog attributes are known across the study.

GNN selection uses **validation AUC**, never test AUC. Hybrid weights are fixed in code before evaluation. Recommendations use full-catalog top-5 ranking against novel test purchases, exclude training purchases and evaluate customers with at least one eligible held-out item. Cold customers receive segment/graph/popularity information where available. No random candidate subsampling inflates ranking metrics.

No claim is made that hybrid beats every baseline. See `backend/artifacts/metrics/recommendation_metrics.json` for complete comparisons. Scores are normalized ranking signals; confidence is a heuristic average, not a calibrated probability. CLV is a proxy, discount sensitivity is an association, and inactivity is not a trained churn forecast. SHAP is not applied to unsupported clustering or embedding models; explanations expose cluster statistics and exact scoring components.

## Commands and artifacts

```sh
python -m backend.scripts.generate_data
python -m backend.scripts.preprocess
python -m backend.scripts.run_eda
python -m backend.scripts.train_segmentation
python -m backend.scripts.build_graph
python -m backend.scripts.train_gnn --epochs 40
python -m backend.scripts.train_recommender
python -m backend.scripts.evaluate
python -m pytest backend/tests -q
```

Individual stages are for experimentation. Run `python -m backend.pipeline` to publish a consistent full set of artifacts, version snapshots, database rows and MLflow metadata. Restart the API after a command-line retrain because serving uses a cached immutable store. Training through the API is disabled by default; enable `ENABLE_TRAINING_API=true` only in a trusted maintenance session. Use one trainer at a time and stop serving during model replacement.

- `backend/data/`: raw and cleaned CSVs, temporal splits, customer/product features, provenance and feature definitions.
- `backend/artifacts/models/`: segmentation model, three GNN checkpoints, embeddings, recommender, assignments, recommendations and manifest.
- `backend/artifacts/graph/`: GraphML, node features, edge index and mapping.
- `backend/artifacts/eda/`: distributions, correlations, retail overview, dendrogram/elbow, RFM HTML, graph and learning curves, quality JSON and report.
- `backend/artifacts/metrics/`: clustering, link prediction and recommendation comparisons.
- `backend/artifacts/versions/<version>/`: immutable model/metric snapshots.
- `backend/artifacts/reports/`: exported CSV/PDF reports. PDF previews cap output at 200 rows and 8 columns; CSV is complete.

Generated datasets and artifacts are excluded from Git and reproduced by the pipeline. Model checkpoints and Joblib files must only be loaded from trusted sources.

## Optional LLM

Export `LLM_API_KEY`, `LLM_BASE_URL` and `LLM_MODEL` for an OpenAI-compatible chat provider. The deterministic system needs no credentials and remains functional on provider failure. Only computed evidence is supplied to the LLM. An LLM summary is advisory and should be checked against the evidence panel; numerical fidelity is guaranteed only by the deterministic template path. Avoid using sensitive customer data with an external provider without appropriate authorization.

## Deployment

Vercel: import the repository, set root directory `frontend`, use the Next.js preset, and set the server-only authentication variables listed above. Set `BACKEND_URL` to your HTTPS backend URL and copy the Render `BACKEND_API_KEY` into the matching Vercel variable. Browser analytics requests use the authenticated Next.js proxy.

Render: `render.yaml` supplies a Docker web service. Set `CORS_ORIGINS` to the exact frontend URL. The demo uses the SQLite database created in the image. For a separately provisioned PostgreSQL database, set `DATABASE_URL` to a SQLAlchemy URL such as `postgresql+psycopg://...` and run `python -c "from backend.app.database import initialize; initialize()"` once after supplying the model artifacts. The Render-specific Dockerfile trains a fixed synthetic demo during image build and serves its baked artifacts without startup training. The free-plan configuration uses ephemeral SQLite, so report records and agent logs reset on instance replacement. For persistent production operations, provision PostgreSQL and durable model storage and initialize the operational tables from the artifacts. Railway can build the same backend Dockerfile, with the same environment and volume requirements. GitHub Actions checks training/tests and frontend build.

The frontend and inference API have been deployed to Vercel and verified end-to-end. The public synthetic demo was explicitly selected; no GitHub integration or Render account was required. Vercel CLI authentication and linked project state are stored outside tracked source. No paid database or durable operational storage has been provisioned.

Before exposing real customer data, extend single-account sign-in with managed multi-user identity, role-based authorization, shared rate and request limits, TLS, managed secrets, migrations/backups, monitoring, access logging and a proper offline job queue. PostgreSQL and cloud deployment configuration have not been exercised here.

## References

- [PyTorch Geometric installation](https://pytorch-geometric.readthedocs.io/en/stable/notes/installation.html)
- [Next.js installation](https://nextjs.org/docs/app/getting-started/installation)
- [LangGraph graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail), a possible future real-data source. It is **not** used here; the supplied generator avoids network ingestion, personal data and licensing ambiguity in the default reproducible experiment.
