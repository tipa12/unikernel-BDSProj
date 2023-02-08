#!/bin/bash
set -x
set -e # Abort on failure

function finish {
  echo "Deleting instance"
  gcloud compute instances delete --zone "$ZONE" --project "${PROJECT_ID:-bdspro}" "$HOSTNAME"
}

trap finish EXIT

# Set default values for the arguments
NAME=""
REPLACE=true
CONFIGURE_ARGS=""
PROJECT_ID="bdspro"

# Check if the required arguments are provided
if [ "$#" -lt 1 ]; then
  echo "Usage: $0 IMAGE_NAME GITHUB_TOKEN [CONFIGURE_ARGS]"
  exit 1
fi

NAME=$1
shift

GITHUB_TOKEN=$1
shift

if [ "$#" -gt 1 ]; then
  CONFIGURE_ARGS=$@
fi

# Generate a URL-friendly unique identifier
UNIQUE_ID=$(
  date +%s | sha256sum | base64 | head -c 32
  echo
)

WORKDIR=$(pwd)/scripts/workdir
export UK_WORKDIR=$WORKDIR

PROJECT_DIR=$(mktemp -d)
echo "Cloning repository..."
(cd "$PROJECT_DIR" && git clone https://oauth2:${GITHUB_TOKEN}@github.com/tipa12/unikernel-BDSProj.git)

WORKDIR=$WORKDIR/apps/unikernel
cp -r "$PROJECT_DIR/unikernel-BDSProj/unikraft/unikernel/" "$WORKDIR"

if [ -n "$CONFIGURE_ARGS" ]; then
  echo "Configuring Unikraft application..." "${CONFIGURE_ARGS}"
  (cd "$WORKDIR" && kraft configure ${CONFIGURE_ARGS}) >/dev/null
else
  echo "Configuring Unikraft application..."
  (cd "$WORKDIR" && kraft configure -F -m x86_64 -p kvm) >/dev/null
fi

echo "Building Unikernel"
(cd "$WORKDIR" && kraft prepare && kraft build -j 2) >/dev/null

echo "Building Building Image"
solo5-virtio-mkimage.sh -f tar -- unikraft.tar.gz "${WORKDIR}/build/testoperator_kvm-x86_64"

echo "Uploading image to Google Cloud Storage..."
gsutil cp unikraft.tar.gz "gs://unikraft/unikraft-${UNIQUE_ID}.tar.gz"

if [ -z "$REPLACE" ]; then
  echo "Creating image on Google Compute Engine..."
  gcloud compute images --project "${PROJECT_ID:-bdspro}" --family=unikraft -q create "$NAME" --source-uri "gs://unikraft/unikraft-${UNIQUE_ID}.tar.gz"
else
  gcloud compute images --project "${PROJECT_ID:-bdspro}" --family=unikraft --force-create -q create "$NAME" --source-uri "gs://unikraft/unikraft-${UNIQUE_ID}.tar.gz"
fi

echo "Done."
