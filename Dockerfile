# Multi-stage build for Streamlit app
FROM python:3.11-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY src/ ./src/
COPY pages/ ./pages/
COPY outputs/ ./outputs/
COPY *.csv ./
COPY *.geojson ./
COPY *.shp ./
COPY *.shx ./
COPY *.dbf ./
COPY *.cpg ./
COPY *.prj ./

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK CMD curl --fail http://localhost:${PORT:-8501}/_stcore/health

# Run Streamlit
CMD ["bash", "-lc", "streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0"]
