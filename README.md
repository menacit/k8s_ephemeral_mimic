<!--
SPDX-FileCopyrightText: © 2025 Menacit AB <foss@menacit.se>
SPDX-License-Identifier: CC-BY-SA-4.0
-->

# k8s\_ephemeral\_mimic


## Introduction
Since \~version 1.23, Kubernetes supports a feature called
["ephemeral containers"](https://kubernetes.io/docs/concepts/workloads/pods/ephemeral-containers/)
which enables ad-hoc startup of containers inside a running pod. This is neat, since pods are
traditionally somewhat immutable and the addition of a long-running side-car container with every
potentially useful debugging tool would result in overhead.  

The feature could also be useful security testing and attack simulation. Instead of speculating
what the consequences could be if _application X_ in _container Y_ of _pod Z_ got popped, let's
spawn an ephemeral container with access to the same volume mounts, secrets, etc and try it out!
Furthermore, any network policies restricting the "parent pod" would also apply to the ephemeral
container.

All the things that give a container its personality (config maps, volumes, security context, etc)
are unfortunately not automatically shared with ephemeral containers. If all pod containers are
running in the same "PID namespace" or the "targetContainerName" property is specified, we may
however abuse a quirk of /proc to access another container's file system/environment variables,
[as noted by Ivan Velichko](https://iximiuz.com/en/posts/kubernetes-ephemeral-containers/#using-kubectl-debug-with-a-shared-pid-namespace).

This trick does not always work and seem to depend on configuration of the underlying container
runtime/operating system. Furthermore, any container-specific security context won't be copied.
Hence, the creation of "k8s\_ephemeral\_mimic.py" - a simple script that clones the
"securityContext", "env", "envFrom" and "volumeMounts" properties of a targeted container. The
tool produces a "JSON patch file" which can be applied to spawn a similar-ish ephemeral container
in a running pod.


## Acknowledgements
This tool was created during research for
[Menacit's Kubernetes Security Course](https://github.com/menacit/kubernetes_security_course).
Funding for development of the course was provided by _Sweden's National Coordination Centre for
Research and Innovation in Cybersecurity_, _the Swedish Civil Contingencies Agency_ and
_the European Union's European Cybersecurity Competence Centre_.  


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
      --read-only-volumes \
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
    -c mimic-0 -- mount \
  | grep /mimic/ | cut -d ' ' -f 3

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


## CLI options
```
usage: k8s_ephemeral_mimic.py [-h] [-i /path/to/pod.json] [-o /path/to/pod.json]
                              [-c container-name] -I example.com/image_name:latest [-e FOO=BAR]
                              [-E {securityContext,env,envFrom,volumeMounts}] [-v] [-V]

k8s_ephemeral_mimic - Inject ephemeral container with mirrored environment, volumes, etc!

options:
  -h, --help            show this help message and exit
  -i /path/to/pod.json, --input /path/to/pod.json
                        Filesystem path to input pod specification in JSON format (default:
                        stdin)
  -o /path/to/pod.json, --output /path/to/pod.json
                        Filesystem path to output pod specification patch in JSON format
                        (default: stdout)
  -c container-name, --container container-name
                        Name of container to mimic (required if pod contains multiple containers)
  -I example.com/image_name:latest, --image example.com/image_name:latest
                        Image to use in ephemeral container
  -e FOO=BAR, --env FOO=BAR
                        Additional environment variable to be set in container (may be used
                        multiple times)
  -E {securityContext,env,envFrom,volumeMounts}, --exclude {securityContext,env,envFrom,volumeMounts}
                        Exclude key from mirror of source container specification (may be used
                        multiple times)
  -r, --read-only-volumes
                        Force all volume mounts to use "read-only mode"
  -v, --verbose         Enable verbose debug logging
  -V, --version         Display script version

License: GPL-2.0-or-later, URL: https://github.com/menacit/k8s_ephemeral_mimic
```
