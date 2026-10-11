# Deployment layout simplification proposal

Status: proposal, evaluated, not applied. The complete change is reproduced by
the migration kit in [deployment-layout-simplification/](deployment-layout-simplification/):
run `python3 docs/proposals/deployment-layout-simplification/migrate.py` from
a clean checkout of `main`. It performs the moves, path rewrites and small
manual fixes, and installs the four README files shipped next to it. All
rendered manifests are byte-identical before and after.

## Recommendation

Reorganize `deploy/` from ten flat, inconsistently named directories into six
directories named by role, add a `deploy/README.md` that answers "which
directory do I want", and fold `scripts/kind/` under `scripts/cluster/` so the
driver pattern is visible from the tree. No manifest content changes.

Measured with fresh haiku and sonnet agents answering the same eleven
questions under the same tool budget: the current tree scored learnability 2
of 5 in five of six runs (one sonnet run gave 3); the proposed tree scored 4
in five of seven runs, 3 in one, and 2 in the one haiku run that never found
the new README. Accuracy was equal; what changed is how fast and how
confidently the layout is understood, and whether the entry point is found.
Details in "Evaluation".

## How the current layout reads to a newcomer

Four agents (two haiku, two sonnet) explored the current tree with a 25
tool-call budget. All four answered the questions correctly, because every
kustomization carries good header comments, and all four rated learnability
2 of 5 for the same reasons:

- **No map.** There is no `deploy/README.md`. The only layout document is
  `deploy/gitops/README.md`, which covers the GitOps split and nothing else.
  CLAUDE.md does not mention `deploy/` at all.
- **Names that mislead.** `deploy/gitops-base` is not a base, it holds one
  optional Component. `deploy/components` collides with the repository-root
  `components/` source tree, and other Components sit outside it
  (`deploy/kind/database-external`, `deploy/kind/grpc-tls`,
  `deploy/gitops-base/components/...`). `deploy/hub` is a two-line alias for
  the gitops packages. `deploy/e2e` is a production-style reaper CronJob that
  is deployed from another repository. `deploy/base/kustomization.yaml`
  describes itself as a "compatibility composition".
- **Keycloak in five places.** `base/keycloak`, `kind/keycloak`,
  `deploy/keycloak`, `deploy/kind` (includes and patches) and
  `deploy/openshift` (includes directly). Both control runs could not say which
  one to use for a manual OpenShift install.
- **Prerequisites hidden inside overlays.** `deploy/kind/infrastructure` and
  `deploy/openshift/infrastructure` share a name but mean different things
  (operator bundles versus a hand-applied Gateway), and the OpenShift setup
  guide is buried three levels down.
- **Two script trees.** `scripts/cluster` (driver facade) and `scripts/kind`
  (Kind implementation) sit side by side; the `exec` chain behind
  `make kind-up` is documented nowhere.
- **Things that look deployable but are not.** `charts/openshell` has a
  `Chart.yaml` but is the vendored tenant gateway chart baked into the
  control-plane image.

## Proposed layout

```text
deploy/
  README.md          the map: role of each directory, "which do I want" table,
                     composition diagram, pitfalls, external path contracts
  base/              unchanged content; platform-resources/ renamed platform/
  overlays/          kind/  openshift/  ibm/        (were deploy/{kind,openshift,ibm})
    openshift/keycloak/                            (was deploy/keycloak)
  gitops/            platform/  applications/  hub/ (hub was deploy/hub)
  addons/            gateway-database-admin-secret/ (was deploy/components/...)
                     openshift-dashboard-metrics/   (was deploy/gitops-base/components/...)
  prerequisites/     README.md
                     kind/      (was deploy/kind/infrastructure + kind-config.yaml + coredns/)
                     openshift/ (was deploy/openshift/infrastructure, incl. GATEWAY-SETUP.md)
  standalone/        pr-env-reaper/ (was deploy/e2e/reaper) + README.md

scripts/cluster/
  README.md          the driver chain behind make kind-* and make openshift-*
  kind/              (was scripts/kind)
  drivers/           unchanged
```

Design rules the layout now states and follows:

- Top level is six nouns, each a role: base, overlays, gitops, addons,
  prerequisites, standalone. Nothing at the top level is an alias of
  something else.
- A directory is either a Kustomization or a Component. Reusable Components
  live in `addons/`; the two Kind-only Components stay next to the overlay
  that uses them and the README says so.
- Every environment has the same shape: `overlays/<env>` plus an optional
  `overlays/<env>/keycloak` stage-1 sub-overlay, plus `prerequisites/<env>`.
- `gitops/` holds exactly what hypershell-gitops consumes by URL, and the
  README lists those paths as an external contract.

What the proposal deliberately does not do: it does not merge the two
Keycloak compositions inside `overlays/openshift`, does not move
`base/postgres.yaml` into a kustomization, and does not touch manifest content.
Those are behavior changes and are listed under "Follow-ups".

## Evaluation

Method: identical briefs to fresh `general-purpose` agents, 25 tool-call
budget, no git history, answers graded against a ground-truth sheet. Round 1
used questions that named the current paths. Round 2 and 3 used concept-based
questions (for example "where is the Component that supplies the controller's
gateway-database admin Secret") so that discoverability, not path-following,
was measured. Control runs saw the current tree with the round-2 questions.

| Round | Tree | Model | Tool calls | Calls to orient | Confidence | Learnability | First read |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | current | haiku | 11 | 5 | 4 | 2 | gitops/README.md (partial) |
| 1 | current | haiku | 10 | 5 | 3 | 2 | gitops/README.md (partial) |
| 1 | current | sonnet | 11 | 4 | 4 | 2 | gitops/README.md (partial) |
| 1 | current | sonnet | 15 | 5 | 4 | 2 | gitops/README.md (partial) |
| 2 control | current | haiku | 11 | 4 | 3 | 2 | gitops/README.md (partial) |
| 2 control | current | sonnet | 14 | 4 | 4 | 3 | none |
| 2 | proposed | haiku | 16 | 5 | 4 | 4 | deploy/README.md |
| 2 | proposed | haiku | 14 | 4 | 4 | 4 | deploy/README.md |
| 2 | proposed | sonnet | 14 | 5 | 4 | 4 | deploy/README.md |
| 2 | proposed | sonnet | 15 | 2 | 4 | 4 | deploy/README.md |
| 3 (after polish) | proposed | haiku | 25 | 11 | 3 | 2 | none (never opened deploy/README.md) |
| 4 (after breadcrumbs) | proposed | haiku | 12 | 4 | 4 | 3 | deploy/README.md |
| 3 (after polish) | proposed | sonnet | 9 | 2 | 4 | 4 | deploy/README.md |

Observations:

- Accuracy was high in every run, so the layout's problem is cost of
  understanding, not possibility of understanding. The differentiators were
  the self-reported confusion lists and the learnability score.
- The one question with an accuracy difference was "which kustomization do I
  use to deploy Keycloak by hand on OpenShift". All four proposed-tree runs
  answered it correctly and without hedging; both control runs hedged or said
  unsure.
- Haiku benefited as much as sonnet. On the current tree haiku rated 2 in all
  three runs; on the proposed tree it rated 4 in all three runs.
- Round-2 confusion lists on the proposed tree were dominated by stale
  comments the mechanical rewrite had missed (relative paths such as
  `../platform-resources` and `../components/...`) and by pre-existing
  behaviors (see "Follow-ups"). Round 3 ran after fixing the stale comments;
  the sonnet run then needed 9 tool calls instead of 14 to 15.
- The round-3 haiku run is the important negative result: it never opened
  `deploy/README.md`. Its first broad grep overflowed, it then followed the
  root README's only deployment link to `deploy/gitops/README.md` (the partial
  document), and it spent the entire budget reconstructing the layout from
  comments, scoring 2, the same as the current tree. A map only helps if the
  places people land point at it. Round 4 added breadcrumbs: the root README
  now links `deploy/README.md` first, the gitops README links up to it, and
  every overlay and package kustomization carries a one-line pointer. The
  round-4 haiku run then found the map after 4 calls, finished in 12 calls
  with every answer correct, and scored 3; its remaining confusions were the
  Kustomize "Component" versus `components/` naming, the three directories
  called `keycloak` with two different Routes, and the wrappers `up.sh`
  generates at run time. Those are properties of the manifests, not of the
  layout, and are listed under "Follow-ups".

### Round 5: 22 questions, 40-call budget

A second question set doubled the original eleven with eleven operational
questions (version pinning, prerequisites ownership, the admin Secret per
environment, NetworkPolicies, Keycloak realm rendering, PR-environment CI,
the swap dev loop, the release bundle, policy checks, PostgreSQL per
environment, and a synthesis task: "add a new environment called gcp"). Two
haiku and two sonnet agents ran per tree. The control tree was a clean
worktree of `main`, so no agent could read this proposal.

| Tree | Model | Tool calls | Calls to orient | Correct of 22 | Learnability | First read | Final context | Cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| current | haiku | 23 | 5 | 21 | 2 | none | 140K | $0.21 |
| current | haiku | 18 | 5 | 20 | 2 | none | 116K | $0.13 |
| current | sonnet | 21 | 7 | 21 | 3 | none | 109K | $0.99 |
| current | sonnet | 20 | 5 | 22 | 3 | none | 110K | $0.99 |
| proposed | haiku | 19 | 4 | 22 | 3 | deploy/README.md | 131K | $0.15 |
| proposed | haiku | 20 | 4 | 22 | 3 | deploy/README.md | 133K | $0.18 |
| proposed | sonnet | 17 | 2 | 22 | 4 | deploy/README.md | 95K | $0.80 |
| proposed | sonnet | 22 | 4 | 22 | 4 | deploy/README.md | 100K | $0.87 |
| current | opus | 32 | 7 | 22 | 3 | none | 122K | $2.07 |
| proposed | opus | 32 | 3 | 22 | 4 | deploy/README.md | 101K | $1.83 |

Cost is input-dominated and priced at first-party rates (Haiku 5.5 turns
whose prompt exceeded 100K tokens at the higher tier); output tokens are
under-reported by the transcripts, so sonnet runs are about $0.08 low.

What the larger set showed:

- The learnability gap narrows to one point (2 and 3 versus 3 and 4) because
  the eleven new questions are about scripts, CI and policy checks, which the
  layout change does not touch. The remaining friction is the same on both
  trees and is listed under "Follow-ups".
- Accuracy is high on both trees. The current tree lost points on hedged
  answers (which Keycloak to apply by hand, which workflow deploys a PR
  environment, where the realm JSON lives); the proposed tree lost none.
- Orientation still differs: 2 to 4 calls on the proposed tree against 5 to 7
  on the current one, and every proposed-tree run, haiku included, found
  `deploy/README.md` first. The breadcrumbs added in round 4 held.
- Sonnet was about 15 percent cheaper and ended with a 10 to 15 percent
  smaller context on the proposed tree. Haiku was mixed: it reads more when
  the README gives it more leads to verify.
- One Opus 5.5 run per tree (added after the round, same questions and
  budget) landed where sonnet did on learnability (3 against 4), used the
  most tool calls of any model (32), and was 2 to 2.5 times the cost of
  sonnet. Its distinctive contribution was verification depth: on the
  proposed tree it traced the Kind up script's run-time-generated overlay and
  found that its relative paths (`../kind`) still pointed at the old location.
  That was a real defect in the migration that the byte-identical render
  check could not see, because that overlay only exists while `make kind-up`
  runs. It is fixed in the kit, and the generated overlay now renders
  identically to the current tree's. Opus on the current tree found nothing
  the cheaper models had not.
- On the synthesis task every run produced a sound plan. Proposed-tree runs
  cited the "Adding a new target environment" section of
  `scripts/cluster/README.md` and the prerequisites rule; current-tree runs
  reasoned by copying the nearest sibling, and two noticed that the OpenShift
  driver hard-codes its overlay path, which is a real obstacle for a new
  environment on either tree.

## Migration

`migrate.py` performs the `git mv` operations, fixes the relative paths inside
moved kustomizations, rewrites path strings across the repository (skipping
`oc ... deploy/keycloak` style resource references, which are not paths), and
then applies the fixes a textual rewrite cannot see: a path built from
components in `scripts/sync_openshell_version.py`, a `source` line in
`scripts/kind/lib.sh`, two test fixtures, the `.forbidden-terms-whitelist.json`
line that moves when CLAUDE.md gains two lines, the breadcrumb comments and the
README files. Running it on a fresh worktree of `main` reproduced the evaluated
tree file-for-file.

Verified in a worktree with Kustomize v5.6.0:

- `kustomize build` output for all 14 entry points and the three Components
  is byte-identical before and after (the reaper's generated ConfigMap differs
  only in two comment strings that mention its own path).
- `make check` passes (forbidden terms, dependency pins, CI component
  registration, deploy orphans, dependency age, OpenShell version, CLI drift,
  release bundle).
- `make ci-test` passes: all 20 shell unit test files, 195 OpenShift lifecycle
  tests among them.
- `python3 scripts/test_gitops_manifests.py` and
  `python3 scripts/test_check_deploy_orphans.py` pass with updated paths.

Not verified here: a live `make kind-up` or `make openshift-up`; the
evaluation container has no container engine daemon, kind or kubectl. In its
place a sonnet agent ran a static dry run of the whole Kind lifecycle on the
proposed tree and found no functional defect:

- `bash -n` on all 28 scripts the `kind-*`, `build-all` and `kind-env`
  targets reach; `make -n` resolves every target to an existing executable;
  `load_cluster_driver` with `CLUSTER_DRIVER=kind` resolves to the moved
  implementation directory.
- Every `deploy/`, `scripts/` and `tests/` path referenced by those scripts
  and the Makefile exists; a whole-tree scan for the old paths finds only
  `oc ... deploy/keycloak` resource references, which are not paths.
- The "deploy all components" block of `up.sh` was executed verbatim against
  a copy of each tree with a stubbed `kubectl`, for both `LOCAL_IMAGES`
  settings; the generated wrappers now reference `../overlays/kind` and render
  byte-identically to the current tree's (4,614 lines each), as do the Keycloak
  sub-overlay, the Kind overlay, `base` and `base/prometheus`.
- All 20 shell unit test files pass on the proposed tree with the same counts
  as on `main`, and the Python policy checks pass.
- Two cosmetic findings were fixed in the kit: two `# shellcheck source=`
  directives that still pointed one level too high, and a README sentence that
  called the temporary overlays git-ignored when `.gitignore` does not list
  them (it never did; adding them is a follow-up).

Still outside the evidence: cluster creation, operator installation from the
remote URLs in `prerequisites/kind`, rollouts, DNS and port forwarding.

Coordination needed before merging:

1. **hypershell-gitops** references `deploy/hub` and
   `deploy/gitops-base/components/openshift-dashboard-metrics` by URL at a
   pinned SHA, so nothing breaks at merge time. The next ref bump in that
   repository must point at `deploy/gitops/hub` and
   `deploy/addons/openshift-dashboard-metrics`. Alternatively keep two
   one-line redirect kustomizations at the old paths for one release.
2. **Release bundle** (`scripts/release_bundle.py`,
   `pipelines/release-bundle/pipeline.yaml`) packages the renamed paths; the
   bundle's internal directory names change accordingly.
3. **CI component registration** (`.github/component-paths.json`) is updated
   by the migration to `deploy/overlays/**`, `deploy/prerequisites/**`,
   `deploy/standalone/**`. `deploy/addons/**` and `deploy/gitops/**` were not
   registered before and are still not; run `/maintain-ci` if they should be.
4. Open pull requests touching `deploy/` or `scripts/kind/` will need a
   rebase; `git` tracks the renames, so conflicts are limited to files edited
   on both sides.

## Follow-ups surfaced by the evaluation (not part of this proposal)

Each of these was raised independently by at least one agent and is a real
property of the current tree, not an artifact of the move.

- `overlays/openshift` includes `base/keycloak` directly plus its own Route and
  NetworkPolicy, while `overlays/openshift/keycloak` (the old `deploy/keycloak`)
  composes the same base with a different Route and hostname patch. One of the
  two should go, or the full overlay should include the sub-overlay the way
  `overlays/kind` does. The stage-1 sub-overlay also ships a placeholder
  hostname (`keycloak.apps.example.com`) that the deploy skill replaces with
  `sed`; the README should say so, or the hostname should become a patch.
- `gitops/platform` hard-codes `HYPERSHELL_MANAGED_CLUSTER_NAME=hub`,
  provider `aws` and visibility `public`, which contradicts the "shared
  packages are environment-neutral" intent; the values belong in the
  hypershell-gitops environment overlay.
- PostgreSQL is defined three ways (`base/postgres.yaml` for OpenShift dev, a
  heredoc in `scripts/cluster/kind/up.sh` for Kind, external in production) and
  `base/postgres.yaml` is not reachable from `base/kustomization.yaml`.
- `scripts/cluster/kind/up.sh` applies `base/prometheus` a second time after
  the overlay (which already includes it) and renders `overlays/kind/jaeger.yaml`
  with `sed` outside Kustomize.
- `scripts/sync_openshell_version.py` lists a file that does not exist
  (`deploy/base/control-plane/deployment.yaml`) and silently skips missing
  files, so a renamed manifest would drop out of the version check unnoticed.
  It should fail on a missing managed file.
- `skills/deploy/deploy-cluster/SKILL.md` says the OpenShift overlay uses
  `:latest` for production while the gitops README says digests are pinned in
  hypershell-gitops; one of them is stale.
- `skills/RECONCILE.md` referenced `deploy/kind/prerequisites/`, a path that
  never existed (fixed by the migration).
- The `openshift-dashboard-metrics` README documents itself in terms of pull
  request numbers (#251, #119) rather than the current contract.
- `.github/component-paths.json` and `skills/RECONCILE.md` name a workflow
  `.github/workflows/pr-environment.yml` that does not exist; the PR
  environment is deployed from `e2e.yml` and `pr-environment-commands.yml`.
- `scripts/test_gitops_manifests.py`, the render-equivalence guard the gitops
  README advertises, runs only in the `checks.yml` CI job and is not part of
  `make check`.
- `GATEWAY-SETUP.md` creates a ClusterIssuer named `letsencrypt-dns`, while
  the overlays and the controller expect `hypershell-ca-issuer`; the
  relationship is not explained.
- `skills/deploy/gcp-cluster/SKILL.md` references pre-split paths
  (`deploy/base/controller-rbac.yaml`, `base/web-console.yaml`).
- `scripts/cluster/drivers/openshift.sh` hard-codes `deploy/openshift` as its
  overlay, so a new OpenShift-family environment (gcp, ibm) cannot reuse the
  driver without parameterizing it; neither ibm nor gcp has a make target.
- The release-bundle path list lives in `scripts/release_bundle.py` and is
  copied into the generated `pipelines/release-bundle/pipeline.yaml`; the
  generation step is not obvious to a reader of the pipeline file.
- The Kind overlay header still says "base is app-only", which stopped being
  true when `base/` regained the platform package, and
  `overlays/openshift/keycloak` describes itself as the "single shared
  Keycloak" while the README calls it the stage-1 render.
