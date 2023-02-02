FROM gcr.io/bdspro/test-bench-dependencies:latest

#copy rest
COPY ./flask-api/* /app/
COPY ./common /app/common

CMD ["python", "main.py"]