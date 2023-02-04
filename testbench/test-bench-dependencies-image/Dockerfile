FROM python:3.9

# copy requirements
COPY ./test-bench-dependencies-image/requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ENV PYTHONPATH=/app

COPY ./__init__.py /app/testbench/
COPY ./main.py /app/testbench/
COPY ./common /app/testbench/common/