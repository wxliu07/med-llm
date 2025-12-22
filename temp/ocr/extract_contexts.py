import json
import os

# -------------------------- 配置项 --------------------------
JSON_DIR = "results/translated_results/json_results"  # 存放 JSON 的目录
TEXT_OUTPUT_DIR = "results/translated_results/extracted_contexts"  # 提取后的文本存放目录


# -----------------------------------------------------------

def extract_contexts():
    # 1. 检查并创建输出目录
    if not os.path.exists(TEXT_OUTPUT_DIR):
        os.makedirs(TEXT_OUTPUT_DIR)
        print(f"📁 已创建输出目录: {TEXT_OUTPUT_DIR}")

    # 2. 获取所有 json 文件
    json_files = [f for f in os.listdir(JSON_DIR) if f.lower().endswith('.json')]

    if not json_files:
        print(f"⚠️  在 {JSON_DIR} 中没有找到 JSON 文件。")
        return

    print(f"🚀 开始处理 {len(json_files)} 个文件...")

    for filename in json_files:
        json_path = os.path.join(JSON_DIR, filename)

        try:
            with open(json_path, 'r', encoding='utf-8') as jf:
                data = json.load(jf)

            # 3. 提取 resRegions 中的 context
            # 根据官方文档，信息存储在 resRegions 列表中
            if "resRegions" in data:
                # 提取所有非空的 context 字段
                contexts = []
                for region in data["resRegions"]:
                    text = region.get("context", "").strip()
                    if text:
                        contexts.append(text)

                # 4. 保存到 txt 文件
                if contexts:
                    # 文件名保持一致，仅后缀改为 .txt
                    txt_filename = os.path.splitext(filename)[0] + ".txt"
                    txt_path = os.path.join(TEXT_OUTPUT_DIR, txt_filename)

                    with open(txt_path, 'w', encoding='utf-8') as tf:
                        tf.write("\n\n".join(contexts))

                    print(f"✅ 处理成功: {filename} -> {txt_filename}")
                else:
                    print(f"⚠️  跳过: {filename} (未发现 context 内容)")
            else:
                print(f"❌ 错误: {filename} 格式不正确，缺少 resRegions 字段")

        except Exception as e:
            print(f"❌ 读取文件 {filename} 时发生错误: {str(e)}")

    print(f"\n✨ 处理完成！所有原文已保存至: {TEXT_OUTPUT_DIR}")


if __name__ == "__main__":
    extract_contexts()