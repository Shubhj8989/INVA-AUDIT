# Spatial geometry utilities


def get_bounding_box(element):
    """
    Returns (x_min, y_min, x_max, y_max, width, height, center_x, center_y)
    for an OCR element.
    """
    box = element.get("box", [])
    if not box:
        return 0, 0, 0, 0, 0, 0, 0, 0
    
    xs = [pt[0] for pt in box]
    ys = [pt[1] for pt in box]
    
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    
    w = x_max - x_min
    h = y_max - y_min
    cx = (x_min + x_max) / 2.0
    cy = (y_min + y_max) / 2.0
    
    return x_min, y_min, x_max, y_max, w, h, cx, cy

def is_inside_zone(element, zone_rect):
    """
    Checks if element center is inside zone_rect (x_min, y_min, x_max, y_max).
    """
    _, _, _, _, _, _, cx, cy = get_bounding_box(element)
    zx_min, zy_min, zx_max, zy_max = zone_rect
    return zx_min <= cx <= zx_max and zy_min <= cy <= zy_max

def group_elements_into_lines(elements, y_tolerance=12):
    """
    Groups OCR elements into horizontal text lines based on Y center overlap.
    Returns list of lines, where each line is a list of elements sorted by X coordinate.
    """
    if not elements:
        return []
        
    # Sort elements top-to-bottom
    sorted_elements = sorted(elements, key=lambda e: get_bounding_box(e)[7])
    
    lines = []
    current_line = []
    current_y = None
    
    for elem in sorted_elements:
        _, _, _, _, _, _, _, cy = get_bounding_box(elem)
        
        if current_y is None:
            current_line = [elem]
            current_y = cy
        elif abs(cy - current_y) <= y_tolerance:
            current_line.append(elem)
            # Update running average Y
            current_y = sum(get_bounding_box(e)[7] for e in current_line) / len(current_line)
        else:
            # Sort current line left-to-right
            current_line.sort(key=lambda e: get_bounding_box(e)[0])
            lines.append(current_line)
            current_line = [elem]
            current_y = cy
            
    if current_line:
        current_line.sort(key=lambda e: get_bounding_box(e)[0])
        lines.append(current_line)
        
    return lines

def line_to_text(line):
    """Joins line elements into a single text string."""
    return " ".join(e.get("text", "") for e in line).strip()

def find_elements_near_keyword(elements, keyword, direction="right", max_distance=300):
    """
    Finds text elements located to the right or below a keyword label.
    Useful for key-value extraction like 'Pick Slip No: 21646361'.
    """
    kw_lower = keyword.lower()
    matches = []
    
    for i, elem in enumerate(elements):
        text = elem.get("text", "").lower()
        if kw_lower in text:
            # Found label element
            lx_min, ly_min, lx_max, ly_max, _, _, lcx, lcy = get_bounding_box(elem)
            
            # Find candidate values
            for candidate in elements:
                if candidate == elem:
                    continue
                cx_min, cy_min, cx_max, cy_max, _, _, ccx, ccy = get_bounding_box(candidate)
                
                if direction == "right":
                    # Same horizontal band, to the right
                    if abs(ccy - lcy) <= 15 and cx_min >= lx_max and (cx_min - lx_max) <= max_distance:
                        matches.append((candidate, cx_min - lx_max))
                elif direction == "below":
                    # Vertically below, roughly same X span
                    if cy_min >= ly_max and (cy_min - ly_max) <= max_distance and abs(ccx - lcx) <= 150:
                        matches.append((candidate, cy_min - ly_max))
                        
    # Sort by closest distance
    matches.sort(key=lambda x: x[1])
    return [m[0] for m in matches]
