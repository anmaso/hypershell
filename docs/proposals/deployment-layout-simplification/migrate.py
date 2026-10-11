#!/usr/bin/env python3
"""Apply the deployment layout proposal to a clean checkout. Run from the repository root:

    python3 docs/proposals/deployment-layout-simplification/migrate.py

Moves directories with git mv, fixes relative paths inside moved kustomizations,
rewrites path strings across the repository, applies the small manual fixes the
rewrite cannot see, and installs the README files shipped next to this script.
Rendered manifests are unchanged; verify with kustomize build before and after.
"""
import json, os, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path.cwd()
KIT = Path(__file__).resolve().parent / "files"

def git(*args):
    subprocess.run(["git", *args], check=True, cwd=ROOT)

def mv(src, dst):
    (ROOT / dst).parent.mkdir(parents=True, exist_ok=True)
    git("mv", str(ROOT / src), str(ROOT / dst))

def edit(path, pairs):
    p = ROOT / path
    s = p.read_text()
    for a, b in pairs:
        if a not in s:
            sys.exit(f"edit: {a!r} not found in {path}")
        s = s.replace(a, b, 1)
    p.write_text(s)

# 1. Moves (order matters).
mv("deploy/base/platform-resources", "deploy/base/platform")
mv("deploy/kind", "deploy/overlays/kind")
mv("deploy/overlays/kind/infrastructure", "deploy/prerequisites/kind")
mv("deploy/overlays/kind/kind-config.yaml", "deploy/prerequisites/kind/kind-config.yaml")
mv("deploy/overlays/kind/coredns", "deploy/prerequisites/kind/coredns")
mv("deploy/openshift", "deploy/overlays/openshift")
mv("deploy/overlays/openshift/infrastructure", "deploy/prerequisites/openshift")
mv("deploy/keycloak", "deploy/overlays/openshift/keycloak")
mv("deploy/ibm", "deploy/overlays/ibm")
mv("deploy/hub", "deploy/gitops/hub")
mv("deploy/components/gateway-database-admin-secret", "deploy/addons/gateway-database-admin-secret")
mv("deploy/gitops-base/components/openshift-dashboard-metrics", "deploy/addons/openshift-dashboard-metrics")
mv("deploy/e2e/reaper", "deploy/standalone/pr-env-reaper")
mv("scripts/kind", "scripts/cluster/kind")
for empty in ("deploy/components", "deploy/e2e", "deploy/gitops-base/components", "deploy/gitops-base"):
    d = ROOT / empty
    if d.is_dir() and not any(d.iterdir()):
        d.rmdir()

# 2. Relative paths inside moved files and other edits the rewrite cannot see.
edit("deploy/base/kustomization.yaml", [("- platform-resources", "- platform")])
edit("deploy/overlays/kind/kustomization.yaml", [("  - ../base\n", "  - ../../base\n")])
edit("deploy/overlays/kind/keycloak/kustomization.yaml", [("../../base/keycloak/", "../../../base/keycloak/")])
edit("deploy/overlays/openshift/kustomization.yaml", [
    ("  - ../base/postgres.yaml", "  - ../../base/postgres.yaml"),
    ("  - ../base/keycloak/", "  - ../../base/keycloak/"),
    ("  - ../base\n", "  - ../../base\n"),
])
edit("deploy/overlays/openshift/keycloak/kustomization.yaml", [("  - ../base/keycloak", "  - ../../../base/keycloak")])
edit("deploy/gitops/platform/kustomization.yaml", [("../../base/platform-resources", "../../base/platform")])
edit("deploy/gitops/hub/kustomization.yaml", [("  - ../gitops/platform", "  - ../platform"), ("  - ../gitops/applications", "  - ../applications")])
edit("scripts/cluster/kind/lib.sh", [
    ('}/../.." && pwd)"', '}/../../.." && pwd)"'),
    ("# shellcheck source=../cluster/reconcile-test-users.sh", "# shellcheck source=../reconcile-test-users.sh"),
    ('/../cluster/reconcile-test-users.sh"', '/../reconcile-test-users.sh"'),
    ("# shellcheck source=../../OPENSHELL_VERSION", "# shellcheck source=../../../OPENSHELL_VERSION"),
])
edit("scripts/cluster/kind/openshell-container.sh", [
    ('/../.." && pwd)"', '/../../.." && pwd)"'),
    ("# shellcheck source=../../OPENSHELL_VERSION", "# shellcheck source=../../../OPENSHELL_VERSION"),
])
# up.sh writes a temporary kustomization under deploy/ at run time whose relative
# paths point at the overlay; those are not repo paths, so the rewrite below misses them.
edit("scripts/cluster/kind/up.sh", [
    ("  - ../kind/database-external'", "  - ../overlays/kind/database-external'"),
    ("  - ../kind${_db_overlay_extra}", "  - ../overlays/kind${_db_overlay_extra}"),
    ("  - ../kind${_db_overlay_extra}", "  - ../overlays/kind${_db_overlay_extra}"),
])
edit("scripts/test_gitops_manifests.py", [
    ('cls.hub = render("hub")', 'cls.hub = render("gitops/hub")'),
    ('("base", "openshift", "ibm", "kind", "keycloak", "base/prometheus")',
     '("base", "overlays/openshift", "overlays/ibm", "overlays/kind", "overlays/openshift/keycloak", "base/prometheus")'),
])
edit("scripts/test_check_deploy_orphans.py", [
    ('"deploy/kind/kustomization.yaml": "resources:\\n  - ../base/kc/\\n"',
     '"deploy/overlays/kind/kustomization.yaml": "resources:\\n  - ../../base/kc/\\n"'),
])
edit("scripts/sync_openshell_version.py", [
    ('REPO_ROOT / "deploy" / "base" / "platform-resources" / "controller.yaml"', 'REPO_ROOT / "deploy" / "base" / "platform" / "controller.yaml"'),
    ('REPO_ROOT / "deploy" / "ibm" / "kustomization.yaml"', 'REPO_ROOT / "deploy" / "overlays" / "ibm" / "kustomization.yaml"'),
])
edit("deploy/addons/gateway-database-admin-secret/README.md", [
    ("  - ../components/gateway-database-admin-secret", "  - ../../addons/gateway-database-admin-secret"),
    ("# deploy/<env>/kustomization.yaml", "# deploy/overlays/<env>/kustomization.yaml (or the environment overlay in hypershell-gitops)"),
])
edit("deploy/addons/gateway-database-admin-secret/kustomization.yaml", [
    ("#     - ../../components/gateway-database-admin-secret", "#     - ../../addons/gateway-database-admin-secret"),
])
edit("deploy/base/applications/kustomization.yaml", [
    ("kept with its ServiceAccount and RBAC in ../platform-resources.", "kept with its ServiceAccount and RBAC in ../platform."),
])

# 3. Repo-wide path rewrites (longest first); skip kubectl/oc resource refs such as `oc get deploy/keycloak`.
RULES = [
    ("deploy/kind/infrastructure", "deploy/prerequisites/kind"),
    ("deploy/kind/kind-config.yaml", "deploy/prerequisites/kind/kind-config.yaml"),
    ("deploy/kind/coredns", "deploy/prerequisites/kind/coredns"),
    ("deploy/openshift/infrastructure", "deploy/prerequisites/openshift"),
    ("deploy/base/platform-resources", "deploy/base/platform"),
    ("deploy/gitops-base/components/openshift-dashboard-metrics", "deploy/addons/openshift-dashboard-metrics"),
    ("deploy/gitops-base/components", "deploy/addons"),
    ("deploy/gitops-base", "deploy/addons"),
    ("deploy/components/gateway-database-admin-secret", "deploy/addons/gateway-database-admin-secret"),
    ("deploy/components", "deploy/addons"),
    ("deploy/e2e/reaper", "deploy/standalone/pr-env-reaper"),
    ("deploy/e2e", "deploy/standalone"),
    ("deploy/hub", "deploy/gitops/hub"),
    ("deploy/keycloak", "deploy/overlays/openshift/keycloak"),
    ("deploy/kind", "deploy/overlays/kind"),
    ("deploy/openshift", "deploy/overlays/openshift"),
    ("deploy/ibm", "deploy/overlays/ibm"),
    ("scripts/kind", "scripts/cluster/kind"),
]
K8S_CMD = re.compile(r"\b(oc|kubectl|kube|kube_cli|oc_cli|rollout|get|patch|describe)\b")
SKIP_DIRS = {".git", "node_modules", "dist", ".pnpm-store"}
SKIP_FILES = {"pnpm-lock.yaml"}
SKIP_PREFIX = str(Path(__file__).resolve().parent)

def is_text(p):
    try:
        return b"\0" not in p.read_bytes()[:4096]
    except OSError:
        return False

changed = 0
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
    if dirpath.startswith(SKIP_PREFIX):
        continue
    for fn in filenames:
        p = Path(dirpath) / fn
        if fn in SKIP_FILES or not is_text(p):
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        out = []
        for line in text.split("\n"):
            new = line
            for a, b in RULES:
                if a not in new:
                    continue
                if a in ("deploy/keycloak", "deploy/hub") and K8S_CMD.search(new) and not re.search(a + r"/", new):
                    continue
                new = re.sub(re.escape(a) + r"(?![\w-])", b, new)
            out.append(new)
        if (joined := "\n".join(out)) != text:
            p.write_text(joined, encoding="utf-8")
            changed += 1
print(f"rewrote {changed} files")

# 4. Fixes after the rewrite.
edit("deploy/addons/openshift-dashboard-metrics/README.md", [("It can patch the existing `deploy/hub` base", "It can patch the existing `deploy/gitops/hub` base")])
edit("skills/RECONCILE.md", [
    ("`deploy/overlays/kind/prerequisites/`", "`deploy/prerequisites/kind/`, `deploy/overlays/kind/`"),
    ("`deploy/overlays/kind/prerequisites/keycloak.yaml`", "`deploy/base/keycloak/`, `deploy/overlays/kind/keycloak/`"),
    ("`deploy/overlays/kind/prerequisites/`", "`deploy/prerequisites/kind/`, `deploy/overlays/kind/`"),
])
edit(".github/component-paths.json", [
    ('      "deploy/base/**",\n      "deploy/overlays/kind/**",\n      "deploy/overlays/openshift/**",\n      "deploy/standalone/**",',
     '      "deploy/base/**",\n      "deploy/overlays/**",\n      "deploy/prerequisites/**",\n      "deploy/standalone/**",'),
])
edit("CLAUDE.md", [("- `specs/` - Desired state of the system",
    "- `deploy/` - Kustomize manifests: `base/`, `overlays/{kind,openshift,ibm}`, `gitops/`, `addons/`, `prerequisites/`, `standalone/`; start at [deploy/README.md](deploy/README.md)\n"
    "- `scripts/cluster/` - cluster lifecycle scripts behind `make kind-*` and `make openshift-*` (driver pattern, see [scripts/cluster/README.md](scripts/cluster/README.md))\n"
    "- `specs/` - Desired state of the system")])
wl = ROOT / ".forbidden-terms-whitelist.json"
entries = json.loads(wl.read_text())
for e in entries:
    if e["filename"] == "CLAUDE.md" and e["line"] == 162:
        e["line"] = 164
wl.write_text(json.dumps(entries, indent=2) + "\n")
edit("README.md", [("""## GitOps deployment packages

For separate platform and application Argo CD instances, see the
[GitOps deployment packages](deploy/gitops/README.md). The existing `deploy/gitops/hub`
entry point remains a combined deployment for current consumers.""",
"""## Deployment manifests

All Kubernetes manifests live under `deploy/`; start with
[deploy/README.md](deploy/README.md), which maps every directory (base,
overlays, gitops, addons, prerequisites, standalone) to its purpose and
consumer. For separate platform and application Argo CD instances, see the
[GitOps deployment packages](deploy/gitops/README.md). The existing `deploy/gitops/hub`
entry point remains a combined deployment for current consumers.""")])
edit("deploy/gitops/README.md", [("# Platform and application GitOps packages\n\n",
    "# Platform and application GitOps packages\n\n> Part of the `deploy/` layout described in [../README.md](../README.md).\n> This file covers only the packages hypershell-gitops consumes.\n\n")])
HEAD = "apiVersion: kustomize.config.k8s.io/v1beta1\nkind: Kustomization\n"
for f, what in [
    ("deploy/overlays/kind/kustomization.yaml", "Kind dev overlay. Layout and consumers: deploy/README.md"),
    ("deploy/overlays/openshift/kustomization.yaml", "OpenShift dev/PR overlay. Layout and consumers: deploy/README.md"),
    ("deploy/overlays/ibm/kustomization.yaml", "IBM ROKS overlay. Layout and consumers: deploy/README.md"),
    ("deploy/gitops/hub/kustomization.yaml", "Combined GitOps package. Layout and consumers: deploy/README.md"),
    ("deploy/gitops/platform/kustomization.yaml", "Platform Argo CD package. Layout and consumers: deploy/README.md"),
    ("deploy/gitops/applications/kustomization.yaml", "Application Argo CD package. Layout and consumers: deploy/README.md"),
    ("deploy/base/kustomization.yaml", "Environment-neutral core (platform + applications). Layout and consumers: deploy/README.md"),
]:
    p = ROOT / f
    s = p.read_text()
    assert s.startswith(HEAD), f
    p.write_text(HEAD + f"# {what}\n" + s[len(HEAD):])

# 5. Install the README files shipped with this script.
for src, dst in [
    ("deploy-README.md", "deploy/README.md"),
    ("prerequisites-README.md", "deploy/prerequisites/README.md"),
    ("pr-env-reaper-README.md", "deploy/standalone/pr-env-reaper/README.md"),
    ("scripts-cluster-README.md", "scripts/cluster/README.md"),
]:
    shutil.copyfile(KIT / src, ROOT / dst)
git("add", "-A")
print("done; review with: git status && git diff --cached -M --stat")
