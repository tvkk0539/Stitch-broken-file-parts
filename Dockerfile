# Stage 1: Build static MP4Box (GPAC)
FROM python:3.11-slim AS gpac-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    git \
    zlib1g-dev \
    ca-certificates \
    cmake

WORKDIR /src/gpac
RUN git clone --depth 1 https://github.com/gpac/gpac.git . && \
    ./configure --static-bin --use-zlib=no && \
    make -j$(nproc) && \
    strip bin/gcc/MP4Box

WORKDIR /src/bento4
RUN git clone --depth 1 https://github.com/axiomatic-systems/Bento4.git . && \
    mkdir cmakebuild && \
    cd cmakebuild && \
    cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local/bento4 .. && \
    make -j$(nproc) && \
    make install

# Stage 2: Final Image
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
    unzip \
    procps \
    genisoimage \
    mediainfo \
    ffmpeg \
    ca-certificates \
    git \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Go
RUN curl -L -o go.tar.gz https://go.dev/dl/go1.25.6.linux-amd64.tar.gz && \
    rm -rf /usr/local/go && \
    tar -C /usr/local -xzf go.tar.gz && \
    rm go.tar.gz
ENV PATH=$PATH:/usr/local/go/bin

# Install Bento4 from builder
COPY --from=gpac-builder /usr/local/bento4 /usr/local/bento4
ENV PATH=$PATH:/usr/local/bento4/bin

# Install MP4Box from builder
COPY --from=gpac-builder /src/gpac/bin/gcc/MP4Box /usr/local/bin/MP4Box

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
