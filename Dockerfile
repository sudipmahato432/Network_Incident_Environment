FROM python:3.10-slim

WORKDIR /app

# Install uv correctly from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy all project files into the container
COPY . .

# Install dependencies using the uv.lock file
# This ensures the environment is exactly what you tested locally
RUN uv sync --frozen

# Expose the app port (Hugging Face / OpenEnv standard)
EXPOSE 7860

# Run the server using the entry point defined in pyproject.toml
# This maps to app:main
CMD ["uv", "run", "server"]