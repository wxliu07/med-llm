import requests
import hashlib
import uuid
import time
import json
import os
from PIL import Image
import base64
import io

# -------------------------- 配置项 --------------------------
# 1. 请务必确认控制台该应用已绑定【图片翻译服务】
# 2. 粘贴后，确保引号内没有多余空格
APP_KEY = "22edc1db2a3413df"
APP_SECRET = "nPtqYG8xgUmg7PsgzW26gv6S5XLhW9PN"

IMAGE_DIR = "results/extracted_images"
OUTPUT_DIR = "results/translated_results"

# 文档要求中文必须是 zh-CHS，而不是 zh
FROM_LANG = "auto"
TO_LANG = "zh-CHS"

# 限制图片最大长宽，防止 Base64 过长导致 5003 错误
MAX_SIZE = 1024


# -------------------------------------------------------------

def init_dirs():
    dirs = [
        OUTPUT_DIR,
        os.path.join(OUTPUT_DIR, "translated_images"),
        os.path.join(OUTPUT_DIR, "json_results"),
        os.path.join(OUTPUT_DIR, "paragraph_texts")
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def compress_and_encode_image(image_path):
    """压缩图片并转为纯净的 Base64"""
    try:
        with Image.open(image_path) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")

            # 缩放图片
            w, h = img.size
            if max(w, h) > MAX_SIZE:
                scale = MAX_SIZE / max(w, h)
                new_w, new_h = int(w * scale), int(h * scale)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            img_byte_stream = io.BytesIO()
            img.save(img_byte_stream, format='JPEG', quality=75)
            img_byte_stream.seek(0)

            # 转 Base64 (确保无换行符)
            base64_data = base64.b64encode(img_byte_stream.read()).decode('utf-8').replace("\n", "")
            return base64_data
    except Exception as e:
        print(f"❌ 图片处理失败 {image_path}：{str(e)}")
        return None


def truncate(q):
    """官网规定的截断逻辑"""
    if q is None:
        return None
    size = len(q)
    return q if size <= 20 else q[:10] + str(size) + q[-10:]


def generate_sign(app_key, q, salt, curtime, app_secret):
    """生成签名 v3"""
    q_truncated = truncate(q)
    # 拼接顺序：应用ID + input + salt + curtime + 应用密钥
    sign_str = app_key + q_truncated + salt + curtime + app_secret

    # 调试用：如果还报202，可以取消下面这行的注释，查看签名原串是否正确
    # print(f"DEBUG SIGN STR: {sign_str}")

    return hashlib.sha256(sign_str.encode('utf-8')).hexdigest()


def translate_image(image_path):
    api_url = "https://openapi.youdao.com/ocrtransapi"

    base64_image = compress_and_encode_image(image_path)
    if not base64_image:
        return None

    # 生成参数
    # 使用无横线的UUID，更符合官方风格
    salt = str(uuid.uuid4()).replace("-", "")
    cur_time = str(int(time.time()))
    sign = generate_sign(APP_KEY, base64_image, salt, cur_time, APP_SECRET)

    data = {
        'q': base64_image,
        'from': FROM_LANG,
        'to': TO_LANG,
        'appKey': APP_KEY,
        'salt': salt,
        'curtime': cur_time,
        'sign': sign,
        'signType': 'v3',
        'type': '1',  # 必填，1=图片
        'renderImage': 'true',
        'docType': 'json',  # 明确指定 json
        'render': 1
    }

    try:
        # requests 自动处理 URL Encode
        response = requests.post(api_url, data=data, timeout=30)
        return response.json()
    except Exception as e:
        print(f"❌ 网络请求异常：{str(e)}")
        return None


def save_result(image_name, result):
    base_name = os.path.splitext(image_name)[0]

    # 保存 JSON
    with open(os.path.join(OUTPUT_DIR, "json_results", f"{base_name}.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 保存图片
    # 检查返回结果中是否有 renderImage 字段
    if "render_image" in result and result["render_image"]:
        try:
            # 1. 将返回的 Base64 字符串解码为二进制数据
            render_img_base64 = result["render_image"]
            image_binary = base64.b64decode(render_img_base64)

            # 2. 写入文件
            base_name = os.path.splitext(image_name)[0]
            output_path = os.path.join(OUTPUT_DIR, "translated_images", f"{base_name}_translated.jpg")

            with open(output_path, "wb") as f:
                f.write(image_binary)
            print(f"✅ 翻译后的图片已保存至: {output_path}")
        except Exception as e:
            print(f"❌ 保存渲染图片失败: {e}")

    # 保存文本
    texts = []
    if "resRegions" in result:  # 注意：文档里返回字段是 resRegions 不是 regions
        for region in result["resRegions"]:
            # 优先取 tranContent
            if "tranContent" in region:
                texts.append(region["tranContent"])
            elif "context" in region:
                texts.append(region["context"])

    if texts:
        with open(os.path.join(OUTPUT_DIR, "paragraph_texts", f"{base_name}.txt"), "w", encoding="utf-8") as f:
            f.write("\n\n".join(texts))
        print(f"✅ 翻译成功: {image_name}")
    else:
        print(f"⚠️  翻译完成但无文本: {image_name}")


def main():
    # 简单检查
    if len(APP_KEY) < 5 or len(APP_SECRET) < 5:
        print("❌ 错误：请先在代码顶部填入正确的 APP_KEY 和 APP_SECRET")
        return

    init_dirs()
    if not os.path.exists(IMAGE_DIR):
        print(f"❌ 目录不存在: {IMAGE_DIR}")
        return

    files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    print(f"🚀 开始处理 {len(files)} 张图片...")

    for i, f in enumerate(files):
        print(f"[{i + 1}/{len(files)}] {f} ...")
        res = translate_image(os.path.join(IMAGE_DIR, f))

        if res:
            if res.get("errorCode") == "0":
                save_result(f, res)
            else:
                print(f"❌ API 错误: Code={res.get('errorCode')} Msg={res.get('msg')}")
                if res.get("errorCode") == "202":
                    print("   👉 提示：请检查控制台是否开通了【图片翻译】服务，或检查Key/Secret是否复制了空格。")

        time.sleep(1)


if __name__ == "__main__":
    main()