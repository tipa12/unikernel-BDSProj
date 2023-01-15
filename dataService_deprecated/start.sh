#!/bin/bash

# Update package manager and install packages
sudo apt update -y
sudo apt install -y python3-pip
pip3 install -r requirements.txt
gunicorn -w 4 -b 0.0.0.0:8000 main:app