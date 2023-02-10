# syntax=docker/dockerfile:1
FROM bdspro
USER root
# Install the gcloud command-line tool
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg  add -
RUN apt-get update && \
    apt-get install -y google-cloud-sdk

USER appuser
WORKDIR /home/appuser
RUN rm -rf scripts/workdir/apps/app-httpreply

COPY ./build_unikraft.sh /sbin

ENTRYPOINT ["/sbin/build_unikraft.sh"]