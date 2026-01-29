# OSWorld-Desktopd 数据格式规范 v1.0

## 概述

本规范定义了 SFT 训练数据的格式标准。核心设计理念：
- **以 Step 为中心**：每个样本是一个完整的 trajectory（步骤序列）
- **用于 SFT 刷分**：记录成功完成任务的路径，用于训练模型

## 数据流程

```
Task → [Step 1] → [Step 2] → ... → [Step N] → Success/Fail
         ↓           ↓                ↓
     screenshot   screenshot      screenshot
     ui_tree      ui_tree         ui_tree
     action       action          action
```

---

## 目录结构

```
dataset/
├── metadata.json                    # 数据集元信息
├── trajectories/
│   ├── {trajectory_id}/
│   │   ├── task.json                # 任务描述
│   │   ├── steps/
│   │   │   ├── 000/
│   │   │   │   ├── screenshot.png   # 执行动作前的截图
│   │   │   │   ├── ui_tree.json     # UI 布局树
│   │   │   │   └── action.json      # 执行的动作
│   │   │   ├── 001/
│   │   │   │   └── ...
│   │   │   └── ...
│   │   ├── result.json              # 最终结果
│   │   └── final_screenshot.png     # 最终状态截图
│   └── ...
└── index.json                       # trajectory 索引
```

---

## 1. Task 定义 (task.json)

```json
{
  "task_id": "chrome_open_google",
  "instruction": "Open Chrome and navigate to google.com",
  "osworld_task_id": "chrome_001",
  "application": "chrome",
  "difficulty": "easy",
  "expected_steps": 3
}
```

---

## 2. Step 定义

每个 step 包含三个部分：当前状态（screenshot + ui_tree）和要执行的动作（action）。

### 2.1 Screenshot 规范

- **格式**: PNG
- **分辨率**: 1920x1080
- **文件名**: `screenshot.png`
- **必需**: 每个 step 都需要提供

### 2.2 UI Tree 规范 (ui_tree.json)

```json
{
  "timestamp": "2025-01-29T10:30:00Z",
  "screen": {
    "width": 1920,
    "height": 1080
  },
  "root": {
    "id": "node_0",
    "role": "desktop",
    "name": "",
    "bounds": {"x": 0, "y": 0, "width": 1920, "height": 1080},
    "children": [
      {
        "id": "node_1",
        "role": "window",
        "name": "Google Chrome",
        "bounds": {"x": 100, "y": 50, "width": 1200, "height": 800},
        "states": ["focused", "active"],
        "children": [...]
      }
    ]
  }
}
```

### 2.3 Action 规范 (action.json)

```json
{
  "step_index": 0,
  "action_type": "click",
  "parameters": {
    "x": 500,
    "y": 300,
    "button": "left"
  },
  "target_element": {
    "id": "node_15",
    "role": "button",
    "name": "Search"
  },
  "reasoning": "Click the search button to submit query"
}
```

#### Action Types

| action_type | parameters | 说明 |
|-------------|------------|------|
| `click` | `{x, y, button}` | 鼠标点击 |
| `double_click` | `{x, y}` | 双击 |
| `right_click` | `{x, y}` | 右键点击 |
| `type` | `{text}` | 输入文本 |
| `hotkey` | `{keys: ["ctrl", "c"]}` | 快捷键 |
| `scroll` | `{x, y, direction, amount}` | 滚动 |
| `drag` | `{start_x, start_y, end_x, end_y}` | 拖拽 |
| `wait` | `{seconds}` | 等待 |

---

## 3. Result 定义 (result.json)

```json
{
  "trajectory_id": "traj_001",
  "success": true,
  "total_steps": 5,
  "completion_time_ms": 12500,
  "error_message": null,
  "model_info": {
    "name": "qwen-vl-7b",
    "version": "1.0"
  }
}
```

---

## 4. 完整示例

### 任务：打开 Chrome 并访问 google.com

```
trajectories/traj_chrome_001/
├── task.json
├── steps/
│   ├── 000/
│   │   ├── screenshot.png      # 桌面初始状态
│   │   ├── ui_tree.json        # 桌面 UI 树
│   │   └── action.json         # click Chrome icon
│   ├── 001/
│   │   ├── screenshot.png      # Chrome 已打开
│   │   ├── ui_tree.json        # Chrome 窗口 UI 树
│   │   └── action.json         # click address bar
│   ├── 002/
│   │   ├── screenshot.png      # 地址栏已聚焦
│   │   ├── ui_tree.json
│   │   └── action.json         # type "google.com"
│   └── 003/
│       ├── screenshot.png      # 已输入 URL
│       ├── ui_tree.json
│       └── action.json         # hotkey ["enter"]
├── final_screenshot.png        # Google 首页已加载
└── result.json                 # success: true
```

---

## 5. Index 文件 (index.json)

```json
{
  "version": "1.0",
  "total_trajectories": 100,
  "successful": 85,
  "failed": 15,
  "trajectories": [
    {
      "id": "traj_chrome_001",
      "task_id": "chrome_open_google",
      "success": true,
      "steps": 4,
      "application": "chrome"
    },
    ...
  ]
}
```

---

## 6. SFT 训练数据转换

将 trajectory 转换为 SFT 训练格式：

```python
# 每个 step 生成一个训练样本
for step in trajectory.steps:
    training_sample = {
        "input": {
            "instruction": task.instruction,
            "screenshot": step.screenshot,  # 或 base64
            "ui_tree": step.ui_tree,
            "history": previous_actions      # 之前的动作序列
        },
        "output": {
            "action": step.action,
            "reasoning": step.action.reasoning
        }
    }
```

---

## 7. UINode 字段参考

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | ✓ | 节点 ID: `node_{index}` |
| `role` | string | ✓ | UI 角色 |
| `name` | string | ✓ | 显示文本 |
| `bounds` | object | ✓ | `{x, y, width, height}` |
| `states` | array | ✗ | 状态列表 |
| `children` | array | ✗ | 子节点 |

### Role 枚举

`desktop`, `window`, `dialog`, `panel`, `toolbar`, `menubar`, `menu`, `menuitem`, `button`, `checkbox`, `radiobutton`, `textfield`, `textarea`, `combobox`, `listbox`, `listitem`, `tab`, `tabpanel`, `treeview`, `treeitem`, `table`, `tablecell`, `scrollbar`, `slider`, `progressbar`, `label`, `link`, `image`, `icon`, `separator`, `tooltip`, `statusbar`, `taskbar`, `unknown`

### States 枚举

`focused`, `selected`, `checked`, `disabled`, `expanded`, `collapsed`, `visible`, `hidden`, `editable`, `readonly`, `pressed`, `active`
