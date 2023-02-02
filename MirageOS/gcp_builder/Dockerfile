# syntax=docker/dockerfile:1

FROM ubuntu:22.04

# Install necessary packages available from standard repos
RUN apt-get update -qq && export DEBIAN_FRONTEND=noninteractive && \
    apt-get install -y --no-install-recommends \
        # Software tools
        software-properties-common \
        build-essential \
        wget \
        curl \
        apt-utils \
        file \
        flex \
        bison \
        zip \
        unzip \
        uuid-runtime \
        openssh-client \
        gpg-agent \
        gnupg \
        ca-certificates \
        socat \
        rsync \
        git \
        python3 \
        python3-pip \
        neovim \
        nano \
        iproute2 \
        iputils-ping \
        net-tools \
        pkg-config \
        libseccomp-dev \
        opam \
        coreutils \
        dosfstools \
        mtools \
        fdisk \
        syslinux \
        syslinux-common \
        tar

# Install the gcloud command-line tool
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg  add -
RUN apt-get update && \
    apt-get install -y google-cloud-sdk

## Cleanup cached data we don't need anymore
RUN apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install MirageOS
RUN opam init --auto-setup --yes
RUN opam switch create 4.14.0
RUN opam update -y
RUN opam install -y 'mirage>4'

RUN opam clean -a -c -s --logs

WORKDIR /usr/src

COPY ./build.sh /sbin
COPY ./solo5-virtio-mkimage.sh /sbin

ENTRYPOINT [ "/bin/bash", "-c", "eval $(opam env) && /bin/bash" ]