FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
# We need to enable non-free repositories to get the unrar-nonfree package
RUN sed -i -r 's/Components: main/Components: main non-free non-free-firmware/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    par2 \
    unrar \
    rar \
    p7zip-full \
    rclone \
    curl \
    procps \
    genisoimage \
    mediainfo \
    ffmpeg \
    ca-certificates \
    git \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Go
RUN curl -L -o go.tar.gz https://go.dev/dl/go1.22.0.linux-amd64.tar.gz && \
    rm -rf /usr/local/go && \
    tar -C /usr/local -xzf go.tar.gz && \
    rm go.tar.gz
ENV PATH=$PATH:/usr/local/go/bin

# Install Bento4
RUN curl -L -o bento4.zip https://www.bok.net/Bento4/binaries/Bento4-SDK-1-6-0-641.x86_64-unknown-linux.zip && \
    mkdir -p /usr/local/bento4 && \
    unzip bento4.zip -d /usr/local/bento4 && \
    mv /usr/local/bento4/Bento4-SDK-1-6-0-641.x86_64-unknown-linux/* /usr/local/bento4/ && \
    rm -rf /usr/local/bento4/Bento4-SDK-1-6-0-641.x86_64-unknown-linux bento4.zip
ENV PATH=$PATH:/usr/local/bento4/bin

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 5000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/ || exit 1

# Run the application
CMD ["python", "app.py"]
