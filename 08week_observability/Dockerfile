FROM ghcr.io/astral-sh/uv:python3.14-bookworm

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync

COPY . .
CMD ["uv", "run", "fastapi", "run", "src/app.py"]