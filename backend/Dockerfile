FROM python:3.12-slim AS builder
WORKDIR /build
COPY backend/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim
LABEL org.opencontainers.image.authors="Ryan Vo <ryandtvo@gmail.com>"
LABEL org.opencontainers.image.title="lumen-studio-backend"

RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app
COPY backend/ .
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app

RUN mkdir -p /app/data && chown -R app:app /app
USER app

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)" || exit 1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]