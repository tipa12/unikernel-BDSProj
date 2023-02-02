FROM gcr.io/bdspro/test-bench-dependencies:latest

#copy rest
COPY ./sink/* /app/
COPY ./common /app/common

CMD ["python", "main.py"]