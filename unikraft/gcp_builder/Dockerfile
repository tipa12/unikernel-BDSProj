# syntax=docker/dockerfile:1

FROM ubuntu:22.04

ARG GITHUB_TOKEN
ENV UK_KRAFT_GITHUB_TOKEN=${GITHUB_TOKEN}

# Install necessary packages available from standard repos
RUN apt-get update -qq && export DEBIAN_FRONTEND=noninteractive && \
    apt-get install -y --no-install-recommends \
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
        libncurses-dev \
        libyaml-dev \
        coreutils \
        dosfstools \
        mtools \
        fdisk \
        syslinux \
        syslinux-common \
        tar

# Note(Florian): I needed to define this on Windows but it might not be necessary on your machine.
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# Install Kraft
RUN pip3 install --upgrade \
        pip \
        requests \
        setuptools
RUN pip3 install --root-user-action=ignore git+https://github.com/unikraft/kraft.git

RUN kraft list update

RUN git config --global user.email "you@example.com" && git config --global user.name "Your Name"
WORKDIR /app

# Install the gcloud command-line tool
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg  add -
RUN apt-get update && \
    apt-get install -y google-cloud-sdk


RUN git clone https://github.com/ls-1801/unikraft-scripts.git scripts \
    && cd scripts/nolibc/ && ./do-httpreply setup

RUN rm -rf scripts/workdir/apps/app-httpreply

COPY ./build_unikraft.sh /sbin
COPY ./solo5-virtio-mkimage.sh /sbin

ENTRYPOINT ["/sbin/build_unikraft.sh"]

CMD ["unikraft"]