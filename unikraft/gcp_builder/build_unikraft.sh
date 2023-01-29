#!/bin/bash

set -e # Abort on failure

# Set default values for the arguments
NAME=""
REPLACE=false
REVISION=""
CONFIGURE_ARGS=""

# Parse the command-line arguments using getopts
while getopts ":r:u" opt; do
    case $opt in
        r)
            REVISION=$OPTARG
            ;;
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
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 IMAGE_NAME [-r REVISION] [-u] [CONFIGURE_ARGS]"
    exit 1
fi

NAME=$1

shift

if [ "$#" -gt 1 ]; then
  CONFIGURE_ARGS=$@
fi

# Generate a URL-friendly unique identifier
UNIQUE_ID=$(date +%s | sha256sum | base64 | head -c 32 ; echo)

echo "Cloning repository..."
git clone https://github.com/ls-1801/Unikraft-Test-Operator.git scripts/workdir/apps/app-httpreply

# Checkout the specified revision if provided
if [ -n "$REVISION" ]; then
    echo "Checking out revision $REVISION..."
    (cd scripts/workdir/apps/app-httpreply && git checkout $REVISION) > /dev/null
fi

export UK_WORKDIR=$(pwd)/scripts/workdir
if [ -n "$CONFIGURE_ARGS" ]; then
  echo "Configuring Unikraft application... $CONFIGURE_ARGS"
  (cd scripts/workdir/apps/app-httpreply && kraft configure $CONFIGURE_ARGS) > /dev/null
else
  echo "Configuring Unikraft application..."
  (cd scripts/workdir/apps/app-httpreply && kraft configure -F -m x86_64 -p kvm) > /dev/null
fi

echo "Building Unikernel"
(cd scripts/workdir/apps/app-httpreply && kraft prepare && kraft build -j 2) > /dev/null

echo "Building Building Image"
solo5-virtio-mkimage.sh -f tar -- unikraft.tar.gz scripts/workdir/apps/app-httpreply/build/testoperator_kvm-x86_64

echo "Uploading image to Google Cloud Storage..."
gsutil cp unikraft.tar.gz gs://unikraft/unikraft-${UNIQUE_ID}.tar.gz
echo "Creating image on Google Compute Engine..."
gcloud compute images -q create $NAME --source-uri gs://unikraft/unikraft-${UNIQUE_ID}.tar.gz

echo "Done."