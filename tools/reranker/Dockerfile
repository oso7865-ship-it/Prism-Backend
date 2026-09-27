FROM python:3.12-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f
WORKDIR /opt/reranker
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY manifest.json download_model.py ./
RUN python download_model.py
COPY service.py ./
USER 65534:65534
EXPOSE 8091
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8091/health',timeout=2)"
CMD ["python", "service.py"]
