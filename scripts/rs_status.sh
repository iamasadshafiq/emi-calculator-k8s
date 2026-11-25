#!/bin/bash
# Prints the members of replica set rs0 and their states (trimmed rs.status()).
# usage: ./scripts/rs_status.sh [pod]          (default mongo-0)
POD=${1:-mongo-0}
kubectl exec -n emi "$POD" -- mongosh --quiet --eval '
  rs.status().members.forEach(m => print(m.name, m.stateStr, "health=" + m.health));'
