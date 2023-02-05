FROM europe-docker.pkg.dev/bdspro/eu.gcr.io/test-bench-dependencies:latest

# Install Docker

RUN apt-get update && apt-get install --yes \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

RUN mkdir -p /etc/apt/keyrings && curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

RUN echo \
  "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  focal stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

RUN apt-get update && apt-get install --yes docker-ce docker-ce-cli

COPY ./* /app/testbench/control/

CMD ["python", "testbench/control/main.py"]