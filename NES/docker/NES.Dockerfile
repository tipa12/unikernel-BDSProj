# The base image is the NES executable image to run the coordinator and a worker.
FROM nebulastream/nes-executable-image:latest

ARG CONFIG_FILE
ARG EXECUTABLE
ENV EXECUTABLE=$EXECUTABLE
COPY config/$CONFIG_FILE config.yaml

ENTRYPOINT ["bash", "-c", "$EXECUTABLE --configPath=config.yaml"]