---
starter_id: fastapi
package_manager: uv
project_name: 10x-dev-tracker
hints:
  language_family: python
  team_size: solo
  deployment_target: self-host
  ci_provider: github-actions
  ci_default_flow: auto-deploy-on-merge
  bootstrapper_confidence: first-class
  path_taken: custom
  quality_override: false
  self_check_answers: null
  has_auth: false
  has_payments: false
  has_realtime: false
  has_ai: false
  has_background_jobs: false
---

## Why this stack

Solo developer building a read-only dashboard to aggregate 10xDEV project status in Python. You chose FastAPI over the recommended Django because you want a lightweight async API backend without batteries-included admin UI. FastAPI is type-safe, async-first, and scaffolds quickly. Deployment is local-only (self-host) for now; you'll add a separate JS/TS frontend later and have FastAPI serve the static files. CI/CD is deferred — you can wire up GitHub Actions once the core MVP is working locally.
