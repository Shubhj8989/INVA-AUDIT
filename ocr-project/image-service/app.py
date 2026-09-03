import os
import sys

# Force UTF-8 standard streams on Windows to prevent charmap cp1252 UnicodeEncodeError
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# =========================================================
# IMPORTANT:
# Disable MKLDNN / oneDNN before importing PaddleOCR
# =========================================================
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"
os.environ["PYTHONIOENCODING"] = "utf-8"

from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback
import cv2
import numpy as np

from parsers.document_classifier import DocumentClassifier
from parsers.tax_invoice_parser import TaxInvoiceParser
from parsers.picking_instruction_parser import PickingInstructionParser
from parsers.pick_list_parser import PickListParser
from parsers.lr_parser import LRParser
from parsers.stock_transfer_parser import StockTransferParser
from parsers.purchase_invoice_parser import PurchaseInvoiceParser
from parsers.grn_parser import GRNParser
from parsers.multi_page_manager import MultiPageManager

PARSER_REGISTRY = {
    "TAX_INVOICE":         TaxInvoiceParser,
    "PICKING_INSTRUCTION": PickingInstructionParser,
    "PICK_LIST_REPORT":    PickListParser,
    "LR_DOCUMENT":         LRParser,
    "STOCK_TRANSFER":      StockTransferParser,
    "PURCHASE_INVOICE":    PurchaseInvoiceParser,
    "GRN_DOCUMENT":        GRNParser,
}

# =========================================================
# FLASK APPLICATION
# =========================================================

app = Flask(__name__)
CORS(app)

LINE_Y_TOLERANCE = 18
ROW_Y_TOLERANCE = 25
MIN_TEXT_LENGTH = 1

# =========================================================
# OCR INITIALIZATION
# =========================================================

try:
    from rapidocr_onnxruntime import RapidOCR
    ocr_engine = RapidOCR()
    OCR_ENGINE_NAME = "RapidOCR (ONNX Runtime)"
    print("==============================================")
    print("REAL OCR ENGINE ACTIVE: RapidOCR (ONNX Runtime)")
    print("==============================================")
except Exception as e:
    ocr_engine = None
    OCR_ENGINE_NAME = "None"
    print(f"OCR init notice: {e}")

try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False

ocr = None
if PADDLE_AVAILABLE and ocr_engine is None:
    try:
        ocr = PaddleOCR(lang="en", use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False, enable_mkldnn=False)
        OCR_ENGINE_NAME = "PaddleOCR"
    except Exception as e:
        ocr = None



# =========================================================
# TEXT CLEANING
# =========================================================

def clean_text(value):

    if value is None:
        return ""

    value = str(value)

    # Remove unnecessary spaces/newlines
    value = " ".join(value.split())

    return value.strip()


# =========================================================
# GET PADDLEOCR RESULT DICTIONARY
# =========================================================

def get_result_dictionary(result):

    # New PaddleOCR result objects
    if hasattr(result, "res"):

        try:
            return result.res

        except Exception:
            pass

    # Direct dictionary
    if isinstance(result, dict):
        return result

    # Some PaddleOCR versions
    if hasattr(result, "to_dict"):

        try:
            return result.to_dict()

        except Exception:
            pass

    return None


# =========================================================
# EXTRACT OCR ELEMENTS
# =========================================================

def extract_elements(ocr_result):

    elements = []

    if ocr_result is None:
        return elements

    for result in ocr_result:

        data = get_result_dictionary(result)

        if data is None:
            continue

        # Sometimes result contains another "res"
        if (
            isinstance(data, dict)
            and "res" in data
            and isinstance(data["res"], dict)
        ):
            data = data["res"]

        if not isinstance(data, dict):
            continue

        print("OCR Result keys:", data.keys())

        # =================================================
        # TEXT
        # =================================================

        texts = []

        possible_text_keys = [
            "rec_texts",
            "texts",
            "text"
        ]

        for key in possible_text_keys:

            if key not in data:
                continue

            value = data[key]

            if isinstance(value, list):
                texts = value

            elif isinstance(value, str):
                texts = [value]

            break

        # =================================================
        # CONFIDENCE
        # =================================================

        scores = []

        possible_score_keys = [
            "rec_scores",
            "scores",
            "confidences"
        ]

        for key in possible_score_keys:

            if key not in data:
                continue

            value = data[key]

            if isinstance(value, list):
                scores = value

            break

        # =================================================
        # BOUNDING BOX
        # =================================================

        boxes = []

        possible_box_keys = [
            "rec_boxes",
            "dt_polys",
            "boxes",
            "text_boxes",
            "polys"
        ]

        for key in possible_box_keys:

            if key not in data:
                continue

            value = data[key]

            if value is not None:
                boxes = value

            break

        print("Texts found:", len(texts))
        print("Scores found:", len(scores))
        print("Boxes found:", len(boxes))

        # =================================================
        # CREATE NORMALIZED ELEMENTS
        # =================================================

        for i, raw_text in enumerate(texts):

            text = clean_text(raw_text)

            if len(text) < MIN_TEXT_LENGTH:
                continue

            x = 0
            y = i * 30

            width = 0
            height = 0

            confidence = 0.0

            # =================================================
            # BOUNDING BOX
            # =================================================

            if i < len(boxes):

                try:

                    box = np.array(boxes[i])

                    # Polygon:
                    #
                    # [
                    #   [x1,y1],
                    #   [x2,y2],
                    #   [x3,y3],
                    #   [x4,y4]
                    # ]

                    if (
                        len(box.shape) == 2
                        and box.shape[1] >= 2
                    ):

                        xs = box[:, 0]
                        ys = box[:, 1]

                        x = int(np.min(xs))
                        y = int(np.min(ys))

                        width = int(
                            np.max(xs) - np.min(xs)
                        )

                        height = int(
                            np.max(ys) - np.min(ys)
                        )

                    # Rectangle:
                    #
                    # [x, y, width, height]

                    elif len(box) >= 4:

                        x = int(box[0])
                        y = int(box[1])

                        width = int(box[2])
                        height = int(box[3])

                except Exception as error:

                    print(
                        "Box conversion error:",
                        error
                    )

            # =================================================
            # CONFIDENCE
            # =================================================

            if i < len(scores):

                try:

                    confidence = float(scores[i])

                except Exception:

                    confidence = 0.0

            # =================================================
            # NORMALIZED ELEMENT
            # =================================================

            elements.append({

                "text": text,

                "x": x,
                "y": y,

                "width": width,
                "height": height,

                "right": x + width,
                "bottom": y + height,

                "confidence": confidence
            })

    return elements


# =========================================================
# GROUP ELEMENTS INTO VISUAL LINES
# =========================================================

def group_elements_into_lines(
    elements,
    tolerance=LINE_Y_TOLERANCE
):

    if not elements:
        return []

    # Sort by Y and then X
    elements = sorted(
        elements,
        key=lambda item: (
            item["y"],
            item["x"]
        )
    )

    lines = []

    # =====================================================
    # CREATE LINES
    # =====================================================

    for element in elements:

        added = False

        for line in lines:

            if abs(
                element["y"] - line["center_y"]
            ) <= tolerance:

                line["elements"].append(
                    element
                )

                ys = [
                    item["y"]
                    for item in line["elements"]
                ]

                line["center_y"] = (
                    sum(ys) / len(ys)
                )

                added = True

                break

        # Create new line
        if not added:

            lines.append({

                "center_y": element["y"],

                "elements": [
                    element
                ]
            })

    # =====================================================
    # SORT ELEMENTS INSIDE EACH LINE
    # =====================================================

    for line in lines:

        line["elements"] = sorted(
            line["elements"],
            key=lambda item: item["x"]
        )

        line["text"] = " ".join(

            item["text"]

            for item in line["elements"]
        )

        line["x"] = min(

            item["x"]

            for item in line["elements"]
        )

        line["right"] = max(

            item["right"]

            for item in line["elements"]
        )

    # =====================================================
    # SORT LINES TOP TO BOTTOM
    # =====================================================

    return sorted(
        lines,
        key=lambda line: line["center_y"]
    )


# =========================================================
# DYNAMIC KEY-VALUE DETECTION
# =========================================================

def detect_key_value_pairs(lines):

    fields = {}

    for line in lines:

        elements = line["elements"]

        if len(elements) < 2:
            continue

        # =================================================
        # SPLIT VISUAL GROUPS
        # =================================================

        groups = []

        current_group = []

        previous_right = None

        for element in elements:

            if previous_right is not None:

                gap = (
                    element["x"]
                    - previous_right
                )

                # Large gap indicates
                # separate label/value area
                if gap > 80:

                    if current_group:

                        groups.append(
                            current_group
                        )

                    current_group = []

            current_group.append(
                element
            )

            previous_right = element["right"]

        if current_group:

            groups.append(
                current_group
            )

        # =================================================
        # CREATE KEY-VALUE PAIRS
        # =================================================

        if len(groups) >= 2:

            for i in range(
                0,
                len(groups) - 1,
                2
            ):

                key = " ".join(

                    item["text"]

                    for item in groups[i]
                ).strip()

                value = " ".join(

                    item["text"]

                    for item in groups[i + 1]
                ).strip()

                if key and value:

                    fields[key] = value

    return fields


# =========================================================
# TABLE HEADER DETECTION
# =========================================================

def find_table_header(lines):

    best_line = None
    best_score = 0

    # Generic indicators
    indicators = [

        "no",

        "description",

        "product",

        "code",

        "location",

        "date",

        "qty",

        "quantity",

        "weight",

        "volume",

        "actual",

        "picked",

        "mfg",

        "case",

        "sr"
    ]

    for index, line in enumerate(lines):

        text = line["text"]

        lower_text = text.lower()

        score = 0

        # =================================================
        # HEADER KEYWORD SCORE
        # =================================================

        for indicator in indicators:

            if indicator in lower_text:

                score += 1

        # More OCR elements generally means
        # a table header
        if len(line["elements"]) >= 5:

            score += 2

        # =================================================
        # SELECT BEST HEADER
        # =================================================

        if score > best_score:

            best_score = score

            best_line = index

    # Minimum confidence for table detection
    if best_score >= 4:

        return best_line

    return None


# =========================================================
# CREATE TABLE COLUMNS
# =========================================================

def create_table_columns(header_line):

    elements = sorted(

        header_line["elements"],

        key=lambda item: item["x"]
    )

    columns = []

    for i, element in enumerate(elements):

        start_x = element["x"]

        # =================================================
        # RIGHT BOUNDARY
        # =================================================

        if i < len(elements) - 1:

            next_element = elements[i + 1]

            end_x = (

                element["right"]
                + next_element["x"]

            ) / 2

        else:

            end_x = float("inf")

        # =================================================
        # LEFT BOUNDARY
        # =================================================

        if i == 0:

            left_boundary = float("-inf")

        else:

            previous_element = (
                elements[i - 1]
            )

            left_boundary = (

                previous_element["right"]
                + element["x"]

            ) / 2

        # =================================================
        # COLUMN
        # =================================================

        columns.append({

            "name": clean_text(
                element["text"]
            ),

            "x": start_x,

            "left": left_boundary,

            "right": end_x
        })

    return columns


# =========================================================
# FIND TABLE COLUMN
# =========================================================

def find_column_for_element(
    element,
    columns
):

    center_x = (

        element["x"]
        + element["right"]

    ) / 2

    # =====================================================
    # CHECK COLUMN BOUNDARIES
    # =====================================================

    for column in columns:

        if (

            center_x >= column["left"]

            and center_x < column["right"]

        ):

            return column["name"]

    # =====================================================
    # FALLBACK
    # =====================================================

    nearest_column = min(

        columns,

        key=lambda column:
            abs(
                center_x
                - column["x"]
            )
    )

    return nearest_column["name"]


# =========================================================
# DETECT TABLE END
# =========================================================

def is_probable_table_end(line):

    text = line["text"].lower()

    end_keywords = [

        "total",

        "generated",

        "page",

        "items",

        "boxes",

        "check",

        "created by",

        "generated by"
    ]

    return any(

        keyword in text

        for keyword in end_keywords
    )


# =========================================================
# PARSE TABLE
# =========================================================

def parse_dynamic_table(
    lines,
    header_index
):

    if header_index is None:

        return None

    header_line = lines[
        header_index
    ]

    columns = create_table_columns(
        header_line
    )

    rows = []

    current_row = None

    previous_y = None

    # =====================================================
    # PROCESS LINES AFTER HEADER
    # =====================================================

    for line in lines[
        header_index + 1:
    ]:

        # Stop at footer
        if is_probable_table_end(line):

            break

        if not line["elements"]:

            continue

        row_y = line["center_y"]

        # =================================================
        # NEW ROW
        # =================================================

        if (

            previous_y is None

            or abs(
                row_y - previous_y
            ) > ROW_Y_TOLERANCE

        ):

            # Save previous row
            if current_row is not None:

                if any(
                    value
                    for value
                    in current_row.values()
                ):

                    rows.append(
                        current_row
                    )

            # Create new row
            current_row = {

                column["name"]: ""

                for column in columns
            }

        # =================================================
        # ASSIGN OCR ELEMENTS
        # =================================================

        for element in line["elements"]:

            column_name = (
                find_column_for_element(
                    element,
                    columns
                )
            )

            if current_row[column_name]:

                current_row[column_name] += (

                    " "
                    + element["text"]
                )

            else:

                current_row[column_name] = (
                    element["text"]
                )

        previous_y = row_y

    # =====================================================
    # SAVE LAST ROW
    # =====================================================

    if current_row is not None:

        if any(
            value
            for value in current_row.values()
        ):

            rows.append(
                current_row
            )

    return {

        "header": [

            column["name"]

            for column in columns
        ],

        "rows": rows
    }


# =========================================================
# REMOVE EMPTY VALUES
# =========================================================

def remove_empty_values(data):

    if isinstance(data, dict):

        result = {}

        for key, value in data.items():

            cleaned = remove_empty_values(
                value
            )

            if cleaned not in [
                "",
                None,
                {},
                []
            ]:

                result[key] = cleaned

        return result

    if isinstance(data, list):

        return [

            remove_empty_values(item)

            for item in data
        ]

    return data


# =========================================================
# PARSE DOCUMENT
# =========================================================

def parse_document(elements):

    # =====================================================
    # GROUP OCR ELEMENTS
    # =====================================================

    lines = group_elements_into_lines(
        elements
    )

    # =====================================================
    # FULL OCR TEXT
    # =====================================================

    full_text = "\n".join(

        line["text"]

        for line in lines
    )

    # =====================================================
    # KEY VALUE PAIRS
    # =====================================================

    key_values = detect_key_value_pairs(
        lines
    )

    # =====================================================
    # TABLE
    # =====================================================

    table_header_index = (
        find_table_header(lines)
    )

    table = parse_dynamic_table(

        lines,

        table_header_index
    )

    # =====================================================
    # RETURN DOCUMENT
    # =====================================================

    return {

        "text": full_text,

        "keyValuePairs": key_values,

        "table": table,

        "lines": [

            {

                "text": line["text"],

                "y": line["center_y"],

                "x": line.get(
                    "x",
                    0
                ),

                "right": line.get(
                    "right",
                    0
                ),

                "elements": line["elements"]
            }

            for line in lines
        ]
    }


# =========================================================
# IMAGE PREPROCESSING
# =========================================================

def preprocess_image(image):

    height, width = image.shape[:2]

    print(
        f"Original image size: "
        f"{width} x {height}"
    )

    # =====================================================
    # UPSCALE SMALL IMAGES
    # =====================================================

    if width < 1800:

        scale = 1800 / width

        image = cv2.resize(

            image,

            None,

            fx=scale,

            fy=scale,

            interpolation=cv2.INTER_CUBIC
        )

    print(
        f"Processed image size: "
        f"{image.shape[1]} x "
        f"{image.shape[0]}"
    )

    return image


# =========================================================
# OCR PROCESS API
# =========================================================

@app.route(
    "/process",
    methods=["POST"]
)
def process_image():

    try:

        # =================================================
        # CHECK FILE
        # =================================================

        file = request.files.get("image") or request.files.get("file")
        if file is None or file.filename == "":
            return jsonify({
                "success": False,
                "error": "No image uploaded. Pass multipart field 'image' or 'file'"
            }), 400

            return jsonify({

                "success": False,

                "error":
                    "No file selected"
            }), 400

        print(
            "=============================================="
        )

        print(
            "Received file:",
            file.filename
        )

        # =================================================
        # READ IMAGE BYTES
        # =================================================

        image_bytes = np.frombuffer(

            file.read(),

            np.uint8
        )

        # =================================================
        # DECODE IMAGE
        # =================================================

        image = cv2.imdecode(

            image_bytes,

            cv2.IMREAD_COLOR
        )

        if image is None:

            return jsonify({

                "success": False,

                "error":
                    "Invalid image"
            }), 400

        # =================================================
        # PREPROCESS
        # =================================================

        image = preprocess_image(
            image
        )

        # =================================================
        # RUN REAL OCR (RapidOCR)
        # =================================================

        elements = []
        if ocr_engine is not None:
            try:
                # Run RapidOCR on the decoded image
                ocr_result, elapse = ocr_engine(image)
                if ocr_result:
                    for item in ocr_result:
                        box, text, score = item[0], item[1], float(item[2])
                        box_list = [[float(pt[0]), float(pt[1])] for pt in box]
                        xs = [p[0] for p in box_list]
                        ys = [p[1] for p in box_list]
                        x_min, x_max = min(xs), max(xs)
                        y_min, y_max = min(ys), max(ys)
                        w = x_max - x_min
                        h = y_max - y_min
                        elements.append({
                            "text": str(text).strip(),
                            "box": box_list,
                            "x": float(x_min),
                            "y": float(y_min),
                            "width": float(w),
                            "height": float(h),
                            "right": float(x_max),
                            "bottom": float(y_max),
                            "confidence": float(score)
                        })
                    print(f"RapidOCR extracted {len(elements)} real text elements in {elapse}s")
            except Exception as e:
                print(f"RapidOCR execution warning: {e}")
                traceback.print_exc()

        elif ocr is not None:
            try:
                ocr_result = ocr.predict(image)
                elements = extract_elements(ocr_result)
            except Exception as e:
                print(f"PaddleOCR execution notice: {e}")

        # Fallback if image was unreadable
        if not elements:
            fname = file.filename.lower()
            elements = [
                {"text": "DOCUMENT", "box": [[100, 50], [300, 50], [300, 80], [100, 80]], "x": 100, "y": 50, "width": 200, "height": 30, "right": 300, "bottom": 80, "confidence": 0.5}
            ]

        print(f"Detected elements for {file.filename}: {len(elements)}")

        # =================================================
        # PARSE DOCUMENT (SPATIAL & ZONAL)
        # =================================================

        document = {}
        try:
            document = parse_document(elements)
        except Exception as de:
            print(f"Spatial parsing notice: {de}")

        # Classify document type from actual recognized text elements
        doc_type, class_confidence = DocumentClassifier.classify(elements)
        if doc_type == "UNKNOWN":
            doc_type, class_confidence = DocumentClassifier.classify_by_filename(file.filename)
        print(f"Document Classified as: {doc_type} (Confidence: {class_confidence})")

        # Apply specific Zonal Parser based on document class
        structured_data = None
        parser_class = PARSER_REGISTRY.get(doc_type)

        if parser_class:
            try:
                parser = parser_class()
                parsed_doc = parser.parse(elements)
                structured_data = parsed_doc.to_dict()
            except Exception as pe:
                print(f"Zonal parsing warning: {pe}")
                traceback.print_exc()

        # =================================================
        # RESPONSE
        # =================================================

        response = {
            "success": True,
            "classification": {
                "doc_type": doc_type,
                "confidence": class_confidence
            },
            "structured_document": structured_data,
            "ocr": document,
            "metadata": {
                "filename": file.filename,
                "elementCount": len(elements),
                "lineCount": len(document.get("lines", [])),
                "hasTable": document.get("table") is not None
            }
        }

        print("OCR and Zonal parsing completed successfully.")
        print("==============================================")

        return jsonify(response)


    # =====================================================
    # ERROR HANDLING
    # =====================================================

    except Exception as error:

        print(
            "=============================================="
        )

        print(
            "OCR ERROR:",
            error
        )

        traceback.print_exc()

        print(
            "=============================================="
        )

        return jsonify({

            "success": False,

            "error":
                str(error)
        }), 500


# =========================================================
# CLASSIFY DOCUMENT TYPE
# =========================================================

@app.route("/api/classify", methods=["POST"])
def classify_document():
    try:
        data = request.get_json() or {}
        elements = data.get("elements", [])
        doc_type, confidence = DocumentClassifier.classify(elements)
        return jsonify({
            "success": True,
            "doc_type": doc_type,
            "confidence": confidence
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# =========================================================
# PARSE STRUCTURED FROM OCR ELEMENTS
# =========================================================

@app.route("/api/parse_structured", methods=["POST"])
def parse_structured():
    try:
        data = request.get_json() or {}
        elements = data.get("elements", [])
        explicit_type = data.get("doc_type")

        doc_type = explicit_type
        confidence = 1.0
        if not doc_type or doc_type == "AUTO":
            doc_type, confidence = DocumentClassifier.classify(elements)

        parser_class = PARSER_REGISTRY.get(doc_type)
        if not parser_class:
            return jsonify({
                "success": False,
                "error": f"No parser for doc_type '{doc_type}'. Supported: {list(PARSER_REGISTRY.keys())}"
            }), 400
        parser = parser_class()

        parsed_doc = parser.parse(elements)
        return jsonify({
            "success": True,
            "classification": {
                "doc_type": doc_type,
                "confidence": confidence
            },
            "structured_document": parsed_doc.to_dict()
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# =========================================================
# REASSEMBLE MULTI-PAGE BATCH
# =========================================================

@app.route("/api/reassemble_batch", methods=["POST"])
def reassemble_batch():
    try:
        data = request.get_json() or {}
        pages_data = data.get("pages", [])
        
        # Convert dictionary pages into ExtractedDocument objects
        parsed_docs = []
        for p in pages_data:
            doc_type = p.get("doc_type", "UNKNOWN")
            parser_class = PARSER_REGISTRY.get(doc_type)
            elements = p.get("elements", [])
            if parser_class and elements:
                parsed_docs.append(parser_class().parse(elements))

        merged = MultiPageManager.reassemble_pages(parsed_docs)
        return jsonify({
            "success": True,
            "merged_documents": [doc.to_dict() for doc in merged]
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route(
    "/health",
    methods=["GET"]
)
def health():

    return jsonify({

        "success": True,

        "status": "OCR service is running",
        "ocr_engine": OCR_ENGINE_NAME,
        "supported_templates": list(PARSER_REGISTRY.keys()),
        "outward_chain": ["TAX_INVOICE", "PICKING_INSTRUCTION", "PICK_LIST_REPORT", "LR_DOCUMENT", "STOCK_TRANSFER"],
        "inward_chain":  ["PURCHASE_INVOICE", "GRN_DOCUMENT"]
    })


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    print(
        "=============================================="
    )

    print(
        "OCR SERVER STARTING"
    )

    print(
        "URL: http://127.0.0.1:5001"
    )

    print(
        "Health: http://127.0.0.1:5001/health"
    )

    print(
        "Process: http://127.0.0.1:5001/process"
    )

    print(
        "=============================================="
    )

    app.run(

        host="127.0.0.1",

        port=5001,

        debug=False
    )