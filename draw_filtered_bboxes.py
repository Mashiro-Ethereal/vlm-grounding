import json
from PIL import Image, ImageDraw
import sys
import os

def draw_filtered_bboxes(json_path, output_path):
    try:
        # Load filtered JSON
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        base_dir = os.path.dirname(json_path)
        image_rel_path = data.get('image_filename')
        
        # Construct absolute image path
        # Assuming image_filename is relative to the project root or the same base directory logic
        # In filtered.json, it was set to "dataset_cropped/github/screenshot_cropped.png"
        # We need to resolve this correctly.
        # Let's assume the script is run from the project root.
        
        # Check if the path is absolute or relative
        if os.path.isabs(image_rel_path):
            image_path = image_rel_path
        else:
            # Try finding it relative to current working directory first
            if os.path.exists(image_rel_path):
                image_path = image_rel_path
            else:
                 # Fallback: relative to the json file?
                 # filtered.json is in dataset_cropped/github/
                 # image is dataset_cropped/github/screenshot_cropped.png
                 # valid path from project root: dataset_cropped/github/screenshot_cropped.png
                 # So if we run from project root, it should be fine.
                 image_path = image_rel_path

        print(f"Loading image from: {image_path}")
        img = Image.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        draw = ImageDraw.Draw(img)
        
        test_samples = data.get('test_samples', [])
        print(f"Found {len(test_samples)} samples to draw.")
        
        for sample in test_samples:
            bbox = sample.get('bbox')
            # bbox format: [x, y, x2, y2]
            if bbox and len(bbox) == 4:
                # Draw rectangle (Red)
                draw.rectangle(bbox, outline='#FF0000', width=3)
                
                # Check point
                point = sample.get('point')
                if point and len(point) == 2:
                     x, y = point
                     r = 3
                     draw.ellipse((x-r, y-r, x+r, y+r), fill='#00FF00', outline='#00FF00')

        # Save output
        img.save(output_path)
        print(f"Annotated screenshot saved to {output_path}")
        
    except Exception as e:
        print(f"Error drawing bboxes: {e}")
        # Build robustness: Do not exit, just raise so parent can handle or ignore
        raise e

if __name__ == "__main__":
    base_dir = "/Users/zhangxiuhui/Desktop/project/osworld-desktopd"
    json_path = os.path.join(base_dir, "dataset_cropped/github/filtered.json")
    output_path = os.path.join(base_dir, "dataset_cropped/github/screenshot_bbox.png")
    
    # Change CWD to base_dir to make relative paths work
    os.chdir(base_dir)
    
    draw_filtered_bboxes(json_path, output_path)
