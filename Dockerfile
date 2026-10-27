FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app:/app/as-v3-reference GMF_ENV=production GMF_AUTH_MODE=password GMF_DATA_DIR=/var/data/gmf
RUN apt-get update && apt-get install -y --no-install-recommends libreoffice-writer tesseract-ocr tesseract-ocr-eng tesseract-ocr-chi-sim fonts-noto-cjk fonts-dejavu-core gosu && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt requirements-dev.txt ./
COPY as-v3-reference/requirements.txt as-v3-reference/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend backend
COPY as-v3-reference/gmf_v3 as-v3-reference/gmf_v3
COPY dist/data/course.json dist/data/course.json
COPY deploy/entrypoint.sh /entrypoint.sh
RUN groupadd --gid 10001 gmf && useradd --uid 10001 --gid 10001 --create-home gmf && chmod 755 /entrypoint.sh
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
