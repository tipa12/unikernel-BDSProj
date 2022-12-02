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
        opam

## Cleanup cached data we don't need anymore
RUN apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install MirageOS
RUN opam init --auto-setup --yes

RUN opam update -y
RUN opam install -y 'mirage>4' ocaml-lsp-server

RUN opam clean -a -c -s --logs

WORKDIR /usr/src/mirageos

ENTRYPOINT [ "/bin/bash", "-c", "eval $(opam env) && /bin/bash" ]
