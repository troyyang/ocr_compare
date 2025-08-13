# OCR Compare - Multi-Engine OCR Comparison Prototype

Compare multiple OCR engines (PaddleOCR, EasyOCR, Tesseract) on real-world documents and recommend the best one based on accuracy, speed, and cost.

## Features

- **Multi-Engine OCR**: Support for PaddleOCR, EasyOCR, and Tesseract
- **File Support**: PDF and image files (PNG, JPG, JPEG)
- **Real-time Processing**: WebSocket-based progress tracking
- **Performance Metrics**: Confidence scores, processing time, cost estimation
- **Search & Analysis**: Full-text search across OCR results
- **Benchmark Suite**: Batch processing and comparison reports

## Quick Setup (≤5 lines)

```bash
git clone https://github.com/troyyang/ocr_compare.git && cd ocr_compare
export OCR_COMPARE_DATA_DIR=$(pwd)/ocr_compare_data && mkdir -p $OCR_COMPARE_DATA_DIR/app/{data,cache}
docker compose up -d
# Access at http://localhost:3000 (frontend) and http://localhost:8088 (API)
```

## Deployment Method

### 1. Run from Code

1. Install **uv** and **python3.10**
2. Install dependencies:

   ```bash
   uv sync
   ```
3. Analyze a single file:
   ```bash
   cd ocr_compare/app
   uv run run_batch_ocr.py --input-path tests/test_data/02_scansmpl.pdf --output-dir data/output
   ```
4. Analyze a folder:

   ```bash
   uv run run_batch_ocr.py --input-path tests/test_data/ --output-dir data/output
   ```

### 2. Run from Docker

1. Install **Docker** and **Docker Compose**
2. Set environment variables:
    ```bash
    cp .env.example .env
    ```
    Edit .env file:
    ```bash
    POSTGRES_DB=ocr_compare
    POSTGRES_USER=ocr_compare
    POSTGRES_PASSWORD=ocr_compare
    POSTGRES_HOST=postgres
    POSTGRES_PORT=5432
    API_PORT=8088
    FRONTEND_PORT=3010
    OCR_COMPARE_DATA_DIR=./ocr_compare_data
    ```

3. Start the containers:

   ```bash
   docker compose up -d
   ```
4. Access the application from a browser:
   [http://localhost:3000](http://localhost:3000)
   **Username:** `admin`
   **Password:** `admin`

## Architecture

* **Frontend**: Vue.js 3 + Arco Design (React-like components)
* **Backend**: FastAPI + Python 3.10+ with async processing
* **Database**: PostgreSQL with JSONB for flexible OCR metadata
* **OCR Engines**: PaddleOCR, EasyOCR, Tesseract with unified wrapper
* **Deployment**: Docker Compose with volume persistence

## API Endpoints

* `POST /api/documents/upload` - Upload PDF/image files
* `POST /api/documents/parse/{id}` - Start OCR processing
* `GET /api/documents/find/{id}` - Retrieve OCR results
* `POST /api/documents` - Search documents and results
* `WebSocket /app_ws` - Real-time progress updates