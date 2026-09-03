import re
from typing import List, Dict, Any
from .base_parser import BaseDocumentParser, ExtractedDocument, ExtractedField, ExtractedLineItem
from utils.spatial_utils import group_elements_into_lines, line_to_text
from utils.text_cleaner import clean_text, extract_numeric_qty, normalize_item_code, normalize_date


class GRNParser(BaseDocumentParser):
    """
    Zonal parser for GRN (Goods Receipt Note) documents - physical or Oracle GRN print.

    Scope of extraction (per audit scope of work):
      HEADERS: GRN No (cross-link key), GRN Date, PO No (cross-link to Purchase Invoice),
               Vendor Name, Receiving Site / Warehouse
      LINE ITEMS: Sr No, Item Code, Item Description, HSN Code,
                  PO Qty, Received Qty (KEY FIELD), Accepted Qty, Rejected Qty, UOM

    OUT OF SCOPE: Rate, Amount, Tax, Payment Terms
    """

    def parse(self, elements: List[Dict[str, Any]], image_width: int = 1000, image_height: int = 1000) -> ExtractedDocument:
        headers: Dict[str, ExtractedField] = {}
        line_items: List[ExtractedLineItem] = []

        lines = group_elements_into_lines(elements, y_tolerance=10)
        full_text_lines = [line_to_text(line) for line in lines]
        combined_text = "\n".join(full_text_lines)

        # -- 1. HEADER EXTRACTION ----------------------------------------------

        # GRN No - CROSS-LINK KEY: primary GRN identifier
        grn_match = re.search(
            r"(?:GRN\s+(?:No|Number)|Goods\s+Receipt\s+(?:No|Note\s+No)|Receipt\s+No)\s*[:\s]*([A-Za-z0-9\-/]+)",
            combined_text, re.IGNORECASE
        )
        if not grn_match:
            grn_match = re.search(r"\bGRN[:\s#\-]*([A-Za-z0-9\-/]{4,20})\b", combined_text, re.IGNORECASE)
        headers["grn_no"] = ExtractedField(
            value=grn_match.group(1).strip() if grn_match else "",
            confidence=0.92 if grn_match else 0.0,
            needs_review=not bool(grn_match),
            review_reason="Missing GRN No - required for inward verification" if not grn_match else "",
            is_cross_link_key=True
        )

        # GRN Date
        grn_date_match = re.search(
            r"(?:GRN\s+Date|Receipt\s+Date|Date\s+of\s+Receipt|Date)\s*[:\s]*"
            r"([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4}|[0-9]{1,2}[\s\-][A-Za-z]{3}[\s\-][0-9]{2,4})",
            combined_text, re.IGNORECASE
        )
        headers["grn_date"] = ExtractedField(
            value=normalize_date(grn_date_match.group(1)) if grn_date_match else None,
            confidence=0.90 if grn_date_match else 0.0
        )

        # PO No - CROSS-LINK KEY: matches PO No on Purchase Invoice
        po_match = re.search(
            r"(?:P\.?O\.?\s*(?:No|Number)|Purchase\s+Order\s+(?:No|Number)|PO\s+Reference)\s*[:\s]*([A-Za-z0-9\-/]+)",
            combined_text, re.IGNORECASE
        )
        headers["po_no"] = ExtractedField(
            value=po_match.group(1).strip() if po_match else "",
            confidence=0.92 if po_match else 0.0,
            needs_review=not bool(po_match),
            review_reason="Missing PO No - required to link to Purchase Invoice" if not po_match else "",
            is_cross_link_key=True
        )

        # Vendor Name
        vendor_match = re.search(
            r"(?:Vendor|Supplier|Received\s+From|Party\s+Name)\s*[:\s]*(.+?)(?=\n(?:GRN|PO|Date|Site|Warehouse)|\Z)",
            combined_text, re.IGNORECASE | re.DOTALL
        )
        headers["vendor_name"] = ExtractedField(
            value=clean_text(vendor_match.group(1))[:100] if vendor_match else "",
            confidence=0.80 if vendor_match else 0.0
        )

        # Receiving Site / Warehouse
        site_match = re.search(
            r"(?:Receiving\s+(?:Site|Location|Warehouse)|Warehouse|Site|Store)\s*[:\s]*([A-Za-z0-9\-\s]{2,40}?)(?=\n|\Z)",
            combined_text, re.IGNORECASE
        )
        if not site_match:
            site_match = re.search(r"\b(MU-PIK|NK-WH|TH-WH|PU-WH|NG-WH|ST-WH)\b", combined_text, re.IGNORECASE)
        headers["receiving_site"] = ExtractedField(
            value=clean_text(site_match.group(1)).upper() if site_match else "",
            confidence=0.82 if site_match else 0.0
        )

        # -- 2. LINE ITEM EXTRACTION -------------------------------------------
        table_start_idx = -1
        table_end_idx = len(lines)

        for idx, line in enumerate(lines):
            line_str = line_to_text(line).upper()
            if ("ITEM CODE" in line_str or "PRODUCT CODE" in line_str or
                    ("CODE" in line_str and ("RECEIVED" in line_str or "QTY" in line_str or "QUANTITY" in line_str))):
                table_start_idx = idx + 1
                break

        if table_start_idx == -1:
            table_start_idx = len(lines) // 4

        for idx in range(max(0, table_start_idx), len(lines)):
            line_str = line_to_text(lines[idx]).upper()
            if "TOTAL" in line_str or "SIGNATURE" in line_str or "AUTHORISED" in line_str:
                table_end_idx = idx
                break

        sr_counter = 1
        for idx in range(table_start_idx, table_end_idx):
            line_str = line_to_text(lines[idx])
            code_match = re.search(r"\b(\d{4,8})\b", line_str)
            if not code_match:
                continue

            item_code = code_match.group(1)

            # HSN Code
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

            # GRN qty fields: PO Qty / Received Qty / Accepted Qty / Rejected Qty
            # Explicit labels first
            po_qty = None
            received_qty = 0.0
            accepted_qty = None
            rejected_qty = None
            uom_val = "PCS"

            exp_po       = re.search(r"(?:PO|Ordered)\s+Qty\s*[:\s]*(\d+(?:\.\d+)?)", line_str, re.IGNORECASE)
            exp_received = re.search(r"(?:Received|Receipt)\s+Qty\s*[:\s]*(\d+(?:\.\d+)?)", line_str, re.IGNORECASE)
            exp_accepted = re.search(r"Accepted\s+Qty\s*[:\s]*(\d+(?:\.\d+)?)", line_str, re.IGNORECASE)
            exp_rejected = re.search(r"Rejected\s+Qty\s*[:\s]*(\d+(?:\.\d+)?)", line_str, re.IGNORECASE)
            exp_uom      = re.search(r"\b(PCS|PC|NOS|SET|BOX|NO|EA|M/C)\b", line_str, re.IGNORECASE)

            if exp_po:       po_qty       = float(exp_po.group(1))
            if exp_received: received_qty = float(exp_received.group(1))
            if exp_accepted: accepted_qty = float(exp_accepted.group(1))
            if exp_rejected: rejected_qty = float(exp_rejected.group(1))
            if exp_uom:      uom_val      = exp_uom.group(1).upper()

            # Fallback: positional - columns are typically PO Qty | Received Qty | Accepted | Rejected
            if not exp_received:
                all_nums = [float(n) for n in re.findall(r"\b\d+(?:\.\d+)?\b", line_str)
                            if n != item_code and n != hsn_val and float(n) < 100000]
                if len(all_nums) >= 4:
                    po_qty, received_qty, accepted_qty, rejected_qty = all_nums[0], all_nums[1], all_nums[2], all_nums[3]
                elif len(all_nums) == 3:
                    po_qty, received_qty, accepted_qty = all_nums[0], all_nums[1], all_nums[2]
                elif len(all_nums) == 2:
                    po_qty, received_qty = all_nums[0], all_nums[1]
                elif len(all_nums) == 1:
                    received_qty = all_nums[0]

            # Description
            desc = line_str
            desc = re.sub(r"\b" + re.escape(item_code) + r"\b", "", desc)
            if hsn_val:
                desc = re.sub(r"\b" + re.escape(hsn_val) + r"\b", "", desc)
            desc = re.sub(r"\b\d+\.\d{2}\b", "", desc)
            desc = clean_text(desc)

            if (not desc or len(desc) < 5) and idx + 1 < table_end_idx:
                next_line_str = line_to_text(lines[idx + 1])
                if not re.search(r"\b\d{4,8}\b", next_line_str):
                    desc = clean_text(next_line_str)

            confidence = 0.92 if (item_code and received_qty > 0) else 0.65

            line_items.append(ExtractedLineItem(
                sr_no=sr_counter,
                item_code=normalize_item_code(item_code),
                description=desc or f"ITEM {item_code}",
                qty=received_qty,           # primary qty = received qty (KEY audit field)
                uom=uom_val,
                hsn_code=hsn_val,
                po_qty=po_qty,
                received_qty=received_qty,
                accepted_qty=accepted_qty,
                rejected_qty=rejected_qty,
                confidence=confidence,
                needs_review=confidence < 0.80 or (rejected_qty is not None and rejected_qty > 0),
                review_reason=(
                    f"Rejected qty: {rejected_qty}" if rejected_qty and rejected_qty > 0
                    else "Low confidence extraction" if confidence < 0.80
                    else ""
                )
            ))
            sr_counter += 1

        return ExtractedDocument(
            doc_type="GRN_DOCUMENT",
            headers=headers,
            line_items=line_items,
            metadata={
                "scope": "inward_grn_verification",
                "cross_link_keys": {
                    "grn_no": headers.get("grn_no", ExtractedField("")).value,
                    "po_no":  headers.get("po_no",  ExtractedField("")).value,
                }
            }
        )
