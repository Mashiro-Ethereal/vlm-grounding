from PIL import Image
import os
import glob

def batch_crop_images():
    base_dir = "/Users/zhangxiuhui/Desktop/project/osworld-desktopd/dataset_cropped"
    
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
    batch_crop_images()
