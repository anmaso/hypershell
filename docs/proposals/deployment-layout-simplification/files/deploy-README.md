# deploy/ - Kubernetes manifests for the HyperShell platform

Everything under this directory is Kustomize; the lifecycle scripts in
`scripts/cluster/` apply it and add a few runtime-only pieces listed under
"Things that are easy to get wrong". Read this file first; each subdirectory
has a one-line purpose below, and the layout is the same for every target
environment.

```text
deploy/
  base/           environment-neutral manifests; never applied directly
  overlays/       one directory per environment this repo deploys itself
  gitops/         the packages hypershell-gitops consumes (external contract)
  addons/         optional Kustomize Components an overlay can switch on
  prerequisites/  cluster-scoped things that must exist before any overlay
  standalone/     manifests that are not part of any overlay
```

## Which directory do I want?

| I want to ... | Use | How it is applied |
| --- | --- | --- |
| Run the platform on a local Kind cluster | `overlays/kind` | `make kind-up` (scripts/cluster, kind driver) |
| Run the platform on an OpenShift dev or PR cluster | `overlays/openshift` | `make openshift-up` (scripts/cluster, openshift driver) |
| Run the platform on IBM Cloud ROKS | `overlays/ibm` | `skills/deploy/ibm-cluster` |
| Deploy only Keycloak first (stage 1 of a manual OpenShift install) | `overlays/openshift/keycloak` | `skills/deploy/deploy-cluster` |
| Point an Argo CD instance at the platform | `gitops/platform` + `gitops/applications` (or `gitops/hub` for one combined instance) | hypershell-gitops, see [gitops/README.md](gitops/README.md) |
| Add an optional capability to an environment | `addons/<name>` via `components:` | the environment overlay, usually in hypershell-gitops |
| Install CRDs, operators or the shared Gateway before the platform | `prerequisites/<env>` | Kind: `up.sh` applies it; OpenShift: cluster admin, see [prerequisites/README.md](prerequisites/README.md) |
| Change the PR-environment reaper | `standalone/pr-env-reaper` | reference copy, synced by hand into hypershell-gitops |

## How the layers compose

```text
base/platform      namespace, controller, controller RBAC, network policies,
                   prometheus, certificates
base/applications  api-server, web-console
base/keycloak      Keycloak deployment + realm renderer + theme
base/postgres.yaml bundled PostgreSQL (OpenShift dev only; not in base/kustomization.yaml)

base  = base/platform + base/applications                       (no Keycloak, no DB)

overlays/kind      = base + overlays/kind/keycloak + Gateway, HTTPRoutes, certs, OIDC secrets
overlays/openshift = base + base/keycloak + base/postgres.yaml + Routes, SCC, network policies
overlays/ibm       = overlays/openshift + Route ingress mode + internal-registry tenant gateway images

gitops/platform     = base/platform + SCC            (Platform Argo CD)
gitops/applications = base/applications + API Route  (Application Argo CD)
gitops/hub          = gitops/platform + gitops/applications (single combined Argo CD)
```

Rules that hold everywhere:

- A directory is either a **Kustomization** (something you can `kustomize build`)
  or a **Component** (`kind: Component`, included through `components:`). All
  reusable Components live in `addons/`. The two Components that only make sense
  for Kind (`overlays/kind/database-external`, `overlays/kind/grpc-tls`) live
  next to the overlay that uses them.
- `overlays/*` and `standalone/*` need
  `kustomize build --load-restrictor=LoadRestrictionsNone` because they reference
  files above their own directory (`base/postgres.yaml`, `scripts/ci/*.sh`). The
  `gitops/*` packages build with default load restrictions.
- `base/` must stay environment-neutral. Hostnames, domains, cluster names,
  provider flags and image overrides belong in an overlay patch.
- Every YAML under `base/` must be reachable from some kustomization;
  `scripts/check_deploy_orphans.py` (part of `make check`) enforces it.
  `scripts/test_gitops_manifests.py` proves the gitops split still renders the
  same resources as `gitops/hub`.

## Things that are easy to get wrong

**Keycloak** is defined once, in `base/keycloak`. `overlays/kind` includes it
through its `keycloak/` sub-overlay (which sets the Kind hostname).
`overlays/openshift` includes `base/keycloak` directly together with its own
Route and NetworkPolicy; the sibling `overlays/openshift/keycloak` is the
stage-1 "Keycloak only" render for a manual install and is not part of the full
overlay. The `gitops/*` packages never include Keycloak; production uses an
externally managed instance.

**PostgreSQL** comes from three different places depending on the environment:
`base/postgres.yaml` is included only by `overlays/openshift`; Kind gets a
stand-in TLS server created by `scripts/cluster/kind/up.sh` plus the
`overlays/kind/database-external` Component; production uses an external
database configured in hypershell-gitops.

**Images.** HyperShell's own images (`controller`, `api-server`, `web-console`)
are `:latest` placeholders in `base/` and pinned by digest in hypershell-gitops.
Tenant gateway images are controller environment variables in
`base/platform/controller.yaml`, kept in step with `OPENSHELL_VERSION` by
`scripts/sync_openshell_version.py`; `overlays/ibm` overrides them to the
cluster-internal registry.

**Runtime-generated overlays.** `scripts/cluster/kind/up.sh` writes temporary
kustomizations (`deploy/.local-images`, `deploy/.db-overlay`) that wrap
`overlays/kind` with local image tags and the database Component. The script
deletes them after the apply; never commit them.

## Not in this directory

- `charts/openshell/` is the vendored upstream OpenShell Helm chart that the
  control plane bakes into its image and renders per tenant gateway. It is not
  part of deploying the platform.
- `pipelines/release-bundle/` packages `gitops/hub`, `base/keycloak/theme` and
  `addons/openshift-dashboard-metrics` into the release bundle.
- `scripts/cluster/` holds the lifecycle scripts (`up`, `down`, `seed`, `swap`)
  that apply these manifests; see [scripts/cluster/README.md](../scripts/cluster/README.md).

## External path contracts

hypershell-gitops references these directories by URL at a pinned commit SHA:
`gitops/platform`, `gitops/applications`, `gitops/hub`,
`addons/openshift-dashboard-metrics`, `base/keycloak/theme`. Renaming any of them
is a coordinated change with that repository.
