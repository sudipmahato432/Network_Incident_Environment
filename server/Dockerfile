FROM python:3.10-slim
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy EVERYTHING from the root (parent of server/)
COPY . .

# Install the project and dependencies
RUN uv pip install --system .

EXPOSE 7860

# Run the server using the entry point
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]