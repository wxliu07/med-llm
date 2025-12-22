import requests
import hashlib
import uuid
import time
import os
import re

# -------------------------- 配置项 --------------------------
APP_KEY = "22edc1db2a3413df".strip()
APP_SECRET = "nPtqYG8xgUmg7PsgzW26gv6S5XLhW9PN".strip()

INPUT_DIR = "results/translated_results/extracted_contexts"
AUDIO_OUTPUT_DIR = "results/translated_results/audio_output"

VOICE_NAME = "youxiaomei"
SPEED = "1"
VOLUME = "1.0"

# 单次 API 请求建议的最大字节长度（留出余量，官方限制 2048）
MAX_BYTE_LEN = 1500


# -----------------------------------------------------------

def truncate(q):
    if q is None: return None
    size = len(q)
    return q if size <= 20 else q[:10] + str(size) + q[-10:]


def generate_sign(app_key, q, salt, curtime, app_secret):
    input_str = truncate(q)
    sign_str = app_key + input_str + salt + curtime + app_secret
    return hashlib.sha256(sign_str.encode('utf-8')).hexdigest()


def split_text(text):
    """
    按句子切分长文本，确保每段都不超过 MAX_BYTE_LEN。
    """
    # 按照 句号、问号、感叹号、换行符切分，保留分隔符
    sentences = re.split(r'([.!?。\n\r])', text)
    # 将分隔符并回前一句
    new_sentences = []
    for i in range(0, len(sentences) - 1, 2):
        new_sentences.append(sentences[i] + sentences[i + 1])
    if len(sentences) % 2 == 1:
        new_sentences.append(sentences[-1])

    chunks = []
    current_chunk = ""
    for s in new_sentences:
        # 检查当前块加上新句子后的字节长度
        if len((current_chunk + s).encode('utf-8')) <= MAX_BYTE_LEN:
            current_chunk += s
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = s
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks


def get_tts_audio(text):
    """调用 API 返回音频的二进制数据"""
    api_url = "https://openapi.youdao.com/ttsapi"
    salt = str(uuid.uuid4())
    cur_time = str(int(time.time()))

    data = {
        'q': text,
        'appKey': APP_KEY,
        'salt': salt,
        'curtime': cur_time,
        'sign': generate_sign(APP_KEY, text, salt, cur_time, APP_SECRET),
        'signType': 'v3',
        'voiceName': VOICE_NAME,
        'format': 'mp3',
        'speed': SPEED,
        'volume': VOLUME
    }

    try:
        response = requests.post(api_url, data=data, timeout=30)
        if 'audio' in response.headers.get('Content-Type', ''):
            return response.content
        else:
            print(f"❌ 分段请求失败: {response.json()}")
            return None
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return None


def batch_process_tts():
    if not os.path.exists(AUDIO_OUTPUT_DIR):
        os.makedirs(AUDIO_OUTPUT_DIR)

    txt_files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.txt')]

    if not txt_files:
        print(f"⚠️ 未找到文件")
        return

    # 这里你之前写的是 [1:]，表示跳过第一个文件，我保留了你的逻辑
    for filename in txt_files[3:]:
        txt_path = os.path.join(INPUT_DIR, filename)
        audio_filename = os.path.splitext(filename)[0] + ".mp3"
        audio_path = os.path.join(AUDIO_OUTPUT_DIR, audio_filename)

        with open(txt_path, 'r', encoding='utf-8') as f:
            full_text = f.read().strip()

        if not full_text:
            continue

        print(f"🎙️ 正在处理: {filename} (长度: {len(full_text)})")

        # 1. 切分文本
        text_chunks = split_text(full_text)
        print(f"   已切分为 {len(text_chunks)} 个片段进行合成...")

        # 2. 逐段获取音频并合并写入
        with open(audio_path, 'wb') as final_audio:
            for i, chunk in enumerate(text_chunks):
                print(f"   -> 正在合成片段 {i + 1}/{len(text_chunks)}...")
                audio_data = get_tts_audio(chunk)
                if audio_data:
                    final_audio.write(audio_data)
                    # 避免触发频率限制
                    time.sleep(0.4)
                else:
                    print(f"   ⚠️ 片段 {i + 1} 合成中断")

        print(f"✅ 合并保存成功: {audio_filename}\n")


if __name__ == "__main__":
    batch_process_tts()