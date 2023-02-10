#!/bin/bash
set -e # Abort on failure

# Set default values for the arguments
CONFIGURE_ARGS=""

# Check if the required arguments are provided
if [ "$#" -lt 1 ]; then
  echo "Usage: $0 GITHUB_TOKEN [CONFIGURE_ARGS]"
  exit 1
fi

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
(cd "$PROJECT_DIR" && git clone https://oauth2:${GITHUB_TOKEN}@github.com/tipa12/unikernel-BDSProj.git)

WORKDIR=$WORKDIR/apps/unikernel
cp -r "$PROJECT_DIR/unikernel-BDSProj/unikraft/unikernel/" "$WORKDIR"

if [ -n "$CONFIGURE_ARGS" ]; then
  (cd "$WORKDIR" && kraft configure ${CONFIGURE_ARGS}) >/dev/null
else
  (cd "$WORKDIR" && kraft configure -F -m x86_64 -p kvm) >/dev/null
fi

(cd "$WORKDIR" && kraft prepare && kraft build -j 2) >/dev/null

gsutil cp "${WORKDIR}/build/testoperator_kvm-x86_64" "gs://unikraft/unikraft_kvm-x86_64_${UNIQUE_ID}" > /dev/null

echo "unikraft_kvm-x86_64_${UNIQUE_ID}"
