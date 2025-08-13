#!/usr/bin/env python3
"""
Clean PDF Data Extractor optimized for LLM processing
Separates tables from text and provides organized structure
"""

import json
import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

try:
    from docling.document_converter import DocumentConverter
except ImportError:
    print("Installing required package: docling")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "docling", "-q"])
    from docling.document_converter import DocumentConverter


class CleanPDFExtractor:
    """
    Extracts and organizes PDF content for optimal LLM processing
    """
    
    def __init__(self):
        self.converter = DocumentConverter()
    
    def extract(self, pdf_path: str, format_text: bool = True) -> Dict[str, Any]:
        """
        Extract and organize PDF content
        
        Returns a clean structure with:
        - Tables separated and typed
        - Text content without table clutter
        - Document sections identified
        - Key information highlighted
        """
        try:
            pdf_file = Path(pdf_path)
            if not pdf_file.exists():
                return {
                    "success": False,
                    "error": f"File not found: {pdf_path}"
                }
            
            # Convert PDF
            print(f"Processing: {pdf_path}", file=sys.stderr)
            result = self.converter.convert(str(pdf_file))
            
            if not result or not hasattr(result, 'document'):
                return {
                    "success": False,
                    "error": "Could not extract document content"
                }
            
            doc = result.document
            
            # Get raw content
            raw_text = doc.export_to_text() if hasattr(doc, 'export_to_text') else ""
            raw_markdown = doc.export_to_markdown() if hasattr(doc, 'export_to_markdown') else ""
            
            # Extract and organize (using markdown for table extraction)
            tables = self._extract_tables(raw_markdown)
            sections = self._extract_sections(raw_markdown)
            text_only = self._remove_tables_from_text(raw_text)
            
            # Format text if requested (converts \n to actual line breaks)
            if format_text:
                text_only = self._format_text_content(text_only)
                sections = self._format_sections(sections)
            
            key_info = self._extract_key_information(raw_text, tables)
            
            return {
                "success": True,
                "file": pdf_file.name,
                "timestamp": datetime.now().isoformat(),
                
                # Organized content for LLM
                "extracted_data": {
                    # Key information for quick access
                    "key_information": key_info,
                    
                    # Tables organized by type
                    "tables_by_type": self._organize_tables_by_type(tables),
                    
                    # MAIN TEXT FOR LLM - properly formatted with line breaks
                    "narrative_text": text_only,
                    
                    # Document structure
                    "document_sections": sections,
                    
                    # Raw tables for reference
                    "all_tables": tables
                },
                
                # Statistics
                "summary": {
                    "total_tables": len(tables),
                    "table_types": list(set(t["type"] for t in tables)),
                    "sections_found": len(sections),
                    "has_rates": any(t["type"] in ["room_rates", "rates"] for t in tables),
                    "has_offers": any("offer" in s.get("title", "").lower() for s in sections)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_tables(self, markdown: str) -> List[Dict[str, Any]]:
        """Extract and classify all tables from markdown"""
        tables = []
        lines = markdown.split('\n')
        current_table = []
        in_table = False
        table_id = 0
        
        for line in lines:
            if '|' in line:
                if not in_table:
                    in_table = True
                    current_table = []
                    table_id += 1
                
                # Skip separator lines
                if not re.match(r'^[\s\|:\-]+$', line):
                    cells = [cell.strip() for cell in line.split('|')]
                    if cells and cells[0] == '':
                        cells = cells[1:]
                    if cells and cells[-1] == '':
                        cells = cells[:-1]
                    if cells:
                        current_table.append(cells)
            else:
                if in_table and current_table:
                    table_type = self._classify_table(current_table)
                    tables.append({
                        "id": table_id,
                        "type": table_type,
                        "headers": current_table[0] if current_table else [],
                        "data": current_table[1:] if len(current_table) > 1 else [],
                        "row_count": len(current_table) - 1
                    })
                in_table = False
                current_table = []
        
        # Handle last table
        if in_table and current_table:
            table_type = self._classify_table(current_table)
            tables.append({
                "id": table_id,
                "type": table_type,
                "headers": current_table[0] if current_table else [],
                "data": current_table[1:] if len(current_table) > 1 else []
            })
        
        return tables
    
    def _classify_table(self, table: List[List[str]]) -> str:
        """Classify table based on headers and content"""
        if not table:
            return "unknown"
        
        # Combine headers and first row for classification
        headers = ' '.join(str(cell).lower() for cell in table[0])
        first_row = ' '.join(str(cell).lower() for cell in table[1]) if len(table) > 1 else ""
        combined = headers + " " + first_row
        
        # Classification rules
        classifications = [
            (["room category", "max occupancy", "no. of rooms"], "room_categories"),
            (["sgl", "dbl", "single", "double", "period", "accommodation"], "room_rates"),
            (["meal", "supplement", "board"], "meal_supplements"),
            (["christmas", "new year", "compulsory", "gala"], "compulsory_supplements"),
            (["offer", "discount", "special", "promotion"], "special_offers"),
            (["cancel", "modification", "policy"], "cancellation_policy"),
            (["transfer", "airport", "speedboat", "seaplane"], "transfers"),
            (["child", "infant", "age"], "child_policy"),
            (["location", "distance", "atoll"], "resort_info")
        ]
        
        for keywords, table_type in classifications:
            if any(keyword in combined for keyword in keywords):
                return table_type
        
        return "general"
    
    def _remove_tables_from_text(self, text: str) -> str:
        """Remove table content from text, keeping only narrative"""
        lines = text.split('\n')
        cleaned = []
        in_table = False
        
        for line in lines:
            # Detect tables (multiple | or consistent spacing suggesting columns)
            if '|' in line and line.count('|') >= 2:
                in_table = True
            elif in_table and (line.strip() == '' or not '|' in line):
                in_table = False
            elif not in_table:
                # Also skip lines that look like table data (multiple spaces suggesting columns)
                if not re.match(r'^[\s\d\.\-,]+$', line):  # Not just numbers and separators
                    cleaned.append(line)
        
        # Clean up headers and format
        result = '\n'.join(cleaned)
        # Remove multiple blank lines
        result = re.sub(r'\n\n+', '\n\n', result)
        return result.strip()
    
    def _extract_sections(self, markdown: str) -> List[Dict[str, Any]]:
        """Extract document sections with their narrative content (excluding tables)"""
        sections = []
        lines = markdown.split('\n')
        current_section = None
        section_lines = []
        in_table = False
        
        for line in lines:
            # Check for markdown headers
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if header_match:
                # Save previous section
                if current_section:
                    # Clean up content - remove empty lines
                    content = '\n'.join(section_lines).strip()
                    # Only keep if there's actual content
                    if content and not content.isspace():
                        current_section['content'] = content
                    else:
                        current_section['content'] = None
                    current_section['has_content'] = bool(current_section['content'])
                    sections.append(current_section)
                
                # Start new section
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                current_section = {
                    'level': level,
                    'title': title,
                    'type': self._classify_section(title),
                    'has_tables': False  # Will update if we find tables
                }
                section_lines = []
                in_table = False
            else:
                # Check if we're entering or in a table
                if '|' in line and line.count('|') >= 2:
                    in_table = True
                    if current_section:
                        current_section['has_tables'] = True
                elif in_table and (line.strip() == '' or '|' not in line):
                    in_table = False
                elif not in_table and current_section:
                    # Only add non-table, non-empty lines to content
                    if line.strip() and not re.match(r'^[\s\-:]+$', line):
                        section_lines.append(line)
        
        # Save last section
        if current_section:
            content = '\n'.join(section_lines).strip()
            if content and not content.isspace():
                current_section['content'] = content
            else:
                current_section['content'] = None
            current_section['has_content'] = bool(current_section['content'])
            sections.append(current_section)
        
        return sections
    
    def _classify_section(self, title: str) -> str:
        """Classify section based on title"""
        title_lower = title.lower()
        
        classifications = {
            'rates': ['rate', 'price', 'tariff', 'cost'],
            'terms': ['term', 'condition'],
            'policies': ['policy', 'policies'],
            'offers': ['offer', 'special', 'promotion', 'package', 'deal'],
            'amenities': ['amenity', 'facility', 'service', 'complimentary'],
            'transfers': ['transfer', 'airport', 'transport'],
            'meals': ['meal', 'dining', 'restaurant', 'food', 'beverage'],
            'cancellation': ['cancel', 'modification', 'refund']
        }
        
        for section_type, keywords in classifications.items():
            if any(keyword in title_lower for keyword in keywords):
                return section_type
        
        return 'general'
    
    def _extract_key_information(self, text: str, tables: List[Dict]) -> Dict[str, Any]:
        """Extract key information that LLM should focus on"""
        key_info = {
            "resort_name": None,
            "validity_period": None,
            "room_count": None,
            "meal_plans_available": [],
            "special_offers_count": 0,
            "has_christmas_supplement": False,
            "has_transfer_included": False
        }
        
        # Extract resort name - look for patterns like "BANYAN TREE VABBINFARU"
        resort_patterns = [
            r'BANYAN TREE ([A-Z]+)',
            r'([A-Z\s]{3,}(?:RESORT|HOTEL|ISLAND|VILLAS?))',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Resort|Hotel|Island)'
        ]
        
        for pattern in resort_patterns:
            resort_match = re.search(pattern, text[:500])
            if resort_match:
                name = resort_match.group(1) if '(' in pattern else resort_match.group(0)
                # Clean up the name
                name = name.strip()
                if name and not any(skip in name for skip in ['Pool Villa', 'Room Category', 'RATES PERIOD']):
                    key_info["resort_name"] = name
                    break
        
        # Extract validity period
        period_patterns = [
            r'PERIOD[:\s]+.*?(\d{1,2}[\s\-/]+(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\w*[\s\-/]+\d{2,4})',
            r'(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4})\s*[-–]\s*(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4})'
        ]
        for pattern in period_patterns:
            match = re.search(pattern, text[:1000], re.IGNORECASE)
            if match:
                key_info["validity_period"] = match.group(0)
                break
        
        # Count room types from tables
        room_tables = [t for t in tables if t["type"] == "room_categories"]
        if room_tables:
            key_info["room_count"] = sum(len(t["data"]) for t in room_tables)
        
        # Check for meal plans
        meal_keywords = ["Half Board", "Full Board", "All Inclusive", "Bed & Breakfast", "Room Only"]
        for keyword in meal_keywords:
            if keyword.lower() in text.lower():
                key_info["meal_plans_available"].append(keyword)
        
        # Count special offers
        key_info["special_offers_count"] = text.lower().count("special offer") + text.lower().count("promotion")
        
        # Check for Christmas supplement
        key_info["has_christmas_supplement"] = "christmas" in text.lower() and "supplement" in text.lower()
        
        # Check for included transfers
        key_info["has_transfer_included"] = "transfer" in text.lower() and "included" in text.lower()
        
        return key_info
    
    def _format_text_content(self, text: str) -> str:
        """
        Format text for better readability
        - Convert literal \n to actual line breaks
        - Clean up excessive whitespace
        - Preserve paragraph structure
        """
        if not text:
            return text
        
        # Handle escaped newlines
        text = text.replace('\\n', '\n')
        
        # Clean up excessive line breaks (more than 2)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Clean up spaces before/after line breaks
        text = re.sub(r' *\n *', '\n', text)
        
        # Ensure bullet points are on their own lines
        text = re.sub(r'([^-\n])(- )', r'\1\n\2', text)
        
        return text.strip()
    
    def _format_sections(self, sections: List[Dict]) -> List[Dict]:
        """
        Format section content for better readability
        Preserves line breaks for proper document structure
        """
        formatted_sections = []
        for section in sections:
            formatted_section = section.copy()
            if formatted_section.get('content'):
                # Format the content to clean up excessive line breaks
                formatted_section['content'] = self._format_text_content(formatted_section['content'])
            formatted_sections.append(formatted_section)
        return formatted_sections
    
    def _organize_tables_by_type(self, tables: List[Dict]) -> Dict[str, List[Dict]]:
        """Organize tables by their type for easier access"""
        organized = {}
        for table in tables:
            table_type = table["type"]
            if table_type not in organized:
                organized[table_type] = []
            organized[table_type].append(table)
        return organized


def extract_for_llm(pdf_path: str, format_text: bool = True) -> Dict[str, Any]:
    """
    Main function for LLM-optimized extraction
    
    Args:
        pdf_path: Path to PDF file
        format_text: If True, formats text for readability (removes literal \n)
    """
    extractor = CleanPDFExtractor()
    return extractor.extract(pdf_path, format_text=format_text)


# For n8n integration
def n8n_extract(pdf_path: str) -> Dict[str, Any]:
    """
    Simplified function for n8n Python node
    """
    result = extract_for_llm(pdf_path)
    
    if result["success"]:
        # Flatten structure for easier access in n8n
        return {
            "success": True,
            "file": result["file"],
            "key_info": result["extracted_data"]["key_information"],
            "tables": result["extracted_data"]["all_tables"],
            "text": result["extracted_data"]["narrative_text"],
            "sections": result["extracted_data"]["document_sections"],
            "summary": result["summary"]
        }
    else:
        return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
        result = extract_for_llm(pdf_file)
        
        # Create output filename based on input
        pdf_name = Path(pdf_file).stem
        output_file = f"{pdf_name}_extracted.json"
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Extraction complete!")
        print(f"📄 Input: {pdf_file}")
        print(f"💾 Output saved to: {output_file}")
        
        # Show summary
        if result.get("success"):
            print(f"📊 Summary:")
            print(f"   - Tables found: {result['summary']['total_tables']}")
            print(f"   - Sections: {result['summary']['sections_found']}")
            print(f"   - Has rates: {result['summary']['has_rates']}")
            print(f"   - Has offers: {result['summary']['has_offers']}")
    else:
        print("Usage: python pdf_extractor_clean.py <pdf_file>")
        print("Output will be saved as <filename>_extracted.json")
        sys.exit(1)