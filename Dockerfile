FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends pandoc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY md_to_epub.py style.css ./

WORKDIR /data

ENTRYPOINT ["python", "/app/md_to_epub.py"]
