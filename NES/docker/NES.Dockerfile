# The base image is the NES executable image to run the coordinator and a worker.
FROM us-docker.pkg.dev/bdspro/us.gcr.io/nes-executable-image:timestamps

RUN apt-get update && apt-get install -y apt-transport-https ca-certificates gnupg curl
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
    | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg \
    | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
RUN apt-get update && apt-get install google-cloud-cli

ARG CONFIG_FILE
ARG EXECUTABLE
ENV EXECUTABLE=$EXECUTABLE
COPY config/$CONFIG_FILE config.yaml

ENTRYPOINT ["bash", "-c", "$EXECUTABLE --configPath=config.yaml"]