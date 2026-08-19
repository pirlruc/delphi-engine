FROM python:3.13-slim-bookworm

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY contracts /app/contracts
COPY delphi /app/delphi
COPY daedalus /app/daedalus
COPY prometheus /app/prometheus
COPY scripts /app/scripts

WORKDIR /app/delphi
RUN uv sync --frozen --no-dev \
    && uv pip install --python .venv/bin/python -e /app/daedalus -e /app/prometheus

ENV PATH="/app/delphi/.venv/bin:${PATH}"
WORKDIR /app
EXPOSE 8000
CMD ["python", "scripts/serve_prototype.py", "--host", "0.0.0.0", "--port", "8000"]
