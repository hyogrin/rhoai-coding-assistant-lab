FROM registry.access.redhat.com/ubi9/python-311:latest

USER 0
RUN dnf install -y nodejs && dnf clean all
USER 1001

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

ENV SANDBOX_WORKSPACE=/tmp/sandbox-workspace
ENV SANDBOX_TIMEOUT=30

CMD ["python3", "server.py"]
