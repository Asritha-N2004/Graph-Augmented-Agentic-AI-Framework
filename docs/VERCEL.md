# Full Vercel deployment

Live frontend: https://cirp-platform.vercel.app

Live backend: https://cirp-api-umber.vercel.app

Production verified on 5 November 2026: demo login, authenticated overview, segmentation, recommendations, graph relationships, model metrics, agent execution and CSV/PDF exports all returned successful responses. Direct unauthenticated data access was rejected. Backend deployment: `dpl_8LMtrT1pu7nwVuPQSkdoHNQH3UPs`; frontend deployment: `dpl_Fg5v2qMzMdodZPkARm5tVRS33xtF`.

The application uses two projects in the authenticated Vercel account: `cirp-platform` for Next.js and `cirp-api` for FastAPI. This avoids depending on Vercel's private-beta multi-service mode. The browser talks to the authenticated Next.js proxy; the proxy attaches a private service key when calling the API.

The public synthetic-demo mode was explicitly requested. `PUBLIC_DEMO_LOGIN=true` displays the demo account shortcut. Production credentials remain server environment variables, and sessions still use the production-only random signing secret. Public demo credentials are `analyst@cirp.local` / `CIRP-Demo-2026`.

## Backend package

`python scripts/prepare_vercel_backend.py` creates `.deploy/backend` from the actual trained data, model artifacts, charts and a clean synthetic SQLite seed. It excludes local agent questions and generated report records. The bundle uses `backend/requirements-serving.txt`, which omits offline training libraries. Recommendation inference loads the already-trained five-signal model and learned GNN similarity data; it does not substitute a different model. GNN training remains an offline operation. `ENABLE_TRAINING_API=false` is enforced in the deployed environment.

Vercel exposes a read-only application bundle. On cold start, the backend copies its synthetic model/report artifacts and SQLite seed to an isolated temporary directory. Analytics and recommendations work across cold starts because the seed and trained models are bundled. Newly generated report records and agent execution logs are temporary and are not shared across instances. Durable operational history requires a separately provisioned database via `DATABASE_URL`; no such resource has been created.

## Secrets and routing

- Backend: `BACKEND_API_KEY`, `ENABLE_TRAINING_API=false`.
- Frontend: matching `BACKEND_API_KEY`, private `AUTH_SECRET`, `AUTH_EMAIL`, `AUTH_PASSWORD`, `PUBLIC_DEMO_LOGIN=true`, and `BACKEND_URL` pointing to the backend's production alias.
- API `/health` stays public. `/api/*` rejects requests without the service key. The service key is never sent to the browser.

`scripts/configure_vercel_demo.py` creates random secrets in memory and supplies values to the Vercel CLI through stdin. It configures both linked projects together; rerunning it rotates the service and session keys and requires redeploying both projects. Do not run it to refresh only one project.

## Updating

1. Train and evaluate locally when models change.
2. Rebuild the backend package and deploy `.deploy/backend` to the linked `cirp-api` project.
3. Deploy `frontend` to the linked `cirp-platform` project.
4. Check public health, rejected unauthenticated API access, demo sign-in, dashboard data, recommendations, agent execution and report downloads on the production aliases.

Do not upload `.deps`, training environments, local credentials, `.env*`, `.vercel` state or CLI tooling. The prepared backend directory and local CLI reside in the ignored `.deploy` workspace folder.

References: [Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python), [function limits](https://vercel.com/docs/functions/limitations).
