# Deployment options

The current deployed application runs entirely on Vercel. See [the full Vercel deployment record](VERCEL.md) for production URLs, configuration and verification. The Vercel + Render instructions below remain an alternative architecture, not the selected live deployment.

The alternative architecture below uses a Vercel frontend and Render backend. No Render service has been created.

1. Publish this repository to GitHub, preferably private by default. Generated datasets, model artifacts, credentials, dependencies and local configuration are excluded from Git.
2. In Render, create a Blueprint from that repository using `render.yaml`. It selects `backend/Dockerfile.render`, a free research web service and `/health` as the health path. Set `CORS_ORIGINS` to the exact Vercel production origin when known.
3. The Render image installs CPU PyTorch, runs the full synthetic training pipeline during the image build and bakes its data, models and SQLite snapshot into the image. The running web process does not train. Verify `/health` returns `models_ready: true` and `/api/analytics/overview` returns measured data.
4. In Vercel, import the same repository and set the project root to `frontend`. `frontend/vercel.json` selects Next.js and the frozen pnpm install. Set server-only `BACKEND_URL` to the HTTPS Render service URL. Set `AUTH_EMAIL`, `AUTH_PASSWORD`, and a random `AUTH_SECRET` of at least 32 characters. Copy Render's generated `BACKEND_API_KEY` into the matching Vercel server environment variable. Never prefix secrets with `NEXT_PUBLIC_`. Production login remains disabled until these settings are present.
5. Copy the resulting Vercel origin into Render's `CORS_ORIGINS`, redeploy Render if needed, and verify overview, recommendations, graph, agent execution and exports from the live frontend. Add each permitted preview origin explicitly; do not use a broad wildcard for real data.

The free demo uses ephemeral SQLite. Reports and agent logs created at runtime reset when the instance is replaced. Fixed synthetic model artifacts survive because they are in the image. Free services can sleep; memory capacity and build resources must be verified during the first real deployment. No paid resources should be provisioned without an agreed budget.

For persistent production operation, provision PostgreSQL and durable artifacts, initialize the operational store against the configured database, and add authentication, authorization and operational controls. Docker, PostgreSQL and cloud execution remain unverified in this environment.

Provider references: [Render Blueprint specification](https://render.com/docs/blueprint-spec), [Render free service limits](https://render.com/docs/free), [Vercel monorepo root configuration](https://vercel.com/docs/monorepos).
