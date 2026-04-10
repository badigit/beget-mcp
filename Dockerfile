FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --frozen --no-dev || uv sync --no-dev

COPY src/ src/

ENV MCP_TRANSPORT=sse
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8322

EXPOSE 8322

CMD ["uv", "run", "python", "-m", "mcp_beget.server"]
