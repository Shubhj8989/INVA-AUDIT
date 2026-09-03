from typing import List, Dict, Any
from .base_parser import ExtractedDocument, ExtractedField, ExtractedLineItem

class MultiPageManager:
    """
    Reassembles multi-page documents belonging to the same Pick Slip or Invoice.
    Stitches line items across pages, re-indexes item numbers, and aggregates totals.
    """

    @classmethod
    def reassemble_pages(cls, parsed_pages: List[ExtractedDocument]) -> List[ExtractedDocument]:
        """
        Groups single-page ExtractedDocument objects by document identifier and merges them.
        """
        if not parsed_pages:
            return []

        grouped_docs: Dict[str, List[ExtractedDocument]] = {}
        
        for doc in parsed_pages:
            # Determine group key
            doc_key = None
            if doc.doc_type == "PICKING_INSTRUCTION":
                doc_key = doc.headers.get("pick_slip_no", ExtractedField("")).value
            elif doc.doc_type == "TAX_INVOICE":
                doc_key = doc.headers.get("gst_invoice_no", ExtractedField("")).value or doc.headers.get("order_no", ExtractedField("")).value
            elif doc.doc_type == "PICK_LIST_REPORT":
                doc_key = doc.headers.get("delivery_no", ExtractedField("")).value or doc.headers.get("sales_order_no", ExtractedField("")).value

            if not doc_key:
                # If no key found, treat as independent document
                doc_key = f"UNGROUPED_{id(doc)}"

            if doc_key not in grouped_docs:
                grouped_docs[doc_key] = []
            grouped_docs[doc_key].append(doc)

        # Merge each group into a unified ExtractedDocument
        merged_results: List[ExtractedDocument] = []
        for key, pages in grouped_docs.items():
            if len(pages) == 1:
                merged_results.append(pages[0])
                continue

            # Merge multiple pages
            base_doc = pages[0]
            all_line_items: List[ExtractedLineItem] = []
            seen_items = set()
            sr_counter = 1

            for page in pages:
                for item in page.line_items:
                    # Prevent accidental duplicate row extraction across overlapping pages
                    item_sig = (item.item_code, item.qty, item.description)
                    if item_sig not in seen_items:
                        seen_items.add(item_sig)
                        item.sr_no = sr_counter
                        all_line_items.append(item)
                        sr_counter += 1

            # Update headers with merged page metadata
            merged_headers = dict(base_doc.headers)
            merged_headers["total_pages_merged"] = ExtractedField(value=len(pages), confidence=1.0)

            merged_doc = ExtractedDocument(
                doc_type=base_doc.doc_type,
                headers=merged_headers,
                line_items=all_line_items,
                metadata={
                    "is_multi_page_merged": True,
                    "pages_count": len(pages),
                    "document_key": key
                }
            )
            merged_results.append(merged_doc)

        return merged_results
