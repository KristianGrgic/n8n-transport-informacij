# PDF Parser API for n8n

Flask API service that extracts structured data from PDF documents using AI-powered Docling library. Designed for integration with n8n workflows to process Maldives resort rate sheets.

## Features
- Extracts tables with automatic classification (room rates, meal plans, etc.)
- Separates narrative text from structured data
- Identifies key information (resort names, validity periods, special offers)
- Returns clean JSON for LLM processing or database storage

## Installation

```bash
# Clone repository
git clone https://github.com/KristianGrgic/n8n-transport-informacij.git
cd n8n-transport-informacij

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

Start the API server:
```bash
python app.py
```

The API runs on `http://localhost:5001` with endpoints:
- `GET /health` - Health check
- `POST /parse` - Upload PDF and receive parsed JSON

## n8n Integration

1. Add HTTP Request node in n8n
2. Configure:
   - Method: `POST`
   - URL: `http://localhost:5001/parse`
   - Send Body: `Form-Data`
   - File field: `file`

## Example Response

```json
{
  "success": true,
  "extracted_data": {
    "key_information": {...},
    "tables_by_type": {...},
    "narrative_text": "...",
    "document_sections": [...]
  }
}
```