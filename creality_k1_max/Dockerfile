ARG BUILD_FROM
FROM $BUILD_FROM

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache \
    bash \
    jq \
    curl \
    python3 \
    py3-pip

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Make run script executable
RUN chmod a+x run.sh

# Run the application
CMD ["./run.sh"]

