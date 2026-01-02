ARG BUILD_FROM
FROM $BUILD_FROM

# Install dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy add-on files
COPY run.sh /app/
COPY monitor.py /app/
RUN chmod +x /app/run.sh /app/monitor.py

# Set working directory
WORKDIR /app

# Start the add-on
CMD ["/app/run.sh"]

