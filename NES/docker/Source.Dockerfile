FROM alpine:latest

RUN apk add --no-cache python3 python3-dev py-pip build-base linux-headers

WORKDIR /app

COPY source/tuple_source.py script.py

RUN pip3 install google-cloud-storage psutil

CMD ["python3", "script.py"]