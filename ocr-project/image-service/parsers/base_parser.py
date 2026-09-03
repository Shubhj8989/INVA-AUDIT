from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class ExtractedField:
    """Represents a single extracted header field with confidence and cross-link metadata."""
    def __init__(
        self,
        value: Any,
        confidence: float = 1.0,
        raw_box: Optional[List] = None,
        needs_review: bool = False,
        review_reason: str = "",
        is_cross_link_key: bool = False   # True for fields used to join documents
    ):
        self.value = value
        self.confidence = round(confidence, 3)
        self.raw_box = raw_box or []
        self.needs_review = needs_review
        self.review_reason = review_reason
        self.is_cross_link_key = is_cross_link_key

    def to_dict(self):
        return {
            "value": self.value,
            "confidence": self.confidence,
            "needs_review": self.needs_review,
            "review_reason": self.review_reason,
            "is_cross_link_key": self.is_cross_link_key,
            "raw_box": self.raw_box
        }


class ExtractedLineItem:
    """
    Represents a single line item extracted from any document.

    All qty fields that are None mean "not present on this document type".
    Scope: item_code + qty fields only - no price/value fields.
    """
    def __init__(
        self,
        sr_no: Any,
        item_code: str,
        description: str,
        qty: float,                          # Primary qty (context-specific: picked/invoiced/received)
        uom: str = "PCS",
        hsn_code: str = "",
        # Outward-specific
        ordered_qty: Optional[float] = None,
        picked_qty: Optional[float] = None,
        rack_location: str = "",
        stamp: str = "",                     # CONFIRMED / REGENERATED
        # Inward-specific
        po_qty: Optional[float] = None,
        received_qty: Optional[float] = None,
        accepted_qty: Optional[float] = None,
        rejected_qty: Optional[float] = None,
        # Transfer-specific
        transfer_qty: Optional[float] = None,
        # Review
        confidence: float = 1.0,
        needs_review: bool = False,
        review_reason: str = "",
        extra_data: Optional[Dict] = None
    ):
        self.sr_no = sr_no
        self.item_code = item_code
        self.description = description
        self.qty = qty
        self.uom = uom
        self.hsn_code = hsn_code
        self.ordered_qty = ordered_qty
        self.picked_qty = picked_qty
        self.rack_location = rack_location
        self.stamp = stamp
        self.po_qty = po_qty
        self.received_qty = received_qty
        self.accepted_qty = accepted_qty
        self.rejected_qty = rejected_qty
        self.transfer_qty = transfer_qty
        self.confidence = round(confidence, 3)
        self.needs_review = needs_review
        self.review_reason = review_reason
        self.extra_data = extra_data or {}

    def to_dict(self):
        d = {
            "sr_no": self.sr_no,
            "item_code": self.item_code,
            "description": self.description,
            "qty": self.qty,
            "uom": self.uom,
            "hsn_code": self.hsn_code,
            "confidence": self.confidence,
            "needs_review": self.needs_review,
            "review_reason": self.review_reason,
        }
        # Only include optional qty fields if they were set
        if self.ordered_qty is not None:   d["ordered_qty"]   = self.ordered_qty
        if self.picked_qty is not None:    d["picked_qty"]    = self.picked_qty
        if self.rack_location:             d["rack_location"] = self.rack_location
        if self.stamp:                     d["stamp"]         = self.stamp
        if self.po_qty is not None:        d["po_qty"]        = self.po_qty
        if self.received_qty is not None:  d["received_qty"]  = self.received_qty
        if self.accepted_qty is not None:  d["accepted_qty"]  = self.accepted_qty
        if self.rejected_qty is not None:  d["rejected_qty"]  = self.rejected_qty
        if self.transfer_qty is not None:  d["transfer_qty"]  = self.transfer_qty
        if self.extra_data:                d["extra_data"]    = self.extra_data
        return d


class ExtractedDocument:
    def __init__(
        self,
        doc_type: str,
        headers: Dict[str, ExtractedField],
        line_items: List[ExtractedLineItem],
        metadata: Optional[Dict] = None,
        is_valid: bool = True
    ):
        self.doc_type = doc_type
        self.headers = headers
        self.line_items = line_items
        self.metadata = metadata or {}
        self.is_valid = is_valid

    def to_dict(self):
        total_items = len(self.line_items)
        total_qty = sum(item.qty for item in self.line_items)
        has_review_flags = (
            any(h.needs_review for h in self.headers.values()) or
            any(item.needs_review for item in self.line_items)
        )
        cross_link_keys = {
            k: v.value for k, v in self.headers.items() if v.is_cross_link_key
        }

        return {
            "doc_type": self.doc_type,
            "is_valid": self.is_valid,
            "has_review_flags": has_review_flags,
            "cross_link_keys": cross_link_keys,
            "summary": {
                "total_items": total_items,
                "total_qty": round(total_qty, 2)
            },
            "headers": {k: v.to_dict() for k, v in self.headers.items()},
            "line_items": [item.to_dict() for item in self.line_items],
            "metadata": self.metadata
        }


class BaseDocumentParser(ABC):
    """Abstract base class for all zonal document parsers."""

    @abstractmethod
    def parse(
        self,
        elements: List[Dict[str, Any]],
        image_width: int,
        image_height: int
    ) -> ExtractedDocument:
        pass
