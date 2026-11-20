FROM python:3.13-slim-bookworm

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock /app/
COPY contracts /app/contracts
COPY delphi /app/delphi
COPY daedalus /app/daedalus
COPY prometheus /app/prometheus
COPY epimetheus /app/epimetheus
COPY hermes /app/hermes
COPY scripts /app/scripts

RUN uv sync --frozen --no-dev --no-editable \
    --package delphi \
    --package daedalus \
    --package delphi-prometheus

ENV PATH="/app/.venv/bin:${PATH}"
EXPOSE 8000
CMD ["python", "scripts/serve_prototype.py", "--host", "0.0.0.0", "--port", "8000"]
