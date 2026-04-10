FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --no-dev

COPY src/ src/
RUN uv sync --no-dev

ENV MCP_TRANSPORT=sse
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8322
ENV PYTHONUNBUFFERED=1

EXPOSE 8322

ENTRYPOINT ["/app/.venv/bin/beget-mcp"]
