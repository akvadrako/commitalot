---
name: Custom issue template
about: Describe this issue template's purpose here.
title: ddd
labels: duplicate
assignees: akvadrako

---

Migrate xxx from yyy to zzz.

## Prepare

- [ ] The new cluster must be created.
      See [Upgrade-EKS-Cluster](https://www.notion.so/onelayerhq/Upgrade-EKS-Cluster-2992cd90517280969f43e46da10cfbdc)

- [ ] You need to setup your local kubernetes context for onelayer.
      See [Configure-Local-K8s-Access](https://www.notion.so/onelayerhq/Configure-Local-K8s-Access-3572cd905172803c90f4eed44590f6c5)

- [ ] Set local variables

```bash
NS="<namespace>" # ex: mendev
SRC="<old-cluster-context>"  # ex: dev-green
DEST="<new-cluster-context>" # ex: dev-blue

# get the backup locations
velero --kubecontext=$SRC backup-location get
velero --kubecontext=$DEST backup-location get

SRC_BUCKET=s3://onelayer-${SRC}-backup
DEST_BUCKET=s3://onelayer-${DEST}-backup
```

## Copy secrets not managed by ExternalSecrets

- [ ] edge-server-certs
- [ ] ndac-bootstrap-tokens-secrets
- [ ] servicenow-instrument-credentials
- [ ] nokia-dac-secrets

You can use this script:

```bash
# copy secrets from one context to another
cs() {
  kubectl --context=$DEST create namespace $1 2>/dev/null || true
	kubectl --context=$SRC get secret $2 -n $1 -o json \
	| jq 'del(.metadata.resourceVersion)' \
	| kubectl --context=$DEST apply -f -
}

cs $NS edge-server-certs
cs $NS ndac-bootstrap-tokens-secrets
cs $NS servicenow-instrument-credentials
cs $NS nokia-dac-secrets
```

## Perform manual CLI steps

- [ ] Stop old environment

```bash
kubectl --context=$SRC -n $NS create quota block-pods --hard=pods=0
kubectl --context=$SRC -n $NS delete pod --all
```

- [ ] Do one last Velero backup

```bash
velero --kubecontext=$SRC backup create $NS --wait \
    --selector 'velero-exclude!=true' \
    --include-namespaces $NS --include-resources pvc,pv
```

- [ ] S3 sync and restore on new cluster

```bash
aws s3 sync $SRC_BUCKET/backups/backups/$NS \
            $DEST_BUCKET/backups/backups/$NS
velero --kubecontext=$DEST restore create --from-backup $NS --exclude-resources pod
```

- [ ] Delete Kafka PVCs !!!

- [ ] Switch traffic

```yaml
weights:
  green: 0 # old
  blue: 100 # new
```

## Validate

Validate the environment is operational on the new cluster.

Run the post-migration validation script (OneLayerHQ/quality-assurance#623, @kyrylzb) which covers:

**Infrastructure health**

- [ ] All core K8s resources healthy (pods, deployments)
- [ ] Key services reachable (`fingerprint-view`, `overlay-corpus`, `network-twin`, mismatch detectors, `datapath-state-monitor`)
- [ ] Kafka topic connectivity and message flow verified on KRaft
- [ ] PostgreSQL accessible with schemas intact (`gsmadb`, `detection`, `trafficflowjournal`)

**Data integrity**

- [ ] Device records present and correctly resolved (manufacturer, model, hardware_type populated)
- [ ] Alert types and counts in `detection.alerts_journal` within expected ranges
- [ ] GSMA DB record count unchanged
- [ ] Topology/cell data intact

**UI critical flows (Playwright E2E)**

- [ ] Devices page loads and displays devices
- [ ] Dashboard renders correctly
- [ ] Topology page shows cells and devices
- [ ] Device details panel shows correct data
- [ ] Integrations page loads with Cellular Core section visible
- [ ] Monitoring alerts visible in UI

**Cluster-level checks**

- [ ] Confirm NATS v2 connectivity
- [ ] Verify external DNS records resolve to new cluster
- [ ] Test Cloudflare tunnel access
- [ ] Validate monitoring dashboards show metrics from new cluster
- [ ] Confirm Velero backup schedule is active on new cluster

## Rollback

If migration fails for an environment:

```bash
kubectl --context=$SRC -n $NS delete quota block-pods
kubectl --context=$SRC rollout restart deployment --all -A
kubectl --context=$SRC rollout restart statefulset --all -A
```

Then revert the weights back to the old color.
