# Agent capabilities -- NemoClaw

Read by `agent-scope-check` before any agent slice opens a PR here.
Edit the YAML below; the script parses the first ```yaml block.

```yaml
allow:
  - src/**
  - nemoclaw/**
  - nemoclaw-blueprint/**
  - agents/**
  - schemas/**
  - scripts/**
  - bin/**
  - test/**
  - docs/**
  - ci/**
  - AGENTS.md
  - README.md

deny:
  - .env
  - .env.*
  - secrets/**
  - "**/credentials*"
  - "**/*.key"
  - "**/*.pem"
  - .github/CODEOWNERS
  - .github/workflows/base-image.yaml
  - .github/workflows/installer-hash-check.yaml
  - .github/workflows/legacy-path-guard.yaml
  - install.sh
  - Dockerfile.base
  - package.json
  - package-lock.json
  - pnpm-lock.yaml
  - commitlint.config.js
  - eslint.config.mjs
  - jsconfig.json

limits:
  max_files: 25
  max_loc: 800
  max_minutes: 30
```

## Notes

- `Dockerfile.base` and `install.sh` are denied because they are the
  upstream-NVIDIA-bound surface; downstream agent edits there cause
  fork drift that humans must reconcile.
- `package.json` / lockfiles are denied because dependency churn
  triggers `installer-hash-check` and `docker-pin-check` cascades.
- `.github/workflows/base-image.yaml`, `installer-hash-check.yaml`,
  `legacy-path-guard.yaml` are denied because they are the integrity
  gates -- agents cannot disable their own scope checks.
- `agents/` and `nemoclaw-blueprint/` are explicitly allow-listed
  because they are the agent-authored surface (blueprint + agent
  manifests).
