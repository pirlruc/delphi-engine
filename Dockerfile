FROM python:3.13-slim-bookworm@sha256:a5a7017efc5969e00ae2b91c8eb0631049a569652aa4ffc4501769049ae45c72

RUN pip install --no-cache-dir uv==0.13.4 \
    && useradd --uid 10001 --create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --chown=10001:10001 pyproject.toml uv.lock /app/
COPY --chown=10001:10001 contracts /app/contracts
COPY --chown=10001:10001 delphi /app/delphi
COPY --chown=10001:10001 daedalus /app/daedalus
COPY --chown=10001:10001 prometheus /app/prometheus
COPY --chown=10001:10001 epimetheus /app/epimetheus
COPY --chown=10001:10001 hermes /app/hermes
COPY --chown=10001:10001 scripts /app/scripts

RUN uv sync --frozen --no-dev --no-editable \
    --package delphi \
    --package daedalus \
    --package delphi-prometheus \
    && rm -rf /root/.cache \
    && chown -R 10001:10001 /app
USER 10001

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["python", "scripts/serve_prototype.py", "--host", "0.0.0.0", "--port", "8000"]
