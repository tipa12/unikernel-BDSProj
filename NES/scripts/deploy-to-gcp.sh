gcloud compute instances delete coordinator --project=bdspro --zone=us-east1-b --quiet || true &
gcloud compute instances delete tuple-source --project=bdspro --zone=us-east1-b --quiet || true &
gcloud compute instances delete worker --project=bdspro --zone=us-east4-b --quiet || true &
wait

gcloud compute instances create-with-container coordinator \
  --project=bdspro \
  --zone=us-east1-b \
  --machine-type=e2-standard-2 \
  --tags=http-server \
  --service-account=152414602910-compute@developer.gserviceaccount.com \
  --scopes=https://www.googleapis.com/auth/datastore,https://www.googleapis.com/auth/devstorage.full_control,https://www.googleapis.com/auth/servicecontrol,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/trace.append,https://www.googleapis.com/auth/devstorage.read_only \
  --container-image us-docker.pkg.dev/bdspro/us.gcr.io/coordinator --network-interface=address=34.74.134.64,private-network-ip=10.142.0.32,subnet=default &
gcloud compute instances create-with-container worker \
  --project=bdspro \
  --zone=us-east4-b \
  --machine-type=e2-standard-2 \
  --service-account=152414602910-compute@developer.gserviceaccount.com \
  --scopes=https://www.googleapis.com/auth/servicecontrol,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/trace.append,https://www.googleapis.com/auth/devstorage.read_only \
  --container-image us-docker.pkg.dev/bdspro/us.gcr.io/worker --network-interface=private-network-ip=10.150.0.34,subnet=default &
gcloud compute instances create-with-container tuple-source \
  --project=bdspro \
  --zone=us-east1-b \
  --machine-type=e2-medium \
  --service-account=152414602910-compute@developer.gserviceaccount.com \
  --scopes=https://www.googleapis.com/auth/datastore,https://www.googleapis.com/auth/devstorage.full_control,https://www.googleapis.com/auth/servicecontrol,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/trace.append,https://www.googleapis.com/auth/devstorage.read_only \
  --container-image us-docker.pkg.dev/bdspro/us.gcr.io/tuple-source --network-interface=private-network-ip=10.142.0.36,subnet=default &
wait
