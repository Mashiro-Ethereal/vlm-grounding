import json
import os

def filter_ui_tree(input_path, output_path, image_filename):
    """
    Fixed VLM grounding dataset generator.
    Fix: Do NOT prune branches based on 'hidden' state of container nodes.
    Trust Geometry (Bounds) over Semantics (States).
    """
    
    with open(input_path, 'r') as f:
        data = json.load(f)

    screen_width = data['screen']['width']
    screen_height = data['screen']['height']
    root = data['root']
    
    # 1. Configuration
    INTERACTIVE_ROLES = {
        "button", "link", "checkbox", "menuitem", "tab", 
        "textfield", "entry", "radiobutton", "slider", "combobox", "input",
        "switch", "toggle", "searchbox", "listbox", "listitem" # Added list items as they often contain buttons
    }
    
    # Roles that are almost always containers or text, not occluding layers
    # We won't let these be "occluders" to avoid false positives in occlusion check
    NON_OCCLUDING_ROLES = {
        'label', 'StaticText', 'staticText', 'text', 'heading', 
        'list', 'listitem', 'group', 'generic', 'paragraph'
    }

    # 2. Helper Functions
    def get_intersection(r1, r2):
        x1 = max(r1[0], r2[0])
        y1 = max(r1[1], r2[1])
        x2 = min(r1[2], r2[2])
        y2 = min(r1[3], r2[3])
        if x1 < x2 and y1 < y2:
            return [x1, y1, x2, y2]
        return None

    def get_area(rect):
        if not rect: return 0
        return max(0, rect[2] - rect[0]) * max(0, rect[3] - rect[1])

    # 3. Global Traversal (Geometry Only)
    all_visible_nodes = [] 

    def traverse(node, parent_clip_rect):
        """
        DFS traversal. 
        CRITICAL FIX: We do NOT check 'states' here. 
        If a parent panel is marked 'hidden' but has valid bounds, we still traverse it.
        We rely on geometric intersection to determine if something is truly off-screen.
        """
        # 1. Get raw bounds
        bounds = node.get('bounds', {})
        bx, by = bounds.get('x', 0), bounds.get('y', 0)
        bw, bh = bounds.get('width', 0), bounds.get('height', 0)
        
        # 2. Skip physically non-existent dimensions
        if bw <= 0 or bh <= 0:
            return

        # 3. Calculate Strict Visible Rect (Clipping)
        # Intersect current raw bounds with parent's visible area
        raw_rect = [bx, by, bx + bw, by + bh]
        visible_rect = get_intersection(raw_rect, parent_clip_rect)

        # 4. If completely clipped, prune this branch
        if not visible_rect or get_area(visible_rect) < 25: 
            return

        # 5. Store node info
        node_info = {
            "id": node.get('id', str(len(all_visible_nodes))),
            "role": node.get('role', 'generic'),
            "name": node.get('name', ''),
            "states": node.get('states', []),  # Store state, check later
            "raw_rect": raw_rect,
            "visible_rect": visible_rect,
            "area": get_area(visible_rect)
        }
        
        all_visible_nodes.append(node_info)
        
        # 6. Traverse children
        # Note: We pass the 'visible_rect' down as the new clip boundary
        children = node.get('children', [])
        for child in children:
            traverse(child, visible_rect)
            
    # Start Traversal
    screen_rect = [0, 0, screen_width, screen_height]
    traverse(root, screen_rect)

    # 4. Selection & Filtering
    final_samples = []
    
    for i, candidate in enumerate(all_visible_nodes):
        
        # --- Filter A: Role Check ---
        if candidate['role'] not in INTERACTIVE_ROLES:
            continue
            
        # --- Filter B: Name Check ---
        name_str = str(candidate['name']).strip()
        if not name_str:
            continue

        # --- Filter C: Leaf-Level State Check (Relaxed) ---
        # Only check 'hidden' on the element itself, and trust bounds if valid.
        # Even if a button says 'hidden', if it passed the geometry check (area > 25),
        # we tend to trust it exists. But to be safe, we can filter strict 'invisible'.
        # However, for your case, trust Geometry > State.
        # Let's only filter if it says 'invisible' (often strictly CSS hidden) but ignored 'hidden' (ARIA).
        if 'invisible' in candidate['states']:
            continue
        # Note: We explicitly DO NOT check 'hidden' here because of your reported bug.

        # --- Filter D: OCCLUSION CHECK ---
        is_occluded = False
        cand_rect = candidate['visible_rect']
        cand_center = [
            (cand_rect[0] + cand_rect[2]) / 2, 
            (cand_rect[1] + cand_rect[3]) / 2
        ]
        
        # Check against subsequent nodes (drawn on top)
        for j in range(i + 1, len(all_visible_nodes)):
            occluder = all_visible_nodes[j]
            occ_rect = occluder['visible_rect']
            
            # 1. Skip if disjoint
            if (occ_rect[0] > cand_rect[2] or occ_rect[2] < cand_rect[0] or 
                occ_rect[1] > cand_rect[3] or occ_rect[3] < cand_rect[1]):
                continue

            # 2. Skip if occluder is non-blocking (text, label, invisible containers)
            if occluder['role'] in NON_OCCLUDING_ROLES:
                continue

            # 3. Center Hit Test
            if (occ_rect[0] <= cand_center[0] <= occ_rect[2] and 
                occ_rect[1] <= cand_center[1] <= occ_rect[3]):
                
                # Double check area overlap to avoid tiny pixel errors
                inter = get_intersection(cand_rect, occ_rect)
                if inter and get_area(inter) / candidate['area'] > 0.5:
                    is_occluded = True
                    break
        
        if not is_occluded:
            final_samples.append({
                "id": candidate['id'],
                "category": candidate['role'],
                "name": name_str,
                "bbox": candidate['visible_rect'],
                "point": cand_center
            })

    # 5. Output
    output_data = {
        "image_filename": image_filename,
        "image_width": screen_width,
        "image_height": screen_height,
        "sample_count": len(final_samples),
        "test_samples": final_samples
    }
    
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"✅ Generated {len(final_samples)} samples (Fixed Hidden Logic).")

if __name__ == "__main__":
    # 替换为你实际的路径测试
    base_dir = "/Users/zhangxiuhui/Desktop/project/osworld-desktopd"
    input_file = os.path.join(base_dir, "dataset_cropped/github/ui_tree.json")
    output_file = os.path.join(base_dir, "dataset_cropped/github/filtered_fixed.json")
    image_rel_path = "dataset_cropped/github/screenshot_cropped.png"
    
    filter_ui_tree(input_file, output_file, image_rel_path)