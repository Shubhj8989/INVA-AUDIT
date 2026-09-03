import sys
import os

# Add current dir to sys.path so imports resolve
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parsers.document_classifier import DocumentClassifier
from parsers.tax_invoice_parser import TaxInvoiceParser
from parsers.picking_instruction_parser import PickingInstructionParser
from parsers.pick_list_parser import PickListParser
from parsers.multi_page_manager import MultiPageManager

def test_tax_invoice_parser():
    print("Testing Tax Invoice Zonal Parser...")
    
    # Mock OCR elements from Panasonic Tax Invoice sample
    mock_elements = [
        {"text": "TAX INVOICE", "box": [[100, 50], [300, 50], [300, 80], [100, 80]]},
        {"text": "Panasonic Life Solutions India Pvt. Ltd.", "box": [[50, 100], [450, 100], [450, 120], [50, 120]]},
        {"text": "GST Invoice No", "box": [[500, 100], [620, 100], [620, 120], [500, 120]]},
        {"text": "7010126040031", "box": [[630, 100], [750, 100], [750, 120], [630, 120]]},
        {"text": "GST Inv Date: 13-AUG-26", "box": [[500, 130], [700, 130], [700, 150], [500, 150]]},
        {"text": "Order No: 701350112372", "box": [[500, 160], [720, 160], [720, 180], [500, 180]]},
        {"text": "Cust PO No: 1624575", "box": [[500, 190], [700, 190], [700, 210], [500, 210]]},
        {"text": "MASTER MALL", "box": [[200, 250], [350, 250], [350, 270], [200, 270]]},
        {"text": "3750700", "box": [[200, 280], [280, 280], [280, 300], [200, 300]]},
        # Table Header
        {"text": "Item Code Item Description HSN Code QTY UOM", "box": [[50, 400], [700, 400], [700, 420], [50, 420]]},
        # Line item
        {"text": "65981 UNO MINI PENTA MODULAR 10A SP 'C' MCB 85362030 9 PCS", "box": [[50, 430], [700, 430], [700, 450], [50, 450]]},
        {"text": "Total Invoice Value: 1450.51", "box": [[50, 500], [400, 500], [400, 520], [50, 520]]}
    ]
    
    # 1. Classification
    doc_type, confidence = DocumentClassifier.classify(mock_elements)
    print(f"  Classification: {doc_type} (Confidence: {confidence})")
    assert doc_type == "TAX_INVOICE", f"Expected TAX_INVOICE, got {doc_type}"
    
    # 2. Parsing
    parser = TaxInvoiceParser()
    result = parser.parse(mock_elements)
    res_dict = result.to_dict()
    
    print(f"  Extracted Headers: GST Inv No={res_dict['headers']['gst_invoice_no']['value']}, Order No={res_dict['headers']['order_no']['value']}")
    print(f"  Extracted Line Items: {len(res_dict['line_items'])} items")
    for item in res_dict['line_items']:
        print(f"    - Item Code: {item['item_code']}, Desc: {item['description']}, Qty: {item['qty']} {item['uom']}")
        
    assert res_dict['headers']['gst_invoice_no']['value'] == "7010126040031"
    assert res_dict['headers']['order_no']['value'] == "701350112372"
    assert len(res_dict['line_items']) >= 1
    assert res_dict['line_items'][0]['item_code'] == "65981"
    assert res_dict['line_items'][0]['qty'] == 9.0
    print("  [PASS] Tax Invoice Parser Test Passed!\n")

def test_picking_instruction_parser():
    print("Testing Picking Instruction Stacked-Row Parser...")
    
    mock_elements = [
        {"text": "Panasonic", "box": [[50, 50], [200, 50], [200, 80], [50, 80]]},
        {"text": "Picking Instruction", "box": [[250, 50], [500, 50], [500, 80], [250, 80]]},
        {"text": "*PI-MU-PIK-26-557270*", "box": [[250, 90], [500, 90], [500, 110], [250, 110]]},
        {"text": "Customer Code: 3750700", "box": [[50, 130], [250, 130], [250, 150], [50, 150]]},
        {"text": "Customer Name: MASTER MALL", "box": [[50, 160], [300, 160], [300, 180], [50, 180]]},
        {"text": "Pick Slip No: 21646361", "box": [[450, 130], [650, 130], [650, 150], [450, 150]]},
        {"text": "Pick Slip Date: 10-Aug-2026", "box": [[450, 160], [680, 160], [680, 180], [450, 180]]},
        {"text": "Order Type: 701-Distributor Sale", "box": [[450, 220], [700, 220], [700, 240], [450, 240]]},
        {"text": "Page 1 of 1", "box": [[800, 900], [900, 900], [900, 920], [800, 920]]},
        # Table Header
        {"text": "Sr. No. Product Code / Location MFG Date Loose Total Qty Actual", "box": [[50, 300], [800, 300], [800, 320], [50, 320]]},
        # Stacked Row 1 (Code & quantities)
        {"text": "1 65981 R-08-B-04 01-01-2023 0 144 0 12 9 9", "box": [[50, 340], [800, 340], [800, 360], [50, 360]]},
        # Stacked Row 2 (Sub-row directly underneath with description)
        {"text": "UNO MINI PENTA MODULAR 10A SP 'C' MCB", "box": [[100, 365], [600, 365], [600, 385], [100, 385]]},
        {"text": "Total 0 0 9 9 0.65", "box": [[50, 420], [500, 420], [500, 440], [50, 440]]}
    ]
    
    # 1. Classification
    doc_type, confidence = DocumentClassifier.classify(mock_elements)
    print(f"  Classification: {doc_type} (Confidence: {confidence})")
    assert doc_type == "PICKING_INSTRUCTION", f"Expected PICKING_INSTRUCTION, got {doc_type}"
    
    # 2. Parsing
    parser = PickingInstructionParser()
    result = parser.parse(mock_elements)
    res_dict = result.to_dict()
    
    print(f"  Extracted Headers: Pick Slip No={res_dict['headers']['pick_slip_no']['value']}, Customer Code={res_dict['headers']['customer_code']['value']}")
    print(f"  Extracted Line Items: {len(res_dict['line_items'])} items")
    for item in res_dict['line_items']:
        print(f"    - Item Code: {item['item_code']}, Desc: {item['description']}, Qty: {item['qty']} {item['uom']}")
        
    assert res_dict['headers']['pick_slip_no']['value'] == "21646361"
    assert len(res_dict['line_items']) >= 1
    assert res_dict['line_items'][0]['item_code'] == "65981"
    assert res_dict['line_items'][0]['qty'] == 9.0
    assert "UNO MINI PENTA MODULAR" in res_dict['line_items'][0]['description']
    print("  [PASS] Picking Instruction Parser Test Passed!\n")

def test_multi_page_reassembly():
    print("Testing Multi-Page Document Reassembly...")
    
    # Page 1 of Picking Instruction
    p1_elements = [
        {"text": "Picking Instruction", "box": [[250, 50], [500, 50], [500, 80], [250, 80]]},
        {"text": "Pick Slip No: 21695471", "box": [[450, 130], [650, 130], [650, 150], [450, 150]]},
        {"text": "Page 1 of 2", "box": [[800, 900], [900, 900], [900, 920], [800, 920]]},
        {"text": "Sr. No. Product Code Total Qty", "box": [[50, 300], [600, 300], [600, 320], [50, 320]]},
        {"text": "1 65981 9", "box": [[50, 340], [600, 340], [600, 360], [50, 360]]},
        {"text": "UNO MINI PENTA MODULAR 10A", "box": [[50, 365], [600, 365], [600, 385], [50, 385]]}
    ]
    
    # Page 2 of Picking Instruction
    p2_elements = [
        {"text": "Picking Instruction", "box": [[250, 50], [500, 50], [500, 80], [250, 80]]},
        {"text": "Pick Slip No: 21695471", "box": [[450, 130], [650, 130], [650, 150], [450, 150]]},
        {"text": "Page 2 of 2", "box": [[800, 900], [900, 900], [900, 920], [800, 920]]},
        {"text": "Sr. No. Product Code Total Qty", "box": [[50, 300], [600, 300], [600, 320], [50, 320]]},
        {"text": "2 65982 15", "box": [[50, 340], [600, 340], [600, 360], [50, 360]]},
        {"text": "UNO MINI PENTA MODULAR 16A", "box": [[50, 365], [600, 365], [600, 385], [50, 385]]}
    ]
    
    parser = PickingInstructionParser()
    doc1 = parser.parse(p1_elements)
    doc2 = parser.parse(p2_elements)
    
    merged_docs = MultiPageManager.reassemble_pages([doc1, doc2])
    
    assert len(merged_docs) == 1
    merged = merged_docs[0].to_dict()
    print(f"  Merged Document Pick Slip: {merged['headers']['pick_slip_no']['value']}")
    print(f"  Merged Items Count: {len(merged['line_items'])} items (Total Qty: {merged['summary']['total_qty']})")
    assert len(merged['line_items']) == 2
    assert merged['summary']['total_qty'] == 24.0
    print("  [PASS] Multi-Page Reassembly Test Passed!\n")

if __name__ == "__main__":
    test_tax_invoice_parser()
    test_picking_instruction_parser()
    test_multi_page_reassembly()
    print("ALL TESTS PASSED SUCCESSFULLY! [READY]")

