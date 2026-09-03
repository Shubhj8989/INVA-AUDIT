import re
from typing import List, Dict, Any
from .base_parser import BaseDocumentParser, ExtractedDocument, ExtractedField, ExtractedLineItem
from utils.spatial_utils import group_elements_into_lines, line_to_text
from utils.text_cleaner import clean_text, extract_numeric_qty, normalize_item_code, normalize_date


class StockTransferParser(BaseDocumentParser):
    """
    Zonal parser for Stock Transfer / Branch Transfer / Inter-Unit Transfer documents.

    Scope of extraction (per audit scope of work):
      HEADERS: Stock Transfer Order No (cross-link key), Transfer Date,
               From Site Code, From Site Name, To Site Code, To Site Name,
               LR No (cross-link to LR doc)
      LINE ITEMS: Sr No, Item Code, Item Description, Transfer Qty, UOM

    OUT OF SCOPE: Value, Rate, Tax
    """

    SITE_CODE_MAP = {
        "MUMBAI": "MU-PIK", "ANDHERI": "MU-PIK", "BHIWANDI": "MU-PIK",
        "NASHIK": "NK-WH", "NAGPUR": "NG-WH",
        "THANE": "TH-WH", "PUNE": "PU-WH", "SURAT": "ST-WH",
    }

    def _infer_site_code(self, text: str) -> str:
        for keyword, code in self.SITE_CODE_MAP.items():
            if keyword in text.upper():
                return code
        m = re.search(r"\b([A-Z]{2}-(?:WH|PIK|DC|DEPOT))\b", text, re.IGNORECASE)
        return m.group(1).upper() if m else ""

    def parse(self, elements: List[Dict[str, Any]], image_width: int = 1000, image_height: int = 1000) -> ExtractedDocument:
        headers: Dict[str, ExtractedField] = {}
        line_items: List[ExtractedLineItem] = []

        lines = group_elements_into_lines(elements, y_tolerance=10)
        full_text_lines = [line_to_text(line) for line in lines]
        combined_text = "\n".join(full_text_lines)

        # -- Stock Transfer Order No - CROSS-LINK KEY -------------------------
        sto_match = re.search(
            r"(?:Stock\s+Transfer\s+(?:Order\s+)?No|Transfer\s+Order\s+No|STO\s+No|Branch\s+Transfer\s+No)\s*[:\s]*([A-Za-z0-9\-/]+)",
            combined_text, re.IGNORECASE
        )
        headers["transfer_order_no"] = ExtractedField(
            value=sto_match.group(1).strip() if sto_match else "",
            confidence=0.92 if sto_match else 0.0,
            needs_review=not bool(sto_match),
            review_reason="Missing Transfer Order No" if not sto_match else "",
            is_cross_link_key=True
        )

        # Transfer Date
        date_match = re.search(
            r"(?:Transfer\s+Date|Date\s+of\s+Transfer|Date)\s*[:\s]*([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4}|[0-9]{1,2}[\s\-][A-Za-z]{3}[\s\-][0-9]{2,4})",
            combined_text, re.IGNORECASE
        )
        headers["transfer_date"] = ExtractedField(
            value=normalize_date(date_match.group(1)) if date_match else None,
            confidence=0.90 if date_match else 0.0
        )

        # From Site
        from_match = re.search(r"(?:From\s+(?:Site|Warehouse|Location|Plant)|From)\s*[:\s]*(.+?)(?=\n(?:To|$))", combined_text, re.IGNORECASE)
        from_text = clean_text(from_match.group(1))[:150] if from_match else ""
        headers["from_site_name"] = ExtractedField(value=from_text, confidence=0.80 if from_text else 0.0)
        headers["from_site_code"] = ExtractedField(value=self._infer_site_code(from_text), confidence=0.75 if from_text else 0.0)

        # To Site
        to_match = re.search(r"(?:To\s+(?:Site|Warehouse|Location|Plant)|To)\s*[:\s]*(.+?)(?=\n(?:Item|Code|Sr|$))", combined_text, re.IGNORECASE)
        to_text = clean_text(to_match.group(1))[:150] if to_match else ""
        headers["to_site_name"] = ExtractedField(value=to_text, confidence=0.80 if to_text else 0.0)
        headers["to_site_code"] = ExtractedField(value=self._infer_site_code(to_text), confidence=0.75 if to_text else 0.0)

        # LR No (transport reference)
        lr_match = re.search(r"LR\s+No\s*[:\s]*([A-Za-z0-9\-/]+)", combined_text, re.IGNORECASE)
        headers["lr_no"] = ExtractedField(
            value=lr_match.group(1).strip() if lr_match else "",
            confidence=0.88 if lr_match else 0.0,
            is_cross_link_key=True
        )

        # -- LINE ITEMS --------------------------------------------------------
        table_start_idx = -1
        table_end_idx = len(lines)

        for idx, line in enumerate(lines):
            line_str = line_to_text(line).upper()
            if ("ITEM CODE" in line_str or "PRODUCT CODE" in line_str or
                    ("CODE" in line_str and ("QTY" in line_str or "QUANTITY" in line_str))):
                table_start_idx = idx + 1
                break

        if table_start_idx == -1:
            table_start_idx = len(lines) // 4

        for idx in range(table_start_idx, len(lines)):
            line_str = line_to_text(lines[idx]).upper()
            if "TOTAL" in line_str or "AUTHORISED" in line_str or "SIGNATURE" in line_str:
                table_end_idx = idx
                break

        sr_counter = 1
        for idx in range(table_start_idx, table_end_idx):
            line_str = line_to_text(lines[idx])
            code_match = re.search(r"\b(\d{4,8})\b", line_str)
            if not code_match:
                continue

            item_code = code_match.group(1)

            # Transfer Qty + UOM
            qty_val = 0.0
            uom_val = "PCS"
            explicit_qty = re.search(r"\b(\d+(?:\.\d+)?)\s*(PCS|PC|NOS|SET|BOX|NO|EA)\b", line_str, re.IGNORECASE)
            if explicit_qty:
                qty_val, uom_val = extract_numeric_qty(explicit_qty.group(0))
            else:
                all_nums = [float(n) for n in re.findall(r"\b\d+(?:\.\d+)?\b", line_str)
                            if n != item_code and float(n) < 100000]
                if all_nums:
                    qty_val = all_nums[0]

            # Description
            desc = line_str
            desc = re.sub(r"\b" + re.escape(item_code) + r"\b", "", desc)
            if explicit_qty:
                desc = desc.replace(explicit_qty.group(0), "")
            desc = re.sub(r"\b\d+\.\d{2}\b", "", desc)
            desc = clean_text(desc)

            if (not desc or len(desc) < 5) and idx + 1 < table_end_idx:
                next_line_str = line_to_text(lines[idx + 1])
                if not re.search(r"\b\d{4,8}\b", next_line_str):
                    desc = clean_text(next_line_str)

            confidence = 0.90 if (item_code and qty_val > 0) else 0.65

            line_items.append(ExtractedLineItem(
                sr_no=sr_counter,
                item_code=normalize_item_code(item_code),
                description=desc or f"ITEM {item_code}",
                qty=qty_val,
                transfer_qty=qty_val,
                uom=uom_val,
                confidence=confidence,
                needs_review=confidence < 0.80,
                review_reason="Low confidence" if confidence < 0.80 else ""
            ))
            sr_counter += 1

        return ExtractedDocument(
            doc_type="STOCK_TRANSFER",
            headers=headers,
            line_items=line_items,
            metadata={
                "scope": "outward_inter_unit_transfer",
                "cross_link_keys": {
                    "transfer_order_no": headers.get("transfer_order_no", ExtractedField("")).value,
                    "lr_no": headers.get("lr_no", ExtractedField("")).value,
                }
            }
        )
