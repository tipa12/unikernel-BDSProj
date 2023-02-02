FROM gcr.io/bdspro/test-bench-dependencies:latest

#copy rest
COPY ./control/* /app/
COPY ./common /app/common

CMD ["python", "main.py"]