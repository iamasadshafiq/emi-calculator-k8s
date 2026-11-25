# Loan EMI Calculator on Kubernetes (Minikube)

DS-584 Cloud Computing, Fall 2026 - Assignment 4
Asad Shafiq (MSDSF26A005), FCIT, University of the Punjab

A Loan EMI calculator (Flask + jQuery + Bootstrap) that saves every calculation in MongoDB.
The web application runs as a Deployment behind a ClusterIP Service and the NGINX Ingress,
MongoDB runs as a 3-member replica set (StatefulSet with one PVC per pod), and a
HorizontalPodAutoscaler scales the web pods on CPU.

```
httperf / browser --> Ingress (emi.local) --> Service emi-web --> emi-web pods (Deployment, HPA 1-5)
                                                                       |
                                                    MONGO_URL: mongo-0, mongo-1, mongo-2 (StatefulSet, rs0)
```

## Repository layout

| Folder | Content |
|---|---|
| `app/` | Flask application, `Dockerfile`, `.dockerignore` |
| `k8s/` | all Kubernetes manifests (namespace, MongoDB, web application, Ingress, HPA) |
| `scripts/` | build, request loops, httperf workload and runs, profiler, experiment and plotting scripts |
| `results/` | raw outputs of all tests (httperf reports, CSV files, logs, graphs) |

## Application

| Endpoint | Description |
|---|---|
| `GET /` | page with the form, the result panel and the history table (AJAX, no postback) |
| `POST /api/emi` | body `{"principal": P, "rate": annual %, "months": n}`; returns EMI, total payment, total interest, `servedBy` (pod name from `HOSTNAME`) and `podIP` |
| `GET /api/history` | last 10 calculations from MongoDB, newest first |
| `GET /health` | 200 only when MongoDB answers a ping (used by the readiness and liveness probes) |

The connection string is read from the `MONGO_URL` environment variable. Calculations are stored in the
collection `calculations` with the fields `principal`, `rate`, `months`, `emi`, `servedBy`, `createdAt`.

Local test without Kubernetes:

```bash
docker build -t emi-web:1.0 app/
docker network create emi-local
docker run -d --name mongo-local --network emi-local mongo:7.0
docker run -d --name emi-local --network emi-local -p 8080:8080 \
       -e MONGO_URL=mongodb://mongo-local:27017/emidb emi-web:1.0
# open http://localhost:8080
```

## Bring up the whole system on a fresh Minikube cluster

Tested with Minikube v1.39.0 (Docker driver), Kubernetes v1.37.0 on Ubuntu 24.04.

```bash
# 1. cluster and addons (port 80 of the node is published so the Ingress is reachable from other machines)
minikube start --driver=docker --cpus=4 --memory=2700 --ports=80:80
minikube addons enable ingress
minikube addons enable metrics-server

# 2. web image: build it and copy it into the Minikube node
./scripts/build_and_load.sh 1.0          # docker build + minikube image load emi-web:1.0

# 3. everything else
kubectl apply -f k8s/
kubectl rollout status statefulset/mongo -n emi
kubectl wait --for=condition=complete job/mongo-init -n emi --timeout=300s
kubectl rollout status deployment/emi-web -n emi
kubectl get all,pvc,configmap -n emi -o wide

# 4. name resolution for the Ingress host
echo "$(minikube ip) emi.local" | sudo tee -a /etc/hosts
curl http://emi.local/health
```

`kubectl apply -f k8s/` creates, in this order: the namespace `emi`, the headless Service and the
StatefulSet `mongo` (3 pods, 1 Gi PVC each), the Job `mongo-init` (waits for the three pods and calls
`rs.initiate()`), the ConfigMap with `MONGO_URL`, the Deployment `emi-web` (3 replicas), its ClusterIP
Service, the Ingress for `emi.local` and the HorizontalPodAutoscaler (1 to 5 pods at 50 % CPU).
The web pods become Ready as soon as the replica set has a PRIMARY.

The HPA controls the number of web pods. For tests with a fixed number of replicas (Milestone 03 and the
fixed-replica runs of Milestone 04) remove it first with `kubectl delete -f k8s/08-hpa.yaml`.

Without the Ingress the application can be opened with
`kubectl port-forward svc/emi-web 8080:80 -n emi` and http://localhost:8080.

## Milestone 03 tests

```bash
./scripts/send_requests.sh 30 results/m3/lb_3replicas.log      # 30 POST requests, count per pod
kubectl scale deployment emi-web --replicas=5 -n emi
./scripts/request_loop.sh 60 > results/m3/loop.log &           # keeps sending requests, prints ok/failed
./scripts/rs_status.sh                                         # replica set members and states
./scripts/mongo_count.sh mongo-1                               # documents stored on one member

# rolling update and rollback
./scripts/build_and_load.sh 1.1
kubectl set image deployment/emi-web emi-web=emi-web:1.1 -n emi
kubectl rollout status deployment/emi-web -n emi
kubectl rollout undo deployment/emi-web -n emi
```

## Milestone 04 load tests

The load generator is httperf 0.9.0 on the Minikube host. It sends the requests to http://emi.local/
(the Ingress). Every request is a `POST /api/emi` with random valid inputs.

```bash
# metrics-server samples every 60 s by default; 15 s gives usable kubectl top / HPA values
kubectl -n kube-system patch deploy metrics-server --type=json   -p '[{"op":"replace","path":"/spec/template/spec/containers/0/args/4","value":"--metric-resolution=15s"}]'

# httperf busy-waits on one CPU core: run_httperf.sh pins it to CPU 3 (taskset),
# so the Minikube node is kept on CPUs 0-2 (the host has 4 CPUs)
docker update --cpuset-cpus=0-2 minikube

python3 scripts/gen_workload.py 1000 > scripts/workload.txt   # 1000 random POST sessions for httperf --wsesslog
./scripts/run_httperf.sh 50 60 out.txt                        # one run: 50 req/s for 60 s

kubectl delete -f k8s/08-hpa.yaml                  # fixed replicas: no HPA
./scripts/run_fixed_experiments.sh                 # 15 runs: 1, 2, 3 replicas x 10, 25, 50, 100, 200 req/s
python3 scripts/summarize_httperf.py               # results/fixed/summary.csv

kubectl apply -f k8s/08-hpa.yaml                   # HPA: 1-5 replicas, 50 % CPU
./scripts/run_autoscale_test.sh                    # 2 min @10, 5 min @100, 3 min @10 req/s

python3 scripts/plot_graphs.py                     # results/graphs/*.png  (needs matplotlib)
```

`scripts/profile.py` is started by both experiment scripts. It writes the host CPU every second
(`*_host_cpu.csv`) and `kubectl top pods -n emi` every 15 seconds (`*_pods.csv`), both with a timestamp column.

## Results folder

| Path | Content |
|---|---|
| `results/m3/` | per-request logs of the load-distribution, self-healing and rolling-update tests |
| `results/fixed/` | 15 httperf reports, profiler CSV files, `summary.csv` |
| `results/autoscale/` | `hpa.csv` (every 15 s), `phases.csv`, httperf reports, profiler CSV files, rescale events |
| `results/graphs/` | the three graphs of Milestone 04 |
