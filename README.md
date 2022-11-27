# HTTP reply on Unikraft

Based on the Httpreply example App.

The build process uses the [Scripts](https://github.com/unikraft-upb/scripts)

1. Clone the Script repository
2. cd into the musl folder
3. `./do-httpreply setup` will install the required Unikraft dependencies within the scripts repository
5. checkout this branch into the scripts/workdir/apps folder
4. change the app directory within the do-httpreply script to `"$top"/apps/tcp-echo` or whatever name you chose for the repository
5. from the musl folder, run `./do-httpreply build` to build the image
6. run `./do-httpreply run` to start the unikernel. This will also create the necessary networking
7. test the unikernel with `echo "PING" | nc 172.44.0.2 8123`

## Setup

Build the image: `docker build --build-arg GITHUB_TOKEN=<token> -t bdspro .`

Run the image: `docker run -it --rm bdspro`

Run the image with this directory mounted: `docker run -it --rm -v $(pwd)/app-bdspro:/usr/src/unikraft/apps/app-bdspro bdspro`

Build the unikernel using Kraftkit:

   1. Navigate to the unikernel source directory
   2. Build the application: `kraft build`
   3. Run the application: `kraft run`
