ARG BUILD_FROM=python:3.11-slim
FROM ${BUILD_FROM}

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Make run script executable
RUN chmod a+x run.sh

# Run the application
CMD ["./run.sh"]

