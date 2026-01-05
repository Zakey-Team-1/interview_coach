FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy project files
COPY . .

# Install crewai CLI
RUN pip install crewai

# Run crewai install
RUN crewai install

# Expose the port
EXPOSE 8080

# Run the application
CMD ["uv", "run", "serve"]
