FROM python:3.10.12

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y poppler-utils
RUN apt-get install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-chi-sim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy application code
COPY . .

# Copy dependency files first to leverage Docker cache
COPY pyproject.toml uv.lock ./

# Set environment variables for uv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Install Babel and compile translations
RUN uv run pip install Babel
RUN echo "Compiling translations..."
RUN uv run pybabel compile -d translations
RUN echo "Translations compiled."

# Make scripts executable
RUN chmod +x ./entrypoint.sh
RUN chmod +x ./start.sh

# Expose port
EXPOSE 8090

# Run the application
ENTRYPOINT ["./entrypoint.sh"]
CMD ["./start.sh"]