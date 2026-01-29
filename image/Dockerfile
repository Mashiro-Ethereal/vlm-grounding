FROM localhost/desktopd:latest

# Install Python and pip for the API script
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-websocket \
    && rm -rf /var/lib/apt/lists/*

# Copy the Chromium API script
COPY chromium_with_api.py /chromium_with_api.py
RUN chmod +x /chromium_with_api.py

# Switch back to user
USER user

# Expose the API port
EXPOSE 8122
