# Releasing

Releases are automated. This doc is the one-time setup a maintainer needs to do before the automation can run, plus what to expect day to day.

## One-time setup

1. **PyPI Trusted Publisher.** On [pypi.org](https://pypi.org), under the `agent-activity-ledger` project's *Publishing* settings, add a trusted publisher:
   - Owner: `ketriumlabs`
   - Repository: `agent-activity-ledger`
   - Workflow: `publish.yml`
   - Environment: `pypi`

   This lets `publish.yml` authenticate via OIDC — no PyPI API token is stored as a GitHub secret.

2. **GitHub environment.** Create a `pypi` environment in the repo's Settings → Environments. Optionally add required reviewers so a human confirms before a publish runs.

3. **GHCR.** No setup needed — `publish.yml` authenticates with the repo's own `GITHUB_TOKEN`, which already has `packages: write` for this repo.

## Day to day

- Merge PRs with [Conventional Commits](https://www.conventionalcommits.org/) messages (squash-merge normalizes this).
- `release-please` opens (and keeps up to date) a "chore: release X.Y.Z" PR on `main` summarizing what changed since the last release.
- Merging that PR tags the release and publishes a GitHub Release, which triggers `publish.yml`:
  - builds the sdist/wheel and publishes to PyPI (with a build-provenance attestation),
  - builds a multi-arch (amd64+arm64) Docker image and pushes it to `ghcr.io/ketriumlabs/agent-activity-ledger` tagged `latest`, `X.Y.Z`, and `X.Y`, with a build-provenance attestation and an SPDX SBOM.
- Nothing else to do — no manual version bumps, no manual `twine upload`, no manual `docker push`.
