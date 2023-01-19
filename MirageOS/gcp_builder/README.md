# GCP Builder

## Setup

1. Build the Docker image `docker build -t bdspro-mirage-gcp .`
2. Call the build script `/sbin/build.sh <name> <token> <args>` where `<token>` is your GitHub access token and `<args>` are the MirageOS build arguments (e.g. `-t virtio --op=map`)
