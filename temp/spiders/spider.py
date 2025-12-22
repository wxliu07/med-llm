import requests
import time
import hashlib
import urllib.parse
import csv  # 新增：用于导出数据
from functools import reduce

# === 配置区域 ===
TARGET_MID = 349950942
SESSDATA = ("008cfcab%2C1781361922%2Ccbf33%2Ac2CjBcAse8isXJ8CyCQvasnznq3tLJ1F_9_VL70fKWbopYRBUL6JhIzc_WZVPkuf8"
            "-kcISVnMyOU9wZ2FFM2RGRFhveldMZEU5dk1qeFlIYllmbHM1TE5GMVY1eHFzbmhiWlNnX0dKZVpQdUxHaEtGVTViYU5GWENjMmx6Sjh3bzZZaDBkQy16ZkdBIIEC")
SAVE_FILENAME = "bilibili_videos.csv"  # 结果保存的文件名
# =================

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 "
              "Safari/537.36")

# --- WBI 签名算法 (保持不变，省略部分以节省篇幅，请保留原有的WBI函数) ---
mixinKeyEncTab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]


def getMixinKey(orig: str):
    return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, '')[:32]


def encWbi(params: dict, img_key: str, sub_key: str):
    mixin_key = getMixinKey(img_key + sub_key)
    curr_time = round(time.time())
    params['wts'] = curr_time
    params = dict(sorted(params.items()))
    query = urllib.parse.urlencode(params)
    wb_key = hashlib.md5((query + mixin_key).encode()).hexdigest()
    return params | {'w_rid': wb_key}


def get_wbi_keys(sess):
    try:
        resp = sess.get('https://api.bilibili.com/x/web-interface/nav', headers={'User-Agent': USER_AGENT})
        resp.raise_for_status()
        json_content = resp.json()
        wbi_img = json_content['data']['wbi_img']
        img_url = wbi_img['img_url']
        sub_url = wbi_img['sub_url']
        return img_url.split('/')[-1].split('.')[0], sub_url.split('/')[-1].split('.')[0]
    except Exception as e:
        print(f"获取 WBI Key 失败: {e}")
        return None, None


# --- 主逻辑 (核心修改部分) ---
def fetch_user_videos(mid):
    if "这里填入" in SESSDATA:
        print("错误：你还没有填写 SESSDATA！")
        return

    sess = requests.Session()
    sess.cookies.set('SESSDATA', SESSDATA, domain='.bilibili.com')
    sess.headers.update({'User-Agent': USER_AGENT, 'Referer': 'https://www.bilibili.com/'})

    img_key, sub_key = get_wbi_keys(sess)
    if not img_key or not sub_key:
        return

    page = 1
    page_size = 30
    all_videos = []  # 用于存储所有抓取到的视频

    print(f"开始全量抓取 UP主 (MID: {mid})...\n")

    while True:
        print(f"正在抓取第 {page} 页...")

        params = {
            'mid': mid,
            'ps': page_size,
            'tid': 0,
            'pn': page,  # 这里是控制翻页的核心参数
            'keyword': '',
            'order': 'pubdate',
            'order_avoided': 'true'
        }

        signed_params = encWbi(params, img_key, sub_key)

        try:
            resp = sess.get('https://api.bilibili.com/x/space/wbi/arc/search', params=signed_params)
            data = resp.json()
        except Exception as e:
            print(f"网络请求异常: {e}")
            break

        if data['code'] != 0:
            print(f"API 报错: {data['message']}")
            break

        vlist = data['data']['list']['vlist']

        # === 核心终止条件 ===
        # 如果 vlist 是空的，说明上一页已经是最后一页了，这里没数据了
        if not vlist:
            print(f"第 {page} 页为空，抓取结束。")
            break
        # ==================

        for video in vlist:
            # 提取关键信息
            item = {
                'bvid': video['bvid'],
                'title': video['title'],
                'description': video['description'],
                'created': video['created'],  # 发布时间戳
                'length': video['length'],
                'play': video['play']
            }
            all_videos.append(item)

        print(f"  - 本页获取 {len(vlist)} 条，累计 {len(all_videos)} 条")

        # === 翻页与延时 ===
        page += 1
        # 必须休眠！请求太快会触发 -412 或 -403 错误
        time.sleep(2)

        # --- 保存结果 ---
    print(f"\n抓取完成，共 {len(all_videos)} 个视频。正在写入 CSV...")

    try:
        with open(SAVE_FILENAME, mode='w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['bvid', 'title', 'description', 'created', 'length', 'play'])
            writer.writeheader()
            writer.writerows(all_videos)
        print(f"成功！文件已保存为: {SAVE_FILENAME}")
    except Exception as e:
        print(f"保存文件失败: {e}")


if __name__ == '__main__':
    fetch_user_videos(TARGET_MID)