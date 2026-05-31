# Model Caching and Startup Optimization

## The Cold Start Problem

Every time a model-server pod starts on a fresh node — scale-up, node drain, pod reschedule, or first deployment — it must load model weights and (on Inferentia) compile NEFF artifacts before serving traffic. Uncached cold starts dominate operational downtime:

| Stage | Accelerator | Cold Start Duration |
|-------|-------------|-------------------|
| Model weight download | NVIDIA GPU | 4–15 min (depends on model size and network) |
| Model weight download | Inferentia2 | 4–15 min |
| NEFF compilation | Inferentia2 only | 30–45 min (first run, no cache) |
| Pod init + health check | Both | 1–3 min |

For a 30B-class model (~60GB on disk), downloading from Hugging Face on every pod restart wastes GPU node time and blocks developer access.

```mermaid
flowchart LR
    COLD[Cold Start<br/>4–45 min] -->|PVC / Snapshot / OCI| WARM[Warm Start<br/>10s–5 min]
    WARM --> SERVE[Serving Traffic]
```

## Warm Start Targets

With caching in place, startup times drop dramatically:

| Accelerator | Warm Start (cached weights) | Warm Start (NEFF cached) |
|-------------|----------------------------|-------------------------|
| NVIDIA GPU | ~3–5 min (load weights to VRAM) | N/A |
| Inferentia2 | ~3–5 min (load weights) | ~10s (NEFF cache hit) |

The KServe **storage-initializer** init container checks the mount path before downloading. If model files already exist on the PVC, the download step is skipped entirely.

## Caching Strategy Comparison

| Approach | Cold Start | Warm Start | Portability | Cost |
|----------|-----------|-----------|-------------|------|
| EBS PVC | Full download | ~10s–3 min | Same AZ only | $0.08/GB/mo |
| EBS Snapshots | Instant API | Same as PVC | Same region | $0.05/GB/mo |
| OCI Model Images | ~5–10 min pull | Near-instant | Any cluster | Registry + egress |
| S3 Mirror | ~5 min download | Same as first | Cross-region | $0.023/GB/mo |

### EBS PVC (Recommended Baseline)

PersistentVolumeClaims bind model weights to a specific availability zone. Once populated, every pod in that AZ mounts the same volume and skips the download.

**Best for:** Single-cluster, single-AZ deployments on ROSA with gp3-csi.

**Limitation:** PVCs do not move across AZs or regions. Scaling GPU nodes must stay in the same AZ as the PVC.

### EBS Snapshots

Create a snapshot of a populated PVC, then provision new PVCs from the snapshot. The API call is near-instant — only the first read triggers lazy block hydration.

**Best for:** Rapid scale-up of new GPU nodes in the same region without re-downloading weights.

**Limitation:** Same-region only. Cross-region snapshot copy adds latency and cost.

### OCI Model Images

Package model weights into a container image pushed to a registry (Quay, ECR, ACR). Pods pull the image instead of downloading from Hugging Face.

**Best for:** Multi-cluster, multi-cloud, or multi-region deployments where PVC portability is insufficient.

**Limitation:** Registry storage cost, image pull time (~5–10 min for large models), and egress charges.

### S3 Mirror

Mirror Hugging Face model files to an S3 bucket (or Azure Blob equivalent). Storage-initializer or a custom init container downloads from S3 instead of Hugging Face — faster and more reliable within the same cloud.

**Best for:** Cross-region deployments within AWS, or as a shared artifact store for multiple clusters.

**Limitation:** First download still required per PVC; not as fast as snapshot or OCI for warm starts.

## PVC Manifest Example

Create a dedicated PVC for model cache in the serving namespace. This matches the pattern used in Phase 4:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-cache
  namespace: model-serving
  labels:
    app.kubernetes.io/part-of: code-assistant-lab
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: gp3-csi          # ROSA: gp3-csi | ARO: managed-csi
  resources:
    requests:
      storage: 100Gi
```

Mount the PVC in your `InferenceService` (or `LLMInferenceService` if using llm-d) spec:

```yaml
spec:
  model:
    name: Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
    uri: hf://Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
  storage:
    key: model-cache
    path: /mnt/models
    parameters:
      type: persistent
```

The storage-initializer init container:

1. Checks `/mnt/models` for existing weight files.
2. Skips download if files are present (warm start).
3. Downloads from Hugging Face only on first populate (cold start).

Verify cache population:

```bash
# Check PVC is bound
oc get pvc model-cache -n model-serving

# Confirm weights exist (exec into a running pod)
oc exec -n model-serving deploy/vllm-model-server -- ls -lh /mnt/models
```

## Operational Best Practices

### Do Not Delete PVCs When Scaling Down Nodes

When reducing GPU node count or deleting machine pools, **retain the model cache PVC**. Deleting the PVC forces a full re-download on the next scale-up — the most expensive cold start scenario.

```bash
# Scale down nodes — keep PVC
rosa edit machinepool --cluster <name> --name gpu-pool --replicas 0

# PVC persists — verify
oc get pvc model-cache -n model-serving
# STATUS: Bound (unchanged)
```

| Action | PVC Impact | Restart Cost |
|--------|-----------|-------------|
| Scale machine pool to 0 | PVC retained | Warm start on scale-up |
| Delete pod (reschedule) | PVC retained | Warm start (~10s–3 min) |
| Delete PVC | Weights lost | Full cold start (4–45 min) |
| Delete namespace | PVC deleted (unless retained policy) | Full cold start |

### Pre-Populate Before First Serve

For Inferentia2 deployments, pre-populate the PVC and allow NEFF compilation to complete *before* exposing the endpoint to developers:

1. Deploy a single pod with the PVC mounted.
2. Wait for model download and NEFF compilation to finish.
3. Take an EBS snapshot of the populated PVC.
4. Scale to production replica count using snapshot-derived PVCs.

### Snapshot Workflow (ROSA)

```bash
# 1. Populate PVC (deploy pod, wait for download)
# 2. Create VolumeSnapshot
cat <<EOF | oc apply -f -
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: model-cache-snapshot
  namespace: model-serving
spec:
  volumeSnapshotClassName: csi-aws-vsc
  source:
    persistentVolumeClaimName: model-cache
EOF

# 3. Verify snapshot is ready
oc get volumesnapshot model-cache-snapshot -n model-serving

# 4. Create new PVC from snapshot for additional nodes
cat <<EOF | oc apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-cache-gpu-2
  namespace: model-serving
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: gp3-csi
  dataSource:
    name: model-cache-snapshot
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
  resources:
    requests:
      storage: 100Gi
EOF
```

### Node Affinity for PVC Co-Location

Because ReadWriteOnce PVCs bind to a single AZ, GPU nodes must run in the **same availability zone** as the PVC:

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: topology.kubernetes.io/zone
          operator: In
          values:
          - us-east-1a    # Must match PVC AZ
```

> **Key insight:** Model caching eliminates the download bottleneck but does not eliminate VRAM loading time. A warm GPU start (~3–5 min) is still required to load weights into GPU memory — plan pod disruption budgets accordingly.

## Strategy Selection Guide

| Deployment Pattern | Recommended Strategy |
|-------------------|---------------------|
| Single ROSA cluster, single AZ | EBS PVC |
| ROSA cluster, frequent scale-up/down | EBS PVC + Snapshots |
| Multi-cluster (ROSA + ARO) | OCI Model Images |
| Cross-region AWS | S3 Mirror + PVC per region |
| Inferentia2 with NEFF compilation | PVC + Snapshot (after first compile) |

## Next Steps

→ Return to `2_multi_accelerator.md` when deploying heterogeneous pools — both NVIDIA and Inferentia pods should share or mirror the same model cache.

→ Run Phase 6 benchmarks after cache optimization to measure warm-start impact on TTFT SLOs.
