# 1. Base Image
FROM python:3.11-slim

# 2. Environment Variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# 3. Working Directory
WORKDIR /app

# 4. Copy requirements
# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# 5. Install Dependencies
# Using --no-cache-dir for potentially smaller image size if not default
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 6. Copy Application Code
# This copies all files from the build context (respecting .dockerignore)
# to the working directory in the image.
COPY . .

# Create a non-root user and group
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Change ownership of the app directory
RUN chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

# 7. Expose Port
# Inform Docker that the container listens on this port at runtime.
EXPOSE 8000

# 8. Command to Run
# Command to run the application using Uvicorn.
# It's recommended to run Uvicorn directly for production.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
