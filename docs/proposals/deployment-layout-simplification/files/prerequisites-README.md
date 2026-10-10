# prerequisites/ - what must exist on the cluster before any overlay

These are cluster-scoped and installed once per cluster, never by the platform
overlays and never by Argo CD from the `gitops/` packages.

| Directory | Contents | Applied by |
| --- | --- | --- |
| `kind/` | Kind cluster config (`kind-config.yaml`), CoreDNS wildcard config, and a kustomization that installs Gateway API CRDs, cert-manager, agent-sandbox and prometheus-operator from pinned upstream release URLs | `scripts/cluster/kind/up.sh`, automatically |
| `openshift/` | GatewayClass, the shared Gateway, agent-sandbox. cert-manager and the Gateway API controller come from OperatorHub and are not manifests here | a cluster admin, by hand, following [openshift/GATEWAY-SETUP.md](openshift/GATEWAY-SETUP.md); `make openshift-up` only checks they exist |

The two directories are deliberately not symmetric: Kind is a throwaway cluster
this repo fully owns, OpenShift clusters are shared and operator-managed.
IBM ROKS cannot run the Gateway API path at all and uses Route ingress instead
(see `overlays/ibm`).
