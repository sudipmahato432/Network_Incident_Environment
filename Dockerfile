FROM python:3.10-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy EVERYTHING into the container
COPY . .

# Install the project and dependencies
RUN uv pip install --system .

# Expose the standard port
EXPOSE 7860

# Run the app from the subfolder
# We use server.app because it's now a package
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]