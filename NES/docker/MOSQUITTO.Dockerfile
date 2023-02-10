# The base image is the NES executable image to run the coordinator and a worker.
FROM eclipse-mosquitto

COPY mosquitto.conf /mosquitto/config
