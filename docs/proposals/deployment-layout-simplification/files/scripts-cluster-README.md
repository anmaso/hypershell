# scripts/cluster - cluster lifecycle for every target environment

`make kind-*` and `make openshift-*` both run the scripts in this directory
with `CLUSTER_DRIVER` set. The entry points are driver-neutral; the driver
supplies the implementation.

```text
make kind-up
  -> CLUSTER_DRIVER=kind scripts/cluster/up.sh
     -> lib.sh: load_cluster_driver sources drivers/kind.sh
        -> cluster_up: exec scripts/cluster/kind/up.sh      (Kind implementation)

make openshift-up
  -> CLUSTER_DRIVER=openshift scripts/cluster/up.sh
     -> lib.sh: load_cluster_driver sources drivers/openshift.sh
        -> cluster_up: implemented inside drivers/openshift.sh
```

| Path | Role |
| --- | --- |
| `up.sh`, `down.sh`, `teardown.sh`, `status.sh`, `seed.sh`, `swap.sh` | Driver-neutral entry points used by the Makefile |
| `lib.sh` | Shared helpers, driver loading, test-user reconciliation (`lib_test.sh` covers it) |
| `drivers/kind.sh` | Thin driver that delegates every lifecycle function to `kind/` |
| `drivers/openshift.sh` | Complete OpenShift driver (renders `deploy/overlays/openshift`, bootstraps Keycloak and the database) |
| `kind/` | Kind implementation: creates the cluster from `deploy/prerequisites/kind/kind-config.yaml`, applies `deploy/prerequisites/kind`, `deploy/overlays/kind/keycloak`, then `deploy/overlays/kind`; also the helper scripts behind `make kind-openshell`, `make kind-gateway-trust`, `make kind-grpc-tls-smoke` |

Adding a new target environment means adding `drivers/<name>.sh` that defines
`cluster_up`, `cluster_down`, `cluster_teardown`, `cluster_status`,
`cluster_seed`, `component_swap` and `component_revert`, plus a
`deploy/overlays/<name>` kustomization. The manifests themselves are described
in [deploy/README.md](../../deploy/README.md).
