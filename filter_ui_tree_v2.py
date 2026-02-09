import json
import os

def filter_ui_tree(input_path, output_path, image_filename):
    """
    Filters UI elements from the input JSON tree based on specific criteria
    and generates a flat list of test samples for VLM grounding.
    """
    
    with open(input_path, 'r') as f:
        data = json.load(f)

    screen_width = data['screen']['width']
    screen_height = data['screen']['height']
    root = data['root']
    
    test_samples = []
    
    # Interactive roles suitable for clicking
    INTERACTIVE_ROLES = {
        "button", "link", "checkbox", "menuitem", "tab", 
        "textfield", "entry", "radiobutton", "slider", "combobox"
    }

    def is_visible(node):
        """Check if a node is visible."""
        bounds = node.get('bounds', {})
        width = bounds.get('width', 0)
        height = bounds.get('height', 0)
        states = node.get('states', [])
        
        # Must have positive dimensions
        if width <= 0 or height <= 0:
            return False
            
        # Must not be hidden
        if 'hidden' in states:
            return False
            
        return True

    def is_in_screen(bounds):
        """Check if the element is strictly within screen bounds."""
        x = bounds.get('x', 0)
        y = bounds.get('y', 0)
        width = bounds.get('width', 0)
        height = bounds.get('height', 0)
        
        x2 = x + width
        y2 = y + height
        
        return (x >= 0 and y >= 0 and 
                x2 <= screen_width and y2 <= screen_height)

    def is_interactive(node):
        """Check if the node has an interactive role."""
        return node.get('role') in INTERACTIVE_ROLES

    def has_description(node):
        """Check if the node has a non-empty name."""
        name = node.get('name')
        return name is not None and len(str(name).strip()) > 0
    
    def is_folded(node):
        """Check if the node is in a collapsed state."""
        states = node.get('states', [])
        return 'collapsed' in states

    def get_center_point(bounds):
        """Calculate center point of bounds."""
        x = bounds.get('x', 0)
        y = bounds.get('y', 0)
        w = bounds.get('width', 0)
        h = bounds.get('height', 0)
        return [x + w // 2, y + h // 2]
    
    def is_large_enough(bounds):
        """Check if element is at least 10x10."""
        width = bounds.get('width', 0)
        height = bounds.get('height', 0)
        return width >= 10 and height >= 10

    def has_text_descendant(node):
        """
        Recursively check if the node has any descendant with a text-related role
        (label or StaticText/staticText).
        """
        TEXT_ROLES = {'label', 'StaticText', 'staticText'}
        
        # Check current node's children
        children = node.get('children', [])
        if not children:
            return False
            
        for child in children:
            if child.get('role') in TEXT_ROLES:
                return True
            if has_text_descendant(child):
                return True
        return False

    def get_intersection(r1, r2):
        """Calculate intersection of two rectangles [x, y, x+w, y+h]."""
        x1 = max(r1[0], r2[0])
        y1 = max(r1[1], r2[1])
        x2 = min(r1[2], r2[2])
        y2 = min(r1[3], r2[3])
        
        if x1 < x2 and y1 < y2:
            return [x1, y1, x2, y2]
        return None

    def get_area(rect):
        if not rect: return 0
        return (rect[2] - rect[0]) * (rect[3] - rect[1])


    def contains_image(node):
        """
        Recursively check if the node or its descendants have an image role.
        """
        if node.get('role') == 'image':
            return True
            
        children = node.get('children', [])
        for child in children:
            if contains_image(child):
                return True
        return False

    def traverse(node, clip_bounds):
        """
        Recursively traverse the tree.
        clip_bounds: [x, y, x2, y2] of the parent's visible area.
        """
        bounds = node.get('bounds', {})
        bx, by = bounds.get('x', 0), bounds.get('y', 0)
        bw, bh = bounds.get('width', 0), bounds.get('height', 0)
        node_rect = [bx, by, bx+bw, by+bh]
        
        # Calculate strict visible area by intersecting with parent clip
        visible_rect = get_intersection(node_rect, clip_bounds)
        
        # If no intersection or too small, prune this branch (assuming children are clipped too)
        if not visible_rect or get_area(visible_rect) < 100: # 10x10 = 100
            return

        # Rule 4: Folded elements do not show.
        # Strict: If collapsed, skip processing this node entirely.
        if is_folded(node):
            return 
            
        # Check this node
        if (is_visible(node) and 
            has_description(node) and 
            is_interactive(node)):
            
            if is_in_screen(bounds):
                # Rule 3: If interactive element contains image -> delete.
                # Rule 4 (previous): Must have text representation (handled by has_text_descendant in v1, 
                # but user now emphasizes "delete if contains image").
                # Let's use strict "contains_image" check.
                if not contains_image(node):
                    
                    sample = {
                        "id": node.get('id'),
                        "category": node.get('role'),
                        "name": node.get('name'),
                        "bbox": node_rect, # Use original full bounds or visible_rect? Usually we want the visual bounds.
                                           # But if it's clipped, we should probably use visible_rect.
                                           # Let's use visible_rect to be safe and accurate to what user sees.
                        "visible_bbox": visible_rect,
                        "point": [(visible_rect[0] + visible_rect[2]) // 2, (visible_rect[1] + visible_rect[3]) // 2]
                    }
                    test_samples.append(sample)
        
        # Traverse children with updated clip bounds
        for child in node.get('children', []):
            traverse(child, visible_rect)
        for child in node.get('children', []):
            traverse(child, visible_rect)

    # Initial clip is the screen
    screen_rect = [0, 0, screen_width, screen_height]
    traverse(root, screen_rect)
    
    # Post-processing: Occlusion Check
    # We assume 'test_samples' are roughly in DOM order (back to front).
    # We will remove elements that are significantly covered by LATER elements.
    
    final_samples = []
    
    # We iterate backwards (top-most first) to build a "kept" list
    # But checking collision against all kept items is expensive if we just keep adding.
    # Standard approach: Check if current item is occluded by any item that comes AFTER it in the original list.
    
    indices_to_remove = set()
    n = len(test_samples)
    
    for i in range(n):
        rect_i = test_samples[i]['visible_bbox']
        area_i = get_area(rect_i)
        
        # Check against all subsequent items (which are presumably on top)
        for j in range(i + 1, n):
            rect_j = test_samples[j]['visible_bbox']
            
            inter = get_intersection(rect_i, rect_j)
            if inter:
                area_inter = get_area(inter)
                # If > 50% of i is covered by j, discard i
                if area_inter / area_i > 0.5:
                    indices_to_remove.add(i)
                    break
    
    final_samples = [s for k, s in enumerate(test_samples) if k not in indices_to_remove]
    
    # Clean up 'visible_bbox' from output if not needed, or keep it as 'bbox' 
    # The prompt asked for "bbox", let's use the visible one as the true bbox
    for s in final_samples:
        s['bbox'] = s.pop('visible_bbox')
        
    test_samples = final_samples
    
    # Construct final output
    output_data = {
        "image_filename": image_filename,
        "image_width": screen_width,
        "image_height": screen_height,
        "sample_count": len(test_samples),
        "test_samples": test_samples
    }
    
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"Generated {len(test_samples)} samples in {output_path}")

if __name__ == "__main__":
    base_dir = "/Users/zhangxiuhui/Desktop/project/vlm-grounding"
    # Use a valid dataset e.g. amazon or bloomberg
    dataset_name = "amazon" 
    input_file = os.path.join(base_dir, f"datasetv2_cropped/{dataset_name}/ui_tree.json")
    output_file = os.path.join(base_dir, f"datasetv2_cropped/{dataset_name}/filtered.json")
    image_rel_path = f"datasetv2_cropped/{dataset_name}/screenshot_cropped.png"
    
    if os.path.exists(input_file):
        filter_ui_tree(input_file, output_file, image_rel_path)
    else:
        print(f"Error: Input file not found: {input_file}")
