#!/bin/sh

gsutil cp "gs://unikraft/$1" unikraft > /dev/null

NAME="unikraft-$(date +%s)"

solo5-virtio-mkimage.sh -f tar -- "$NAME.tar.gz" unikraft

gsutil cp "$NAME.tar.gz" "gs://unikraft/$NAME.tar.gz" > /dev/null

gcloud compute images --project "${PROJECT_ID:-bdspro}" create "$NAME" --family=unikraft --source-uri "gs://unikraft/$NAME.tar.gz" > /dev/null

echo "$NAME"