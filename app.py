"""
Simple Flask API for PDF parsing with Docling
Designed for n8n integration
"""

from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import tempfile
from pathlib import Path
from pdf_extractor_clean import extract_for_llm
import logging

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEMP_DIR = Path(tempfile.gettempdir()) / "pdf_parser"
TEMP_DIR.mkdir(exist_ok=True)

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy", "service": "PDF Parser API"})

@app.route('/parse', methods=['POST'])
def parse_pdf():
    """
    Parse PDF file endpoint
    Accepts: PDF file upload (multipart/form-data)
    Returns: JSON with extracted data
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                "success": False, 
                "error": "No file provided. Please upload a PDF file."
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                "success": False, 
                "error": "No file selected"
            }), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({
                "success": False, 
                "error": "Invalid file format. Only PDF files are accepted."
            }), 400
        
        filename = secure_filename(file.filename)
        temp_path = TEMP_DIR / filename
        logger.info(f"Processing PDF: {filename}")
        
        file.save(str(temp_path))
        
        logger.info(f"Parsing PDF with Docling: {temp_path}")
        result = extract_for_llm(str(temp_path))
        
        result['original_filename'] = file.filename
        
        try:
            temp_path.unlink()
        except Exception as e:
            logger.warning(f"Could not delete temp file: {e}")
        
        logger.info(f"Successfully parsed: {filename}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        return jsonify({
            "success": False, 
            "error": f"Error processing PDF: {str(e)}"
        }), 500

@app.errorhandler(413)
def request_entity_too_large(_):
    """Handle file too large error"""
    return jsonify({
        "success": False,
        "error": "File too large. Maximum size is 50MB."
    }), 413

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))

    print(f"Starting PDF Parser API on port {port}")
    print("Endpoints:")
    print("  - GET  /health - Health check")
    print("  - POST /parse  - Parse PDF file")

    app.run(host='0.0.0.0', port=port, debug=False)