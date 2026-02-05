import json
from PIL import Image, ImageDraw
import sys
import os

def draw_bboxes(image_path, json_path, output_path):
    try:
        # Load image
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        
        # Load JSON
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        # Interactive roles to highlight
        INTERACTIVE_ROLES = {
            'button', 'link', 'listitem', 'textfield', 'listbox', 'tab', 
            'checkbox', 'menuitem', 'combobox', 'slider', 'togglebutton'
        }

        # Recursive function to draw boxes
        def visit(node):
            is_visible = True
            
            # Check 1: Explicit hidden state
            if 'states' in node and 'hidden' in node['states']:
                is_visible = False
            
            # Check 2: Zero dimensions
            if 'bounds' in node:
                b = node['bounds']
                if b['width'] <= 0 or b['height'] <= 0:
                    is_visible = False
            else:
                is_visible = False

            # Draw ONLY if visible and is an interactive role
            if is_visible and node.get('role') in INTERACTIVE_ROLES:
                b = node['bounds']
                x, y, w, h = b['x'], b['y'], b['width'], b['height']
                
                # Draw rectangle (Green for interactive elements to be distinct)
                draw.rectangle([x, y, x+w, y+h], outline='#00FF00', width=2)
                
                # Optional: Label the role lightly? 
                # For now keeping it simple as requested: "draw框"
            
            if 'children' in node:
                for child in node['children']:
                    visit(child)
        
        # Start traversal from root
        if 'root' in data:
            visit(data['root'])
            
        # Save output
        img.save(output_path)
        print(f"Annotated image saved to {output_path}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Hardcoded paths as requested by context, or could make them arguments
    # Using the specific paths provided in the user prompt
    base_path = "/Users/zhangxiuhui/Desktop/project/osworld-desktopd/dataset/sft_100/trajectories/github/steps/000"
    img_path = os.path.join(base_path, "screenshot.png")
    json_path = os.path.join(base_path, "ui_tree.json")
    
    # saving to the repo root as requested
    output_path = "/Users/zhangxiuhui/Desktop/project/osworld-desktopd/annotated_screenshot_github_000_clean.png"
    
    print(f"Processing {img_path} and {json_path}...")
    draw_bboxes(img_path, json_path, output_path)
