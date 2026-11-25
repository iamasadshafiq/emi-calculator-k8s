#!/bin/bash
# Prints how many documents one replica set member has in emidb.calculations.
# usage: ./scripts/mongo_count.sh [pod]        (default mongo-0)
POD=${1:-mongo-0}
kubectl exec -n emi "$POD" -- mongosh emidb --quiet --eval '
  db.getMongo().setReadPref("secondaryPreferred");
  print(db.hello().me, "documents in calculations:", db.calculations.countDocuments());'
