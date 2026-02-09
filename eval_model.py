import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from openai import OpenAI

# ================= 配置区域 =================
# 1. API 设置
BASE_URL = "https://matrixllm.alipay.com/v1"
API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL_NAME = "gpt-5.2"  # 指定测试模型

# 2. 数据集设置
DATASET_PATH = "GUI_Grounding_Benchmark/test.jsonl"  # 你的本地数据集路径
OUTPUT_FILE = f"eval_results_{MODEL_NAME}.jsonl"            # 评测结果保存路径

# 3. OSS URL 前缀设置 (非常重要！)
# 请替换为你 OSS Bucket 的实际访问域名和前缀
# 格式: https://{bucket}.{endpoint}/{prefix}/
# 例如: https://gui-test-zxh-0129.oss-cn-beijing.aliyuncs.com/benchmark_v1/
OSS_BASE_URL = "https://gui-test-zxh-0129.oss-cn-beijing.aliyuncs.com/gui_grounding_benchmark_v1/"

# 4. 并发设置
MAX_WORKERS = 5  # 根据 API 速率限制调整并发数
# ===========================================

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

def construct_image_url(relative_path):
    """
    将本地相对路径 (images/abc.png) 转换为 OSS 公网 URL
    """
    # 移除可能的开头的 /
    if relative_path.startswith('/'):
        relative_path = relative_path[1:]
    return f"{OSS_BASE_URL}{relative_path}"

def parse_model_response(content):
    """
    从模型输出中提取 JSON，兼容 markdown 格式
    """
    try:
        # 尝试直接解析
        return json.loads(content)
    except:
        # 尝试提取 ```json ... ```
        match = re.search(r'```json\s*({.*?})\s*```', content, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        # 尝试提取纯 { ... }
        match = re.search(r'({.*"point".*})', content, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    return None

def normalize_to_pixel(norm_point, width, height):
    """
    将 [0-1000] 归一化坐标转换为绝对像素坐标
    """
    x, y = norm_point
    abs_x = (x / 1000.0) * width
    abs_y = (y / 1000.0) * height
    return [abs_x, abs_y]

def check_hit(pred_point, gt_bbox):
    """
    判断点是否在 BBox 内部
    gt_bbox: [xmin, ymin, xmax, ymax]
    """
    px, py = pred_point
    xmin, ymin, xmax, ymax = gt_bbox
    # 允许 1-2 像素的误差缓冲 (可选)
    return (xmin <= px <= xmax) and (ymin <= py <= ymax)

def evaluate_single_sample(image_url, width, height, sample_data):
    """
    测试单个样本 (Query -> Response -> Check)
    """
    query = sample_data['name']
    gt_bbox = sample_data['bbox']
    
    # --- 1. 构造 Prompt ---
    # 使用归一化坐标系 [0-1000]
    system_prompt = "You are a GUI automation agent. Locate the center of the UI element described by the user."
    user_prompt = f"""
    Target Element: The element with text "{query}"
    
    Task:
    1. Analyze the UI screenshot.
    2. Identify the center point (x, y) of the target element.
    3. Normalize coordinates to 0-1000 range (0,0 is top-left).
    
    Output JSON ONLY:
    {{ "point": [x, y] }}
    """

    try:
        # --- 2. 调用 LLM ---
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                    ],
                },
            ],
            temperature=0.0 # 评测时设为0，保证结果确定性
        )
        
        content = response.choices[0].message.content
        
        # --- 3. 解析结果 ---
        parsed = parse_model_response(content)
        if not parsed or 'point' not in parsed:
            return {
                "success": False,
                "error": "Parse Error",
                "raw_response": content,
                "sample_id": sample_data.get('id')
            }
            
        norm_point = parsed['point']
        abs_point = normalize_to_pixel(norm_point, width, height)
        
        # --- 4. 判定准确性 ---
        is_hit = check_hit(abs_point, gt_bbox)
        
        return {
            "success": True,
            "is_hit": is_hit,
            "pred_point_norm": norm_point,
            "pred_point_abs": abs_point,
            "gt_bbox": gt_bbox,
            "query": query,
            "sample_id": sample_data.get('id')
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "sample_id": sample_data.get('id')
        }

def main():
    if not API_KEY:
        print("❌ 错误: 未设置 OPENAI_API_KEY")
        return

    # 1. 加载数据集
    all_tasks = []
    print(f"📖 正在读取数据集: {DATASET_PATH}")
    
    with open(DATASET_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            record = json.loads(line)
            # 这里的 record 是一张图片
            img_path_rel = record['image_filename'] # 例如 images/aljazeera.png
            img_url = construct_image_url(img_path_rel)
            w, h = record['image_width'], record['image_height']
            
            # 遍历这张图里的所有测试点
            for sample in record['test_samples']:
                # 将每个测试点封装为一个任务
                all_tasks.append({
                    "image_url": img_url,
                    "width": w,
                    "height": h,
                    "sample": sample,
                    "image_id": record.get('image_id', 'unknown')
                })

    print(f"🔍 总计发现 {len(all_tasks)} 个测试点。开始评测 {MODEL_NAME} ...")

    # 2. 并发执行评测
    results = []
    correct_count = 0
    total_processed = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交所有任务
        future_to_task = {
            executor.submit(
                evaluate_single_sample, 
                task['image_url'], 
                task['width'], 
                task['height'], 
                task['sample']
            ): task for task in all_tasks
        }

        # 使用 tqdm 显示进度
        for future in tqdm(as_completed(future_to_task), total=len(all_tasks), desc="Evaluating"):
            task = future_to_task[future]
            res = future.result()
            
            # 记录结果
            result_record = {
                "image_id": task['image_id'],
                "query": task['sample']['name'],
                "model": MODEL_NAME,
                "result": res
            }
            results.append(result_record)
            
            if res.get("success"):
                total_processed += 1
                if res.get("is_hit"):
                    correct_count += 1
            else:
                print(f"\n⚠️ API Error on {task['image_id']}: {res.get('error')}")

    # 3. 计算指标与保存
    accuracy = (correct_count / total_processed) * 100 if total_processed > 0 else 0
    
    print("\n" + "="*40)
    print(f"📊 评测报告: {MODEL_NAME}")
    print(f"✅ 总处理样本: {total_processed}")
    print(f"🎯 命中样本: {correct_count}")
    print(f"🏆 准确率 (Accuracy): {accuracy:.2f}%")
    print(f"💾 详细结果已保存至: {OUTPUT_FILE}")
    print("="*40)

    # 保存结果
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

if __name__ == "__main__":
    main()