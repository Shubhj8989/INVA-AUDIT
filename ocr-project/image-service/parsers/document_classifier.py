from typing import List, Dict, Any, Tuple
import re


class DocumentClassifier:
    """
    Classifies scanned documents into one of 7 audit-scope document types:

    OUTWARD chain:
      - TAX_INVOICE          (Physical Sales Invoice)
      - PICKING_INSTRUCTION  (Picklist / Ticklist)
      - PICK_LIST_REPORT     (Oracle Pick List print)
      - LR_DOCUMENT          (Lorry Receipt)
      - STOCK_TRANSFER       (Branch / Inter-unit Transfer)

    INWARD chain:
      - PURCHASE_INVOICE     (Physical Purchase Invoice)
      - GRN_DOCUMENT         (Goods Receipt Note)
      - UNKNOWN
    """

    PATTERNS = {
        "TAX_INVOICE": [
            r"tax\s+invoice",
            r"gst\s+invoice\s+no",
            r"gst\s+inv\s+date",
            r"place\s+of\s+supply",
            r"pre-tax\s+value",
            r"panasonic\s+life\s+solutions",
            r"order\s+no",
            r"ship\s*[-\s]*to",
        ],
        "PICKING_INSTRUCTION": [
            r"picking\s+instruction",
            r"pick\s+slip\s+no",
            r"pi-mu-pik",
            r"pi-nk|pi-th|pi-pu",
            r"sub\s+inventory",
            r"total\s+qty\s*\(pcs\)",
            r"actual\s+picked\s+qty",
            r"loose\s+qty",
            r"report\s+run\s+date",
        ],
        "PICK_LIST_REPORT": [
            r"pick\s+list\s+report",
            r"delivery\s+no",
            r"shipment\s+priority",
            r"agent\s+request\s+date",
            r"inner\s+box-to-loose",
            r"sales\s+order\s+no.*delivery\s+no",  # both present
        ],
        "LR_DOCUMENT": [
            r"\blr\s+no\b",
            r"lorry\s+receipt",
            r"consignor",
            r"consignee",
            r"vehicle\s+no",
            r"no\.\s+of\s+packages",
            r"freight",
            r"goods\s+receipt\s+note.*transport",   # GR in transport context
        ],
        "STOCK_TRANSFER": [
            r"stock\s+transfer",
            r"branch\s+transfer",
            r"inter.?unit\s+transfer",
            r"transfer\s+order\s+no",
            r"sto\s+no",
            r"from\s+(?:site|warehouse|plant).*to\s+(?:site|warehouse|plant)",
        ],
        "PURCHASE_INVOICE": [
            r"purchase\s+invoice",
            r"p\.?o\.?\s+no",
            r"purchase\s+order\s+no",
            r"vendor\s+(?:code|name)",
            r"sold\s+by",
            r"supplier\s+(?:gstin|invoice)",
            r"bill\s+to.*ship\s+to",
        ],
        "GRN_DOCUMENT": [
            r"\bgrn\s+no\b",
            r"goods\s+receipt\s+note",
            r"receipt\s+no",
            r"received\s+qty",
            r"accepted\s+qty",
            r"rejected\s+qty",
            r"receiving\s+(?:site|warehouse|store)",
        ],
    }

    # Weights: higher-specificity patterns count more
    WEIGHTS = {
        "TAX_INVOICE":         [2, 3, 3, 1, 1, 2, 1, 1],
        "PICKING_INSTRUCTION": [3, 3, 3, 2, 2, 2, 2, 1, 1],
        "PICK_LIST_REPORT":    [3, 3, 2, 2, 2, 3],
        "LR_DOCUMENT":         [3, 3, 2, 2, 2, 2, 1, 1],
        "STOCK_TRANSFER":      [3, 3, 3, 3, 3, 2],
        "PURCHASE_INVOICE":    [3, 3, 3, 2, 2, 2, 2],
        "GRN_DOCUMENT":        [3, 3, 2, 3, 2, 2, 2],
    }

    @classmethod
    def classify(cls, elements: List[Dict[str, Any]]) -> Tuple[str, float]:
        """
        Scans all OCR text elements and returns (doc_type, confidence).
        Uses weighted pattern matching across all 7 document classes.
        """
        full_text = " ".join([e.get("text", "").lower() for e in elements])

        scores = {}
        for doc_type, patterns in cls.PATTERNS.items():
            weights = cls.WEIGHTS.get(doc_type, [1] * len(patterns))
            total_weight = sum(weights)
            matched_weight = 0
            for pattern, weight in zip(patterns, weights):
                if re.search(pattern, full_text, re.IGNORECASE):
                    matched_weight += weight
            scores[doc_type] = matched_weight / total_weight if total_weight > 0 else 0.0

        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]

        if best_score < 0.15:
            return "UNKNOWN", 0.0

        return best_type, round(best_score, 3)

    @classmethod
    def classify_by_filename(cls, filename: str) -> Tuple[str, float]:
        """
        Fallback classifier using filename heuristics (used when OCR elements unavailable).
        """
        name = filename.lower()
        if any(k in name for k in ["invoice", "tax_inv", "gst_inv", "sinv"]):
            return "TAX_INVOICE", 0.70
        if any(k in name for k in ["picking", "pi-", "picklist", "ticklist", "pick_instr"]):
            return "PICKING_INSTRUCTION", 0.70
        if any(k in name for k in ["pick_list", "picklist_report", "plr"]):
            return "PICK_LIST_REPORT", 0.70
        if any(k in name for k in ["lr_", "lorry", "lr-", "lrno"]):
            return "LR_DOCUMENT", 0.70
        if any(k in name for k in ["transfer", "sto", "branch_tr", "inter_unit"]):
            return "STOCK_TRANSFER", 0.70
        if any(k in name for k in ["purchase", "pinv", "vendor_inv", "supplier"]):
            return "PURCHASE_INVOICE", 0.70
        if any(k in name for k in ["grn", "goods_receipt", "receipt_note"]):
            return "GRN_DOCUMENT", 0.70
        return "UNKNOWN", 0.0
