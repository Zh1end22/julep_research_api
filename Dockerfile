# Use the Python 3 official image
# https://hub.docker.com/_/python
FROM python:3.10-slim

# Run in unbuffered mode
ENV PYTHONUNBUFFERED=1 

# Create and change to the app directory.
WORKDIR /app

# Copy local code to the container image.
COPY . ./

# Install project dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONPATH=/app

# Run the web service on container startup.
CMD ["/bin/sh", "-c", "exec gunicorn --bind 0.0.0.0:5000 app:app"] 
