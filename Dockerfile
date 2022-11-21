# syntax=docker/dockerfile:1

FROM ubuntu:22.04

ARG GITHUB_TOKEN
ENV UK_KRAFT_GITHUB_TOKEN=${GITHUB_TOKEN}

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
        # Libraries
        libncurses-dev \
        libyaml-dev

# Note(Florian): I needed to define this on Windows but it might not be necessary on your machine.
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# Install Kraft
RUN pip3 install --upgrade \
        pip \
        requests \
        setuptools

RUN pip3 install git+https://github.com/unikraft/kraft.git

# Install Kraftkit
# RUN curl --proto '=https' --tlsv1.2 -sSf https://get.kraftkit.sh | sh

## Cleanup cached apt data we don't need anymore
RUN apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/unikraft

RUN kraft list update
# For Kraftkit do this instead:
# RUN kraft pkg update

# Build app-helloworld as environment sanity check
# RUN kraft up -t helloworld -p linuxu -m x86_64 apps/app-helloworld
# For Kraftkit do this instead:
# RUN kraft pkg pull -p linuxu -m x86_64 -w apps/app-helloworld github.com/unikraft/app-helloworld.git

RUN git clone https://github.com/unikraft-upb/scripts

ENTRYPOINT [ "/bin/bash" ]
