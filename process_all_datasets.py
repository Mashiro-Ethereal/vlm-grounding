import os
import sys
from filter_ui_tree_v2 import filter_ui_tree
from draw_filtered_bboxes import draw_filtered_bboxes

def process_all_datasets(base_dir):
    """
    Iterates through all subdirectories in dataset_cropped and applies
    filtering and drawing scripts.
    """
    dataset_root = os.path.join(base_dir, "datasetv2_cropped")
    
    if not os.path.exists(dataset_root):
        print(f"Error: {dataset_root} does not exist.")
        return

    # iterate over all subdirectories
    subdirs = [d for d in os.listdir(dataset_root) 
               if os.path.isdir(os.path.join(dataset_root, d))]
    
    subdirs.sort()
    
    print(f"Found {len(subdirs)} datasets to process.")
    
    success_count = 0
    fail_count = 0
    
    for subdir_name in subdirs:
        subdir_path = os.path.join(dataset_root, subdir_name)
        
        # Check for required files
        ui_tree_path = os.path.join(subdir_path, "ui_tree.json")
        screenshot_path = os.path.join(subdir_path, "screenshot_cropped.png")
        
        if not os.path.exists(ui_tree_path):
            print(f"Skipping {subdir_name}: ui_tree.json not found")
            fail_count += 1
            continue
            
        if not os.path.exists(screenshot_path):
            print(f"Skipping {subdir_name}: screenshot_cropped.png not found")
            fail_count += 1
            continue
            
        print(f"Processing {subdir_name}...")
        
        try:
            # 1. Run filter_ui_tree
            filtered_json_path = os.path.join(subdir_path, "filtered.json")
            # Image path relative to project root or absolute?
            # In filter_ui_tree.py, we previously passed "dataset_cropped/github/screenshot_cropped.png"
            # Here we should construct it similarly: "dataset_cropped/{subdir_name}/screenshot_cropped.png"
            image_rel_path = os.path.join("datasetv2_cropped", subdir_name, "screenshot_cropped.png")
            
            filter_ui_tree(ui_tree_path, filtered_json_path, image_rel_path)
            
            # 2. Run draw_filtered_bboxes
            output_image_path = os.path.join(subdir_path, "screenshot_bbox.png")
            draw_filtered_bboxes(filtered_json_path, output_image_path)
            
            success_count += 1
            
        except Exception as e:
            print(f"Error processing {subdir_name}: {e}")
            fail_count += 1

    print(f"\nProcessing complete.")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")

if __name__ == "__main__":
    base_dir = "/Users/zhangxiuhui/Desktop/project/vlm-grounding"
    # Ensure CWD is correct for relative paths in scripts
    os.chdir(base_dir)
    process_all_datasets(base_dir)
