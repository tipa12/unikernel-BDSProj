#!/bin/bash
set -x
set -e # Abort on failure

function finish {
  echo "Deleting instance"
  gcloud compute instances delete --zone "$ZONE" --project "$PROJECT_ID" "$HOSTNAME"
}

trap finish EXIT

# Set default values for the arguments
NAME=""
REPLACE=false
CONFIGURE_ARGS=""
GITHUB_TOKEN=""

# Parse the command-line arguments using getopts
while getopts ":u" opt; do
    case $opt in
        u)
            REPLACE=true
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            exit 1
            ;;
    esac
done
shift $((OPTIND-1))

# Check if the required arguments are provided
if [ "$#" -lt 2 ]; then
    echo "Usage: $0 IMAGE_NAME GITHUB_TOKEN [-u] [CONFIGURE_ARGS]"
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
UNIQUE_ID=$(date +%s | sha256sum | base64 | head -c 32 ; echo)

PROJECT_DIR=$(pwd)

echo "Cloning repository..."
(cd $PROJECT_DIR && git clone https://oauth2:${GITHUB_TOKEN}@github.com/tipa12/unikernel-BDSProj.git)

WORKDIR=$PROJECT_DIR/unikernel-BDSProj/MirageOS/unikernel

if [ -n "$CONFIGURE_ARGS" ]; then
  echo "Configuring MirageOS application... $CONFIGURE_ARGS"
  (cd $WORKDIR && mirage configure $CONFIGURE_ARGS) > /dev/null
else
  echo "Configuring MirageOS application..."
  (cd $WORKDIR && mirage configure -t unix) > /dev/null
fi

echo "Building Unikernel"
(cd $WORKDIR && make depends && make -j $(nproc)) > /dev/null

echo "Building Image"
solo5-virtio-mkimage.sh -f tar -- mirageos.tar.gz $WORKDIR/dist/unikernel.virtio

echo "Uploading image to Google Cloud Storage..."
gsutil cp mirageos.tar.gz gs://mirageos/mirageos-${UNIQUE_ID}.tar.gz

echo "Creating image on Google Compute Engine..."
if [ -z "$REPLACE" ]; then
  gcloud compute images -q create $NAME --source-uri gs://mirage/mirage-${UNIQUE_ID}.tar.gz --family mirageos
else
  gcloud compute images --force-create -q create $NAME --source-uri gs://mirage/mirage-${UNIQUE_ID}.tar.gz --family mirageos
fi

echo "Done."
