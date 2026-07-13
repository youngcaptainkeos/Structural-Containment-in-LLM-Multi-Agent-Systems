FROM python:3.12-slim

# Install Java Runtime for TLA+
RUN apt-get update && \
    apt-get install -y default-jre && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r langgraph-fvs-test/requirements.txt

CMD ["python", "langgraph-fvs-test/experiment_runner.py"]