docker build -t us-docker.pkg.dev/bdspro/us.gcr.io/coordinator -f ./docker/NES.Dockerfile --build-arg CONFIG_FILE=coordinator.yml --build-arg EXECUTABLE=nesCoordinator . &
docker build -t us-docker.pkg.dev/bdspro/us.gcr.io/worker -f ./docker/NES.Dockerfile --build-arg CONFIG_FILE=worker.yml --build-arg EXECUTABLE=nesWorker . &
docker build -t us-docker.pkg.dev/bdspro/us.gcr.io/tuple-source -f ./docker/Source.Dockerfile . &
wait

docker push us-docker.pkg.dev/bdspro/us.gcr.io/coordinator &
docker push us-docker.pkg.dev/bdspro/us.gcr.io/worker &
docker push us-docker.pkg.dev/bdspro/us.gcr.io/tuple-source &
wait

if [ "$1" == "--reload" ]; then
  echo "Reload Instances."
  gcloud compute ssh --zone us-east1-b coordinator --command "sudo systemctl start konlet-startup" &
  gcloud compute ssh --zone us-east4-b worker --command "sleep 3 && sudo systemctl start konlet-startup" &
  gcloud compute ssh --zone us-east1-b tuple-source --command "sudo systemctl start konlet-startup" &
  wait
fi
