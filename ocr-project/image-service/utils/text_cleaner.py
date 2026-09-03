import re
from datetime import datetime

def clean_text(value):
    """Normalize whitespace and strip text."""
    if value is None:
        return ""
    value = str(value)
    return " ".join(value.split()).strip()

def extract_numeric_qty(value):
    """
    Extracts numeric quantity and UOM from strings like:
    '9 PCS' -> (9.0, 'PCS')
    '511' -> (511.0, 'PCS')
    '144.00' -> (144.0, 'PCS')
    """
    if not value:
        return 0.0, "PCS"
    
    text = clean_text(value).upper()
    
    # Check for known UOMs
    uom = "PCS"
    for unit in ["PCS", "PC", "BOX", "BOXES", "M/C", "O/B", "SET", "NOS", "KGS", "CFT"]:
        if unit in text:
            uom = unit
            break
            
    # Find numeric part
    match = re.search(r"[-+]?\d*\.?\d+", text.replace(",", ""))
    if match:
        try:
            qty = float(match.group(0))
            return qty, uom
        except ValueError:
            pass
            
    return 0.0, uom

def normalize_item_code(value):
    """Cleans item codes by removing OCR punctuation and leading/trailing junk."""
    if not value:
        return ""
    cleaned = clean_text(value)
    # Remove leading/trailing non-alphanumeric except hyphens
    cleaned = re.sub(r"^[^\w\-]+|[^\w\-]+$", "", cleaned)
    return cleaned.strip()

def normalize_date(value):
    """
    Standardize various date formats (13-AUG-26, 10-Aug-2026, 01-01-2023, 2026-08-13)
    to ISO YYYY-MM-DD.
    """
    if not value:
        return None
    cleaned = clean_text(value)
    
    date_patterns = [
        ("%d-%b-%y", r"^\d{1,2}-[A-Za-z]{3}-\d{2}$"),
        ("%d-%b-%Y", r"^\d{1,2}-[A-Za-z]{3}-\d{4}$"),
        ("%d-%m-%Y", r"^\d{1,2}-\d{1,2}-\d{4}$"),
        ("%d/%m/%Y", r"^\d{1,2}/\d{1,2}/\d{4}$"),
        ("%Y-%m-%d", r"^\d{4}-\d{1,2}-\d{1,2}$"),
    ]
    
    for fmt, pattern in date_patterns:
        if re.match(pattern, cleaned):
            try:
                dt = datetime.strptime(cleaned, fmt)
                # Handle 2-digit years if needed
                if dt.year < 2000:
                    dt = dt.replace(year=dt.year + 100)
                return dt.strftime("%Y-%m-%d")
            except Exception:
                continue
                
    return cleaned
