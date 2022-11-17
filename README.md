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

