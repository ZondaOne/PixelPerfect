FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0

# Install system dependencies for image processing
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgcc-s1 \
    wget \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create models directory
RUN mkdir -p /app/models

# Create non-root user for security (recommended by Render)
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Copy requirements first for better caching
COPY --chown=app:app requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Add user pip packages to PATH
ENV PATH="/home/app/.local/bin:${PATH}"

# Copy application code
COPY --chown=app:app app/ ./app/

# Expose port (Render uses PORT environment variable)
EXPOSE $PORT


# Command to run the application
# Render automatically sets the PORT environment variable
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT