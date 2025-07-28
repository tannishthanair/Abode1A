# Use a slim Python base image compatible with AMD64
FROM --platform=linux/amd64 python:3.9-slim-bullseye

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY app/requirements.txt .

# Install dependencies (including PyMuPDF's underlying C libraries)
# We need to install necessary system dependencies for PyMuPDF (MuPDF's shared libraries)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libharfbuzz-dev \
    libfreetype6-dev \
    libjpeg-dev \
    zlib1g-dev \
    pkg-config \
    libopenjp2-7 \
    libfontconfig1 \
    libglib2.0-0 \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the rest of your application code into the container
COPY app/ .

# Command to run the application
# The container will automatically process PDFs from /app/input
# when started with the specified Docker run command.
# No ENTRYPOINT or CMD is strictly needed here if the `docker run` command
# explicitly overrides the entrypoint or executes `python main.py`.
# However, for clarity and if main.py is the primary executable:
CMD ["python", "main.py"]