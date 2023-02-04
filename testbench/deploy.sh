#!/bin/bash

if [ "$1" == "--build-common" ]; then
  shift
  docker build -t europe-docker.pkg.dev/bdspro/eu.gcr.io/test-bench-dependencies -f ./testbench/test-bench-dependencies-image/Dockerfile ./testbench && docker push europe-docker.pkg.dev/bdspro/eu.gcr.io/test-bench-dependencies
fi

if [ "$1" == "--fast" ]; then
  echo "Fast mode selected."
  docker build -t europe-docker.pkg.dev/bdspro/eu.gcr.io/source-instance -f ./testbench/source/Dockerfile ./testbench/source && docker push europe-docker.pkg.dev/bdspro/eu.gcr.io/source-instance && gcloud compute ssh --zone europe-west3-a source --command "sudo systemctl start konlet-startup" &
  docker build -t europe-docker.pkg.dev/bdspro/eu.gcr.io/control-instance -f ./testbench/control/Dockerfile ./testbench/control && docker push europe-docker.pkg.dev/bdspro/eu.gcr.io/control-instance && gcloud compute ssh --zone europe-west3-a control --command "sudo systemctl start konlet-startup" &
  docker build -t europe-docker.pkg.dev/bdspro/eu.gcr.io/sink-instance -f ./testbench/sink/Dockerfile ./testbench/sink && docker push europe-docker.pkg.dev/bdspro/eu.gcr.io/sink-instance && gcloud compute ssh --zone europe-west3-a sink --command "sudo systemctl start konlet-startup" &
  docker build -t europe-docker.pkg.dev/bdspro/eu.gcr.io/flask-api-instance -f ./testbench/flask-api/Dockerfile ./testbench/flask-api && docker push europe-docker.pkg.dev/bdspro/eu.gcr.io/flask-api-instance && gcloud compute ssh --zone europe-west3-a flask-api --command "sudo systemctl start konlet-startup" &
else
  echo "Regular mode selected."
  gcloud builds submit --config=testbench/source/cloudbuild.yaml &
  gcloud builds submit --config=testbench/sink/cloudbuild.yaml &
  gcloud builds submit --config=testbench/control/cloudbuild.yaml &
  gcloud builds submit --config=testbench/flask-api/cloudbuild.yaml &
fi

wait
echo "Deployed to GCP"


