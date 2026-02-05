import json
from PIL import Image, ImageDraw
import sys
import os

def draw_bboxes_cropped(image_path, json_path, output_path):
    try:
        # Load image
        img = Image.open(image_path)
        
        # Calculate offset
        # Image: 1280x720
        # Root Bounds: 1261x583 (from ui_tree.json)
        # Refined Analysis:
        # Left Border: 2px
        # Top Chrome: 135px
        # Bottom Border: 2px
        # viewport: 1261x583
        
        Y_OFFSET = 135
        
        # Crop the image to the viewport
        # Box is (left, upper, right, lower)
        # Left: 2
        # Top: 135
        # Right: 2 + 1261 = 1263
        # Bottom: 720 - 2 = 718
        crop_box = (2, 135, 1263, 718)
        print(f"Cropping image with box: {crop_box}")
        img_cropped = img.crop(crop_box)
        
        draw = ImageDraw.Draw(img_cropped)
        
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

            # Check 3: Strictly within viewport bounds
            # Viewport size is 1261 x 583
            if 'bounds' in node:
                b = node['bounds']
                # Check if node is completely outside the viewport
                if (b['x'] >= 1261 or b['y'] >= 583 or 
                    b['x'] + b['width'] <= 0 or b['y'] + b['height'] <= 0):
                    is_visible = False
            
            # Draw ONLY if visible and is an interactive role
            if is_visible and node.get('role') in INTERACTIVE_ROLES:
                b = node['bounds']
                # Coordinates in JSON are relative to the viewport (0,0)
                # Since we cropped the image to the viewport, we can use x, y directly.
                x, y, w, h = b['x'], b['y'], b['width'], b['height']
                
                # Draw rectangle (Green)
                draw.rectangle([x, y, x+w, y+h], outline='#00FF00', width=2)
            
            if 'children' in node:
                for child in node['children']:
                    visit(child)
        
        # Start traversal from root
        if 'root' in data:
            visit(data['root'])
            
        # Save output
        img_cropped.save(output_path)
        print(f"Annotated cropped image saved to {output_path}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    base_path = "/Users/zhangxiuhui/Desktop/project/osworld-desktopd/dataset/sft_100/trajectories/github/steps/000"
    img_path = os.path.join(base_path, "screenshot.png")
    json_path = os.path.join(base_path, "ui_tree.json")
    
    output_path = "/Users/zhangxiuhui/Desktop/project/osworld-desktopd/annotated_screenshot_github_000_viewport_only.png"
    
    print(f"Processing {img_path} and {json_path}...")
    draw_bboxes_cropped(img_path, json_path, output_path)
