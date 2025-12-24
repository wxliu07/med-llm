import os
from pathlib import Path
from dotenv import load_dotenv
from datasets import load_dataset
from huggingface_hub import login, snapshot_download


def setup_environment(use_mirror=True):
    """配置环境：Token、镜像站及加速器"""
    load_dotenv()
    token = os.getenv("HUGGING_FACE_TOKEN")

    if not token:
        raise ValueError("错误：未在 .env 文件中找到 HUGGING_FACE_TOKEN")

    login(token=token)

    if use_mirror:
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
        print("已启用 HF 镜像站加速")

    # 开启极速下载模式（底层由 Rust 编写，远快于默认的 Python 下载器）
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
    print("已开启 HF_TRANSFER 并发加速模式")


def download_hf_dataset(repo_id, config_name=None, cache_dir="cache"):
    """
    下载数据集。datasets 库默认自带 tqdm 进度条。
    """
    print(f"开始处理数据集: {repo_id} (Config: {config_name})")
    try:
        ds = load_dataset(
            repo_id,
            config_name,
            cache_dir=cache_dir,
            num_proc=4  # 多进程处理提升加载速度
        )
        print(f"数据集加载成功，样本量: {len(ds['train'])}")
        return ds
    except Exception as e:
        print(f"数据集下载失败: {e}")
        return None


def download_hf_model(model_id, cache_dir="models"):
    """
    下载大模型。snapshot_download 提供更直观的进度反馈。
    """
    print(f"开始下载模型: {model_id}")
    try:
        model_path = snapshot_download(
            repo_id=model_id,
            cache_dir=cache_dir,
            ignore_patterns=["*.msgpack", "*.h5", "*.ot"],  # 排除非必要格式节省空间
            resume_download=True
        )
        print(f"模型已存至: {model_path}")
        return model_path
    except Exception as e:
        print(f"模型下载失败: {e}")
        return None


def main():
    # 1. 初始化
    setup_environment(use_mirror=True)

    # 2. 数据集下载示例 (MedTrinity)
    # dataset_id = "UCSC-VLAA/MedTrinity-25M"
    # config = "25M_demo"
    # ds = download_hf_dataset(dataset_id, config, cache_dir="./data/cache")

    # 3. 大模型下载示例 (例如你微调可能用到的医学视觉模型，此处以 Phi-3-vision 为例)
    # model_id = "microsoft/Phi-3-vision-128k-instruct"
    # download_hf_model(model_id, cache_dir="./models")


if __name__ == "__main__":
    main()
