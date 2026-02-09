import json
import os

def filter_ui_tree(input_path, output_path, image_filename):
    """
    Strictly filters UI elements based on 4 user-defined criteria:
    1. Strictly inside screen bounds.
    2. Interactive role.
    3. Visible (geometry > 0).
    4. Has a name (description).
    """
    
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 0. 获取屏幕尺寸
    screen_width = data['screen']['width']
    screen_height = data['screen']['height']
    
    # 交互元素白名单 (只保留可点击的)
    INTERACTIVE_ROLES = {
        "button", "link", "checkbox", "menuitem", "tab", 
        "textfield", "entry", "radiobutton", "slider", "combobox", "input",
        "switch", "toggle", "searchbox", "listbox", "option", "treeitem"
    }

    valid_samples = []

    def is_strictly_in_screen(bounds):
        """条件1: 严格完全在屏幕内部"""
        x, y = bounds['x'], bounds['y']
        w, h = bounds['width'], bounds['height']
        
        # 左上角检查
        if x < 0 or y < 0:
            return False
        # 右下角检查 (必须小于等于屏幕宽高)
        if (x + w) > screen_width or (y + h) > screen_height:
            return False
            
        return True

    def process_node(node):
        # 1. 递归遍历子节点 (先深度遍历，不因父节点被过滤而停止)
        if "children" in node:
            for child in node["children"]:
                process_node(child)

        # --- 开始针对当前节点的 4 重筛选 ---
        
        # 预处理数据
        role = node.get('role', 'generic')
        name = node.get('name', '')
        bounds = node.get('bounds', {})
        states = node.get('states', [])
        
        # 基础几何检查 (防 crash)
        if 'width' not in bounds or 'height' not in bounds:
            return

        # [条件 2] 可交互性筛选
        if role not in INTERACTIVE_ROLES:
            return

        # [条件 4] 描述筛选 (Name 不为空)
        if not name or len(str(name).strip()) == 0:
            return

        # [条件 3] 可见性筛选
        # A. 几何尺寸必须存在且合理 (设定最小阈值 5px 防止噪点)
        if bounds['width'] < 5 or bounds['height'] < 5:
            return
        # B. 状态检查 (只剔除明确 invisible 的，忽略 hidden)
        if 'invisible' in states:
            return

        # [条件 1] 严格屏幕范围筛选
        if not is_strictly_in_screen(bounds):
            return

        # --- 通过所有筛选，加入结果集 ---
        
        # 计算中心点 (方便后续做点击测试验证)
        cx = bounds['x'] + bounds['width'] / 2
        cy = bounds['y'] + bounds['height'] / 2

        valid_samples.append({
            "id": node.get('id'),
            "name": name.strip(),  # 这里对应你要求的 "query"
            "role": role,           # 保留 role 方便后续分析 (如 "button", "link")
            "bbox": [               # [x, y, w, h] 或者 [x1, y1, x2, y2]
                bounds['x'], 
                bounds['y'], 
                bounds['x'] + bounds['width'], 
                bounds['y'] + bounds['height']
            ],
            "point": [cx, cy]
        })

    # 开始遍历
    if 'root' in data:
        process_node(data['root'])

    # 生成最终数据集格式
    output_data = {
        "image_filename": image_filename,
        "image_size": [screen_width, screen_height],
        "sample_count": len(valid_samples),
        "test_samples": valid_samples # [image, query, bbox] 的集合
    }

    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"筛选完成: {len(valid_samples)} 个符合条件的元素。")

# --- 使用示例 ---
if __name__ == "__main__":
    # 替换你的实际路径
    input_file = "ui_tree.json"
    output_file = "grounding_dataset.json"
    img_path = "screenshot.png"
    
    if os.path.exists(input_file):
        filter_ui_tree(input_file, output_file, img_path)
    else:
        print("请提供正确的 json 文件路径")