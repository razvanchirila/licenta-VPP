FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app/backend

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY vpp_core ./vpp_core
COPY data ./data
COPY scripts ./scripts
COPY main.py .

RUN useradd --create-home --uid 10001 vpp
USER vpp

EXPOSE 8000
CMD ["python", "scripts/docker_start.py"]
