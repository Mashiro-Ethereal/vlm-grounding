import os
import shutil
import json
import glob

def clean_empty_datasets():
    base_dir = "datasetv2_cropped"
    print(f"Scanning {base_dir} for empty datasets...")
    
    # Find all ui_tree.json files
    json_files = glob.glob(os.path.join(base_dir, "*", "ui_tree.json"))
    
    removed_count = 0
    kept_count = 0
    
    for json_path in json_files:
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            # Check if root children is empty
            root = data.get('root', {})
            children = root.get('children', [])
            
            if not children:
                # Remove the parent directory of this json file
                dir_to_remove = os.path.dirname(json_path)
                print(f"Removing empty dataset: {dir_to_remove}")
                shutil.rmtree(dir_to_remove)
                removed_count += 1
            else:
                kept_count += 1
                
        except Exception as e:
            print(f"Error processing {json_path}: {e}")
            
    print("-" * 30)
    print(f"Cleanup complete.")
    print(f"Removed: {removed_count} directories")
    print(f"Kept: {kept_count} directories")

if __name__ == "__main__":
    clean_empty_datasets()
