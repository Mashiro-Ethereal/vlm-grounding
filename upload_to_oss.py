import os
import mimetypes
import alibabacloud_oss_v2 as oss
from tqdm import tqdm

# ================= 配置区域 =================
# 阿里云 OSS 配置
REGION = "cn-beijing"
BUCKET_NAME = 'gui-test-zxh-0129'
ENDPOINT = f'oss-{REGION}.aliyuncs.com'

# 本地数据集根目录 (请修改为你整理好的那个文件夹路径)
LOCAL_DATASET_ROOT = '/Users/zhangxiuhui/Desktop/project/vlm-grounding/GUI_Grounding_Benchmark' 

# OSS 上的目标前缀 (也就是文件夹名)
# 例如设置为 'benchmark_v1/'，那么文件就会传到 gui-test-zxh-0129/benchmark_v1/ 下
OSS_TARGET_PREFIX = 'gui_grounding_benchmark_v1/' 
# ===========================================

def main():
    # 1. 初始化 OSS 客户端
    # 确保你的环境变量 OSS_ACCESS_KEY_ID 和 OSS_ACCESS_KEY_SECRET 已设置
    credentials_provider = oss.credentials.EnvironmentVariableCredentialsProvider()
    cfg = oss.config.load_default()
    cfg.credentials_provider = credentials_provider
    cfg.region = REGION
    cfg.endpoint = ENDPOINT
    client = oss.Client(cfg)

    print(f"🚀 开始准备上传...")
    print(f"   本地目录: {LOCAL_DATASET_ROOT}")
    print(f"   OSS 目标: oss://{BUCKET_NAME}/{OSS_TARGET_PREFIX}")

    # 2. 收集所有需要上传的文件
    files_to_upload = []
    if not os.path.exists(LOCAL_DATASET_ROOT):
        print(f"❌ 错误: 本地路径不存在 -> {LOCAL_DATASET_ROOT}")
        return

    for root, dirs, files in os.walk(LOCAL_DATASET_ROOT):
        for file in files:
            # 过滤掉系统隐藏文件 (如 .DS_Store)
            if file.startswith('.'):
                continue
                
            local_path = os.path.join(root, file)
            
            # 计算 OSS 上的 Key (保持相对目录结构)
            # 例如: LOCAL_ROOT/images/01.png -> images/01.png
            relative_path = os.path.relpath(local_path, LOCAL_DATASET_ROOT)
            
            # 拼接 OSS 前缀: benchmark_v1/images/01.png
            # 注意：Windows下路径分隔符可能需要替换为 '/'
            oss_key = os.path.join(OSS_TARGET_PREFIX, relative_path).replace("\\", "/")
            
            files_to_upload.append((local_path, oss_key))

    print(f"📦 共发现 {len(files_to_upload)} 个文件，开始上传...\n")

    # 3. 批量上传
    success_count = 0
    fail_count = 0

    # 使用 tqdm 显示进度条
    for local_path, oss_key in tqdm(files_to_upload, desc="Uploading", unit="file"):
        try:
            # 自动猜测 Content-Type (MIME类型)
            content_type, _ = mimetypes.guess_type(local_path)
            if content_type is None:
                content_type = 'application/octet-stream' # 默认二进制流

            # 构造上传请求
            # 使用 put_object_from_file 接口
            request = oss.PutObjectRequest(
                bucket=BUCKET_NAME,
                key=oss_key,
                acl='public-read', # 设置为公共读，方便后续评测代码直接通过 URL 访问图片
                headers={
                    'Content-Type': content_type
                }
            )

            result = client.put_object_from_file(request, local_path)
            
            if result.status_code == 200:
                success_count += 1
            else:
                print(f"\n❌ 上传失败 [{oss_key}]: Status {result.status_code}")
                fail_count += 1

        except Exception as e:
            print(f"\n❌ 异常错误 [{oss_key}]: {e}")
            fail_count += 1

    # 4. 总结
    print("\n" + "="*40)
    print(f"✅ 上传完成!")
    print(f"   成功: {success_count}")
    print(f"   失败: {fail_count}")
    
    # 打印一个示例 URL 供你验证
    if len(files_to_upload) > 0:
        example_key = files_to_upload[0][1]
        print(f"   示例文件链接: https://{BUCKET_NAME}.{ENDPOINT}/{example_key}")
    print("="*40)

if __name__ == "__main__":
    main()