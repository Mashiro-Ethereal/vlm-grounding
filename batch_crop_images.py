from PIL import Image
import os
import glob

import shutil

def copy_source_files():
    base_source_dir = "dataset/sft_v2_100/trajectories"
    base_target_dir = "datasetv2_cropped"
    
    print(f"Start copying files from {base_source_dir} to {base_target_dir}...")
    
    # Ensure target directory exists
    if not os.path.exists(base_target_dir):
        os.makedirs(base_target_dir)
        
    # Get all trajectory directories
    traj_dirs = glob.glob(os.path.join(base_source_dir, "*"))
    
    copied_count = 0
    skipped_count = 0
    
    for traj_path in traj_dirs:
        if not os.path.isdir(traj_path):
            continue
            
        traj_id = os.path.basename(traj_path)
        source_step_dir = os.path.join(traj_path, "steps", "000")
        target_traj_dir = os.path.join(base_target_dir, traj_id)
        
        # Check if source step directory exists
        if not os.path.exists(source_step_dir):
            print(f"Warning: Source step directory not found for {traj_id}: {source_step_dir}")
            skipped_count += 1
            continue
            
        # Create target directory for this trajectory
        os.makedirs(target_traj_dir, exist_ok=True)
        
        # Files to copy
        files_to_copy = ["screenshot.png", "ui_tree.json"]
        
        for file_name in files_to_copy:
            source_file = os.path.join(source_step_dir, file_name)
            target_file = os.path.join(target_traj_dir, file_name)
            
            if os.path.exists(source_file):
                shutil.copy2(source_file, target_file)
            else:
                print(f"Warning: File not found: {source_file}")
        
        copied_count += 1
        if copied_count % 10 == 0:
            print(f"Copied files for {copied_count} trajectories...", end='\r')
            
    print(f"\nCopying complete.")
    print(f"Processed trajectories: {copied_count}")
    print(f"Skipped directories: {skipped_count}")

def batch_crop_images():
    # Update to new target directory
    base_dir = "datasetv2_cropped"
    
    # Crop parameters refined by border analysis
    # Left: 2px border
    # Top Chrome: 135px (Calculated: 720 - 583 - 2)
    # Right: 1263px (2 + 1261 Viewport)
    # Bottom: 718px (720 - 2px border)
    crop_box = (2, 135, 1263, 718)
    
    print(f"Start processing images in {base_dir}...")
    print(f"Crop Box: {crop_box}")
    
    # Find all screenshot.png files in subdirectories
    search_pattern = os.path.join(base_dir, "*", "screenshot.png")
    image_files = glob.glob(search_pattern)
    
    print(f"Found {len(image_files)} images to process.")
    
    processed_count = 0
    error_count = 0
    
    for img_path in image_files:
        try:
            # Construct output path in same directory
            dir_name = os.path.dirname(img_path)
            output_path = os.path.join(dir_name, "screenshot_cropped.png")
            
            with Image.open(img_path) as img:
                # Perform crop
                img_cropped = img.crop(crop_box)
                # Save
                img_cropped.save(output_path)
                
            processed_count += 1
            if processed_count % 10 == 0:
                print(f"Processed {processed_count} images...", end='\r')
                
        except Exception as e:
            print(f"\nError processing {img_path}: {e}")
            error_count += 1
            
    print(f"\nProcessing complete.")
    print(f"Successfully cropped: {processed_count}")
    print(f"Errors: {error_count}")

if __name__ == "__main__":
    copy_source_files()
    print("-" * 30)
    batch_crop_images()
