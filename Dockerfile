FROM python:3.12-slim

# nmap needed for network scanning (A3)
RUN apt-get update && apt-get install -y \
    nmap \
    openssh-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Reports land here — mount a volume to persist them
RUN mkdir -p /app/reports

ENTRYPOINT ["python", "agent.py"]
