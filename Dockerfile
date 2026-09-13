FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app
# uv.lock коммитится и ставится через --frozen: без него `uv sync` резолвил
# зависимости заново на каждой сборке и образ зависел от даты сборки, а не от
# содержимого репо. Так mcp 2.0.0 (28.07.2026) и сломал соседний сервер.
# README.md и LICENSE тут не для красоты: pyproject объявляет их в readme и
# license-files, и без них сборка проекта падает на
# "OSError: Readme file does not exist".
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --frozen --no-dev

COPY src/ src/
RUN uv sync --frozen --no-dev

# Реестр MCP проверяет владение образом по этому имени: оно обязано совпадать
# с полем name в server.json, иначе публикация отклоняется.
LABEL io.modelcontextprotocol.server.name="io.github.badigit/beget-mcp"

ENV MCP_TRANSPORT=sse
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8322
ENV PYTHONUNBUFFERED=1

EXPOSE 8322

ENTRYPOINT ["/app/.venv/bin/beget-mcp"]
