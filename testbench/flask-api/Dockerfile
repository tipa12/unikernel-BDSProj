FROM europe-docker.pkg.dev/bdspro/eu.gcr.io/test-bench-dependencies:latest

COPY ./main.py /app/testbench/flaskapi/main.py

ENV PYTHONPATH="/app/testbench/flaskapi:$PYTHONPATH"
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:80", "testbench.flaskapi.main:app"]