from docx import Document
from docx.oxml.ns import qn
import os
from PIL import Image
import io


def extract_all_images_in_order(doc_path, output_dir="extracted_images"):
    """
    按顺序提取Word文档中的所有图片，并保存到指定目录
    :param doc_path: Word文档路径
    :param output_dir: 图片保存目录
    :return: 按顺序的图片信息列表（路径、位置索引）
    """
    # 1. 初始化配置
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    doc = Document(doc_path)
    image_info_list = []  # 存储按顺序的图片信息
    image_index = 0  # 图片顺序索引

    # 2. 遍历文档的所有段落（核心：按XML节点顺序提取）
    for para_idx, paragraph in enumerate(doc.paragraphs):
        # 遍历段落中的每个Run（文字/图片容器）
        for run_idx, run in enumerate(paragraph.runs):
            # 解析Run中的图片节点（w:drawing 是现代Word的图片标签）
            drawing_nodes = run._r.xpath(".//w:drawing")
            for draw_node in drawing_nodes:
                # 提取图片二进制数据
                blip = draw_node.xpath(".//a:blip/@r:embed")[0]  # 关联的图片ID
                image_part = doc.part.related_parts[blip]
                image_bytes = image_part.blob  # 图片二进制数据

                # 获取图片格式（默认png，兼容jpg/jpeg）
                img_ext = image_part.content_type.split("/")[-1].lower()
                img_ext = "jpg" if img_ext == "jpeg" else img_ext

                # 保存图片
                img_filename = f"image_{image_index:03d}.{img_ext}"
                img_save_path = os.path.join(output_dir, img_filename)

                # 写入图片文件（处理PIL兼容问题）
                try:
                    with Image.open(io.BytesIO(image_bytes)) as img:
                        img.save(img_save_path)
                except:
                    # 直接写入二进制（兼容特殊格式）
                    with open(img_save_path, "wb") as f:
                        f.write(image_bytes)

                # 记录图片信息（顺序索引、位置、路径）
                image_info = {
                    "index": image_index,
                    "paragraph_idx": para_idx,
                    "run_idx": run_idx,
                    "save_path": img_save_path,
                    "filename": img_filename
                }
                image_info_list.append(image_info)
                image_index += 1

    # 3. 兼容旧版Word的w:pict标签（老式图片嵌入）
    pict_nodes = doc.element.body.xpath(".//w:pict")
    for pict_idx, pict_node in enumerate(pict_nodes):
        blip_nodes = pict_node.xpath(".//v:imagedata/@r:id")
        for blip_id in blip_nodes:
            if blip_id in doc.part.related_parts:
                image_part = doc.part.related_parts[blip_id]
                image_bytes = image_part.blob
                img_ext = image_part.content_type.split("/")[-1].lower()
                img_ext = "jpg" if img_ext == "jpeg" else img_ext

                img_filename = f"image_{image_index:03d}.{img_ext}"
                img_save_path = os.path.join(output_dir, img_filename)

                with open(img_save_path, "wb") as f:
                    f.write(image_bytes)

                image_info = {
                    "index": image_index,
                    "type": "pict (old style)",
                    "save_path": img_save_path,
                    "filename": img_filename
                }
                image_info_list.append(image_info)
                image_index += 1

    # 4. 输出提取结果
    print(f"共提取 {len(image_info_list)} 张图片，保存至：{output_dir}")
    for info in image_info_list:
        print(f"顺序 {info['index']:03d} | 保存路径：{info['save_path']}")

    return image_info_list


# ------------------- 调用示例 -------------------
if __name__ == "__main__":
    # 配置参数
    WORD_PATH = "results/听力1-6单元academic listening-12篇文本.docx"  # 你的Word文档路径
    OUTPUT_DIR = "results/extracted_images"  # 图片保存目录

    # 执行提取
    extracted_images = extract_all_images_in_order(WORD_PATH, OUTPUT_DIR)

    # 验证顺序：打印所有图片的顺序索引和路径
    print("\n按文档顺序的图片列表：")
    for img in extracted_images:
        print(f"第{img['index'] + 1}张图：{img['save_path']}")