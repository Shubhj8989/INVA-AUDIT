import re
from typing import List, Dict, Any
from .base_parser import BaseDocumentParser, ExtractedDocument, ExtractedField, ExtractedLineItem
from utils.spatial_utils import group_elements_into_lines, line_to_text
from utils.text_cleaner import clean_text, normalize_date


class LRParser(BaseDocumentParser):
    """
    Zonal parser for Lorry Receipt (LR) documents.

    Scope of extraction (per audit scope of work):
      HEADERS: LR No (cross-link key), LR Date, Transporter Name, Vehicle No,
               From (Consignor / Dispatch Site), To (Consignee / Delivery Address),
               No. of Packages, Description of Goods, Weight (Gross/Net),
               Invoice No Reference (links back to Tax Invoice)

    OUT OF SCOPE: Freight charges, billing amounts, payment terms
    """

    def parse(self, elements: List[Dict[str, Any]], image_width: int = 1000, image_height: int = 1000) -> ExtractedDocument:
        headers: Dict[str, ExtractedField] = {}

        lines = group_elements_into_lines(elements, y_tolerance=10)
        full_text_lines = [line_to_text(line) for line in lines]
        combined_text = "\n".join(full_text_lines)

        # -- LR No - CROSS-LINK KEY: matches LR No on Tax Invoice ------------
        lr_match = re.search(r"LR\s+No\s*[:\s]*([A-Za-z0-9\-/]+)", combined_text, re.IGNORECASE)
        if not lr_match:
            lr_match = re.search(r"Lorry\s+Receipt\s+(?:No|Number)\s*[:\s]*([A-Za-z0-9\-/]+)", combined_text, re.IGNORECASE)
        if not lr_match:
            lr_match = re.search(r"(?:GR|CN|LR)[:\s#]*([A-Za-z0-9\-/]{4,20})", combined_text, re.IGNORECASE)
        headers["lr_no"] = ExtractedField(
            value=lr_match.group(1).strip() if lr_match else "",
            confidence=0.92 if lr_match else 0.0,
            needs_review=not bool(lr_match),
            review_reason="Missing LR No - required to link to Tax Invoice" if not lr_match else "",
            is_cross_link_key=True
        )

        # LR Date
        lr_date_match = re.search(r"(?:LR\s+)?Date\s*[:\s]*([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4}|[0-9]{1,2}[\s\-][A-Za-z]{3}[\s\-][0-9]{2,4})", combined_text, re.IGNORECASE)
        headers["lr_date"] = ExtractedField(
            value=normalize_date(lr_date_match.group(1)) if lr_date_match else None,
            confidence=0.90 if lr_date_match else 0.0
        )

        # Transporter / Carrier Name
        transporter_match = re.search(r"(?:Transporter|Carrier|Transport\s+Co|Carried\s+By)\s*[:\s]*([A-Za-z\s&.,]{3,60}?)(?=\n|LR|Date|\Z)", combined_text, re.IGNORECASE)
        headers["transporter_name"] = ExtractedField(
            value=clean_text(transporter_match.group(1)) if transporter_match else "",
            confidence=0.85 if transporter_match else 0.0
        )

        # Vehicle No (Indian format: MH12AB1234 or MH 12 AB 1234)
        vehicle_match = re.search(r"\b([A-Z]{2}\s*\d{2}\s*[A-Z]{1,2}\s*\d{4})\b", combined_text, re.IGNORECASE)
        headers["vehicle_no"] = ExtractedField(
            value=re.sub(r"\s+", "", vehicle_match.group(1)).upper() if vehicle_match else "",
            confidence=0.88 if vehicle_match else 0.0
        )

        # From - Consignor / Dispatch Site
        from_match = re.search(r"(?:From|Consignor|Sender)\s*[:\s]*(.+?)(?=\n(?:To|Consignee)|$)", combined_text, re.IGNORECASE | re.DOTALL)
        headers["from_address"] = ExtractedField(
            value=clean_text(from_match.group(1))[:200] if from_match else "",
            confidence=0.80 if from_match else 0.0
        )

        # To - Consignee / Delivery Address
        to_match = re.search(r"(?:To|Consignee|Receiver)\s*[:\s]*(.+?)(?=\n(?:Packages|Goods|Weight|LR|Description)|$)", combined_text, re.IGNORECASE | re.DOTALL)
        headers["to_address"] = ExtractedField(
            value=clean_text(to_match.group(1))[:200] if to_match else "",
            confidence=0.80 if to_match else 0.0
        )

        # Number of Packages
        pkg_match = re.search(r"(?:No\.?\s*of\s*(?:Packages|Pkgs|Boxes|Pkts)|Packages)\s*[:\s]*(\d+)", combined_text, re.IGNORECASE)
        headers["no_of_packages"] = ExtractedField(
            value=int(pkg_match.group(1)) if pkg_match else None,
            confidence=0.88 if pkg_match else 0.0
        )

        # Description of Goods (general - not item-code level)
        desc_match = re.search(r"(?:Description\s+of\s+Goods|Nature\s+of\s+Goods|Contents)\s*[:\s]*(.+?)(?=\n(?:Weight|Packages|Declared)|$)", combined_text, re.IGNORECASE | re.DOTALL)
        headers["goods_description"] = ExtractedField(
            value=clean_text(desc_match.group(1))[:300] if desc_match else "",
            confidence=0.80 if desc_match else 0.0
        )

        # Weight (Gross / Net)
        weight_match = re.search(r"(?:Gross\s+)?Weight\s*[:\s]*(\d+(?:\.\d+)?)\s*(?:KG|Kg|kg)?", combined_text, re.IGNORECASE)
        headers["weight_kg"] = ExtractedField(
            value=float(weight_match.group(1)) if weight_match else None,
            confidence=0.85 if weight_match else 0.0
        )

        # Invoice No Reference (cross-link back to Tax Invoice)
        inv_ref_match = re.search(r"(?:Invoice\s+No|Inv\.?\s*No)\s*[:\s]*([A-Za-z0-9\-/]+)", combined_text, re.IGNORECASE)
        headers["invoice_no_ref"] = ExtractedField(
            value=inv_ref_match.group(1).strip() if inv_ref_match else "",
            confidence=0.88 if inv_ref_match else 0.0,
            is_cross_link_key=True
        )

        return ExtractedDocument(
            doc_type="LR_DOCUMENT",
            headers=headers,
            line_items=[],  # LR is a header-only document
            metadata={
                "scope": "outward_transport_verification",
                "cross_link_keys": {
                    "lr_no": headers.get("lr_no", ExtractedField("")).value,
                    "invoice_no_ref": headers.get("invoice_no_ref", ExtractedField("")).value,
                }
            }
        )
