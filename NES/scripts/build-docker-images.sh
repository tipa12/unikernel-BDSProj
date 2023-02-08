docker build -t us-docker.pkg.dev/bdspro/us.gcr.io/coordinator -f ./docker/NES.Dockerfile --build-arg CONFIG_FILE=coordinator.yml --build-arg EXECUTABLE=nesCoordinator . &
docker build -t us-docker.pkg.dev/bdspro/us.gcr.io/worker -f ./docker/NES.Dockerfile --build-arg CONFIG_FILE=worker.yml --build-arg EXECUTABLE=nesWorker . &
docker build -t us-docker.pkg.dev/bdspro/us.gcr.io/mqtt -f ./docker/MOSQUITTO.Dockerfile . &
wait

docker push us-docker.pkg.dev/bdspro/us.gcr.io/coordinator &
docker push us-docker.pkg.dev/bdspro/us.gcr.io/worker &
docker push us-docker.pkg.dev/bdspro/us.gcr.io/mqtt &
wait

if [ "$1" == "--reload" ]; then
  echo "Reload Instances."
  gcloud compute ssh --zone us-east1-b coordinator --command "sudo systemctl start konlet-startup" &
  gcloud compute ssh --zone us-east1-b worker --command "sudo systemctl start konlet-startup" &
  gcloud compute ssh --zone us-east1-b mqtt --command "sudo systemctl start konlet-startup" &
  wait
fi
