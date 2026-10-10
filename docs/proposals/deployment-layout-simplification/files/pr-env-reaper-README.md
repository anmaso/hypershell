# pr-env-reaper - reference copy

CronJob and RBAC that reclaim expired ephemeral pull-request environments
(`specs/platform/ephemeral-pr-environments.spec.md`, "Timebox and Reaping").
The scripts it runs are generated into a ConfigMap from `scripts/ci/`, so it
builds with `--load-restrictor=LoadRestrictionsNone`.

Nothing in this repository deploys it. The live copy is an Argo CD application
in hypershell-gitops (`clusters/hysh-aws-01/apps/pr-env-reaper`). Change the
schedule, RBAC or scripts here first, then sync that copy by hand.
