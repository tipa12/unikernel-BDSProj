gcloud compute ssh --zone us-east1-b coordinator --command "docker logs -f \$(docker ps | grep bdspro | awk '{print \$1}')" &
gcloud compute ssh --zone us-east4-b worker --command "docker logs -f \$(docker ps | grep bdspro | awk '{print \$1}')" &
gcloud compute ssh --zone us-east1-b tuple-source --command "docker logs -f \$(docker ps | grep bdspro | awk '{print \$1}')"
