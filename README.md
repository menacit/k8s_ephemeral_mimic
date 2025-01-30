<!--
SPDX-FileCopyrightText: © 2025 Menacit AB <foss@menacit.se>
SPDX-License-Identifier: CC-BY-SA-4.0
-->

# k8s\_ephemeral\_mimic


## Introduction
TODO!


## Example usage
Generate and apply ephemeral container patch:

```
$ NAMESPACE=kube-system
$ POD=cilium-g5xf4
$ CONTAINER=cilium-agent
$ EPHEMERAL_IMAGE=ghcr.io/doctor-love/k8s_assessment_tools:latest

$ kubectl proxy &
$ PROXY_PID=${!}
$ BASE_URL=http://localhost:8001/api/v1/namespaces/${NAMESPACE}/pods/${POD}

$ curl \
    --request GET \
    ${BASE_URL} \
  | ./k8s_ephemeral_mimic.py \
    --container ${CONTAINER} \
    --image ${EPHEMERAL_IMAGE} \
  | curl \
    --request PATCH \
    --header 'Content-Type: application/strategic-merge-patch+json' \
    --data @- \
    ${BASE_URL}/ephemeralcontainers

$ kill ${PROXY_PID}
```

Dump environment variables and list mounted volumes:

```
$ kubectl \
  --namespace ${NAMESPACE} exec ${POD} \
  -c mimic-0 -- env | grep MIMIC_
  
MIMIC_CILIUM_CLUSTERMESH_CONFIG=/var/lib/cilium/clustermesh/
MIMIC_GOMEMLIMIT=3896381440
MIMIC_KUBERNETES_SERVICE_HOST=213.24.76.23
MIMIC_KUBERNETES_SERVICE_PORT=6443
MIMIC_K8S_NODE_NAME=worker-2
MIMIC_CILIUM_K8S_NAMESPACE=kube-system

$ kubectl \
  --namespace ${NAMESPACE} exec ${POD} \
  -c mimic-0 -- mount | grep /mimic/ | cut -d ' ' -f 3

/mimic/tmp
/mimic/lib/modules
/mimic/run/xtables.lock
/mimic/sys/fs/bpf
/mimic/var/run/cilium
/mimic/var/run/cilium/cgroupv2
/mimic/host/proc/sys/net
/mimic/host/proc/sys/kernel
/mimic/host/etc/cni/net.d
/mimic/var/lib/cilium/clustermesh
/mimic/var/run/cilium/envoy/sockets
/mimic/var/lib/cilium/tls/hubble
/mimic/var/run/secrets/kubernetes.io/serviceaccount
```
