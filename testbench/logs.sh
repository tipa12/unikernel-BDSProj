red() {
  tput setaf 1
  cat
  tput sgr0
}
green() {
  tput setaf 2
  cat
  tput sgr0
}
yellow() {
  tput setaf 3
  cat
  tput sgr0
}

gcloud compute ssh --zone europe-west3-a control --command "docker logs -f \$(docker ps | grep bdspro | awk '{print \$1}')" &
gcloud compute ssh --zone europe-west3-a source --command "docker logs -f \$(docker ps | grep bdspro | awk '{print \$1}')" &
gcloud compute ssh --zone europe-west3-a sink --command "docker logs -f \$(docker ps | grep bdspro | awk '{print \$1}')"
