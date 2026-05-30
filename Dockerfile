FROM python:3.11-slim AS builder
WORKDIR /app
RUN pip install uv --no-cache-dir
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project

FROM python:3.11-slim AS runtime
WORKDIR /app
COPY --from=builder /app/.venv .venv
COPY . .
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
