FROM python:3.10-slim

# Set up a working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your environment code
COPY . .

# Expose the standard Hugging Face Space port
EXPOSE 7860

# Start the web server for the validator ping
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]