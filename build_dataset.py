import json
import os
import shutil
from tqdm import tqdm

# ================= 配置 =================
SOURCE_ROOT = "datasetv2_cropped"       # 你现在的源目录
TARGET_ROOT = "GUI_Grounding_Benchmark" # 你想要的新目录
# =======================================

def reorganize_dataset():
    # 1. 创建目标目录结构
    images_dir = os.path.join(TARGET_ROOT, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    final_jsonl_path = os.path.join(TARGET_ROOT, "test.jsonl")
    
    # 获取所有子文件夹
    if not os.path.exists(SOURCE_ROOT):
        print(f"❌ 找不到源目录: {SOURCE_ROOT}")
        return

    subdirs = sorted([d for d in os.listdir(SOURCE_ROOT) if os.path.isdir(os.path.join(SOURCE_ROOT, d))])
    
    print(f"🚀 开始整理 {len(subdirs)} 个样本到 '{TARGET_ROOT}' ...")
    
    valid_records = []
    
    for subdir_name in tqdm(subdirs):
        source_subdir = os.path.join(SOURCE_ROOT, subdir_name)
        source_json = os.path.join(source_subdir, "filtered.json")
        source_img = os.path.join(source_subdir, "screenshot_cropped.png")
        
        # 检查文件是否存在
        if not os.path.exists(source_json) or not os.path.exists(source_img):
            continue
            
        # --- A. 确定新的唯一文件名 ---
        # 假设 subdir_name 是唯一的 (例如 'aljazeera', 'amazon')
        # 新文件名: aljazeera.png (或者 aljazeera_01.png 如果有多个)
        new_filename = f"{subdir_name}.png"
        target_img_path = os.path.join(images_dir, new_filename)
        
        # --- B. 复制图片 ---
        shutil.copy2(source_img, target_img_path)
        
        # --- C. 处理 JSON 数据 ---
        with open(source_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 关键：更新 image_filename 为新的相对路径
        # 这样 jsonl 文件就自包含引用了
        data['image_filename'] = f"images/{new_filename}"
        
        # (可选) 这里可以添加 image_id 字段
        data['image_id'] = subdir_name
        
        # (可选) 清理掉不需要的字段，只保留核心
        # data.pop('sample_count', None) # 如果你想重新计算也可以
        
        valid_records.append(data)

    # --- D. 写入最终 JSONL ---
    with open(final_jsonl_path, 'w', encoding='utf-8') as f_out:
        for record in valid_records:
            f_out.write(json.dumps(record, ensure_ascii=False) + '\n')
            
    print("\n✅ 整理完成！")
    print(f"📂 新数据集位置: {os.path.abspath(TARGET_ROOT)}")
    print(f"📄 标注文件: test.jsonl (包含 {len(valid_records)} 条记录)")
    print(f"🖼️  图片文件夹: images/ (包含 {len(os.listdir(images_dir))} 张图片)")

if __name__ == "__main__":
    reorganize_dataset()