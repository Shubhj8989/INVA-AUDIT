import re
from typing import List, Dict, Any
from .base_parser import BaseDocumentParser, ExtractedDocument, ExtractedField, ExtractedLineItem
from utils.spatial_utils import group_elements_into_lines, line_to_text
from utils.text_cleaner import clean_text, extract_numeric_qty, normalize_item_code, normalize_date


class PurchaseInvoiceParser(BaseDocumentParser):
    """
    Zonal parser for physical Purchase Invoices (Inward / GRN verification).

    Scope of extraction (per audit scope of work):
      HEADERS: Invoice No, Invoice Date, Vendor Name, Vendor Code,
               PO No (cross-link key to GRN), Receiving Site
      LINE ITEMS: Sr No, Item Code, Item Description, HSN Code,
                  Ordered Qty (PO Qty), Invoiced Qty, UOM

    OUT OF SCOPE: Rate, Amount, GST%, CGST, SGST, IGST, Total Value,
                  Payment Terms, Discount
    """

    def parse(self, elements: List[Dict[str, Any]], image_width: int = 1000, image_height: int = 1000) -> ExtractedDocument:
        headers: Dict[str, ExtractedField] = {}
        line_items: List[ExtractedLineItem] = []

        lines = group_elements_into_lines(elements, y_tolerance=10)
        full_text_lines = [line_to_text(line) for line in lines]
        combined_text = "\n".join(full_text_lines)

        # -- 1. HEADER EXTRACTION ----------------------------------------------

        # Invoice No (vendor's invoice number)
        inv_match = re.search(r"Invoice\s+(?:No|Number|#)\s*[:\s]*([A-Za-z0-9\-/]+)", combined_text, re.IGNORECASE)
        headers["invoice_no"] = ExtractedField(
            value=inv_match.group(1).strip() if inv_match else "",
            confidence=0.92 if inv_match else 0.0,
            needs_review=not bool(inv_match),
            review_reason="Missing Invoice No" if not inv_match else ""
        )

        # Invoice Date
        inv_date_match = re.search(
            r"(?:Invoice\s+Date|Date)\s*[:\s]*([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4}|[0-9]{1,2}[\s\-][A-Za-z]{3}[\s\-][0-9]{2,4})",
            combined_text, re.IGNORECASE
        )
        headers["invoice_date"] = ExtractedField(
            value=normalize_date(inv_date_match.group(1)) if inv_date_match else None,
            confidence=0.90 if inv_date_match else 0.0
        )

        # Vendor Name
        vendor_match = re.search(
            r"(?:Vendor|Supplier|Manufacturer|Sold\s+By|From)\s*[:\s]*(.+?)(?=\n(?:Address|GSTIN|GST|Invoice|Date|PO)|\Z)",
            combined_text, re.IGNORECASE | re.DOTALL
        )
        headers["vendor_name"] = ExtractedField(
            value=clean_text(vendor_match.group(1))[:100] if vendor_match else "",
            confidence=0.80 if vendor_match else 0.0
        )

        # Vendor Code
        vendor_code_match = re.search(r"Vendor\s+Code\s*[:\s]*([A-Za-z0-9\-]+)", combined_text, re.IGNORECASE)
        headers["vendor_code"] = ExtractedField(
            value=vendor_code_match.group(1).strip() if vendor_code_match else "",
            confidence=0.85 if vendor_code_match else 0.0
        )

        # PO No - CROSS-LINK KEY: matches PO No on GRN document
        po_match = re.search(
            r"(?:P\.?O\.?\s*No|Purchase\s+Order\s+(?:No|Number)|Order\s+Reference)\s*[:\s]*([A-Za-z0-9\-/]+)",
            combined_text, re.IGNORECASE
        )
        headers["po_no"] = ExtractedField(
            value=po_match.group(1).strip() if po_match else "",
            confidence=0.92 if po_match else 0.0,
            needs_review=not bool(po_match),
            review_reason="Missing PO No - required for inward match" if not po_match else "",
            is_cross_link_key=True
        )

        # Receiving Site (Ship-To / Deliver-To)
        ship_to_match = re.search(
            r"(?:Ship\s*[-\s]*To|Deliver\s+To|Receiving\s+(?:Site|Location|Warehouse))\s*[:\s]*(.+?)(?=\n[A-Z]|\Z)",
            combined_text, re.IGNORECASE | re.DOTALL
        )
        headers["receiving_site"] = ExtractedField(
            value=clean_text(ship_to_match.group(1))[:200] if ship_to_match else "",
            confidence=0.78 if ship_to_match else 0.0
        )

        # -- 2. LINE ITEM EXTRACTION -------------------------------------------
        table_start_idx = -1
        table_end_idx = len(lines)

        for idx, line in enumerate(lines):
            line_str = line_to_text(line).upper()
            if ("ITEM CODE" in line_str or "PRODUCT CODE" in line_str or
                    ("HSN" in line_str and ("QTY" in line_str or "QUANTITY" in line_str))):
                table_start_idx = idx + 1
                break

        if table_start_idx == -1:
            table_start_idx = len(lines) // 4

        for idx in range(max(0, table_start_idx), len(lines)):
            line_str = line_to_text(lines[idx]).upper()
            if "TOTAL" in line_str or "AMOUNT" in line_str or "GRAND TOTAL" in line_str:
                table_end_idx = idx
                break

        sr_counter = 1
        for idx in range(table_start_idx, table_end_idx):
            line_str = line_to_text(lines[idx])
            code_match = re.search(r"\b(\d{4,8})\b", line_str)
            if not code_match:
                continue

            item_code = code_match.group(1)

            # HSN Code (6-8 digits, starts with 84/85 for electrical goods)
            hsn_val = ""
            for h in re.finditer(r"\b(\d{6,8})\b", line_str):
                c = h.group(1)
                if c != item_code and re.match(r"^(84|85|73|39|34)", c):
                    hsn_val = c
                    break
            if not hsn_val:
                for h in re.finditer(r"\b(\d{8})\b", line_str):
                    if h.group(1) != item_code:
                        hsn_val = h.group(1)
                        break

            # Quantities: Ordered (PO) qty and Invoiced qty
            # Typical format: "100 100" or "PO Qty: 100  Invoice Qty: 100"
            ordered_qty = None
            invoiced_qty = 0.0
            uom_val = "PCS"

            explicit_po_qty = re.search(r"(?:PO|Ordered)\s+Qty\s*[:\s]*(\d+(?:\.\d+)?)", line_str, re.IGNORECASE)
            explicit_inv_qty = re.search(r"(?:Invoice|Billed|Supply)\s+Qty\s*[:\s]*(\d+(?:\.\d+)?)", line_str, re.IGNORECASE)
            explicit_uom = re.search(r"\b(PCS|PC|NOS|SET|BOX|NO|EA|M/C)\b", line_str, re.IGNORECASE)

            if explicit_po_qty:
                ordered_qty = float(explicit_po_qty.group(1))
            if explicit_inv_qty:
                invoiced_qty = float(explicit_inv_qty.group(1))
            if explicit_uom:
                uom_val = explicit_uom.group(1).upper()

            if not explicit_inv_qty:
                all_nums = [float(n) for n in re.findall(r"\b\d+(?:\.\d+)?\b", line_str)
                            if n != item_code and n != hsn_val and float(n) < 100000]
                if len(all_nums) >= 2:
                    ordered_qty = all_nums[0]
                    invoiced_qty = all_nums[1]
                elif len(all_nums) == 1:
                    invoiced_qty = all_nums[0]

            # Description
            desc = line_str
            desc = re.sub(r"\b" + re.escape(item_code) + r"\b", "", desc)
            if hsn_val:
                desc = re.sub(r"\b" + re.escape(hsn_val) + r"\b", "", desc)
            desc = re.sub(r"\b\d+\.\d{2}\b", "", desc)  # strip price tokens
            desc = clean_text(desc)

            if (not desc or len(desc) < 5) and idx + 1 < table_end_idx:
                next_line_str = line_to_text(lines[idx + 1])
                if not re.search(r"\b\d{4,8}\b", next_line_str):
                    desc = clean_text(next_line_str)

            confidence = 0.90 if (item_code and invoiced_qty > 0) else 0.65

            line_items.append(ExtractedLineItem(
                sr_no=sr_counter,
                item_code=normalize_item_code(item_code),
                description=desc or f"ITEM {item_code}",
                qty=invoiced_qty,           # primary qty = invoiced qty
                uom=uom_val,
                hsn_code=hsn_val,
                po_qty=ordered_qty,
                received_qty=None,          # only known from GRN
                confidence=confidence,
                needs_review=confidence < 0.80,
                review_reason="Low confidence extraction" if confidence < 0.80 else ""
            ))
            sr_counter += 1

        return ExtractedDocument(
            doc_type="PURCHASE_INVOICE",
            headers=headers,
            line_items=line_items,
            metadata={
                "scope": "inward_purchase_verification",
                "cross_link_keys": {
                    "po_no": headers.get("po_no", ExtractedField("")).value,
                }
            }
        )
