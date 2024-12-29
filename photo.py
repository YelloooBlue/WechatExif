import os
from datetime import datetime
from PIL import Image
import piexif
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# pip install pillow piexif tqdm -i https://pypi.mirrors.ustc.edu.cn/simple

# ====================================== 【照片】EXIF - DateTimeOriginal ======================================

def get_photo_exif_date(image_path):
    """获取图像的EXIF拍摄时间"""
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        if exif_data is not None:
            for tag, value in exif_data.items():
                if tag == 36867:  # Tag 36867 是 DateTimeOriginal
                    return value
    except Exception as e:
        print(f"无法读取EXIF数据: {e} {image_path}")
    return None

def set_photo_exif_date(image_path, date_taken):
    """根据文件名添加EXIF拍摄时间，而不重新编码图像"""
    try:
        exif_dict = piexif.load(image_path)  # 读取现有的EXIF数据
        exif_dict['Exif'][36867] = date_taken.encode('utf-8')  # 更新拍摄时间
        exif_bytes = piexif.dump(exif_dict)  # 直接将更新后的EXIF数据写入图片文件中
        
        # 将EXIF数据写回文件，而不修改图片本身
        piexif.insert(exif_bytes, image_path)
        # print(f"已添加EXIF拍摄时间: {date_taken} 到 {image_path}")
    except Exception as e:
        print(f"无法添加EXIF数据: {e} {image_path}")

# ====================================== 提取文件名中的日期 ======================================

def extract_timestamp_from_filename_regex(filename, length=13, datetime_start=None, datetime_end=None):
    """从文件名中提取时间戳（正则表达式）"""
    pattern = re.compile(r'(\d{%d})' % length)
    match = pattern.search(filename)
    if match:
        timestamp = match.group(1)
        try:
            timestamp = int(timestamp)
        except ValueError:
            return None
        timestamp = datetime.fromtimestamp(timestamp / 1000)
        
        # 判断日期是否在指定范围内（可选）
        if datetime_start and timestamp < datetime_start:
            return None
        if datetime_end and timestamp > datetime_end:
            return None

        return timestamp
    return None

# ====================================== 处理单个文件 ======================================

def process_file(image_path):
    """处理单个文件，获取EXIF日期并根据文件名设置EXIF日期"""
    exif_date = get_photo_exif_date(image_path)
    if exif_date:
        return (os.path.basename(image_path), exif_date, None)
    else:
        date_taken = extract_timestamp_from_filename_regex(os.path.basename(image_path))
        if date_taken:
            set_photo_exif_date(image_path, date_taken.strftime('%Y:%m:%d %H:%M:%S'))
            return (os.path.basename(image_path), None, date_taken)
    return (os.path.basename(image_path), None, None)

# ====================================== 主函数 ======================================

def main(folder_path):
    files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
    
    with_exif_files = []
    no_exif_files = []

    # 使用多线程处理文件
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(process_file, os.path.join(folder_path, filename)): filename for filename in files}
        
        for future in tqdm(as_completed(futures), total=len(futures), desc="处理文件"):
            filename, exif_date, date_taken = future.result()
            if exif_date:
                with_exif_files.append((filename, exif_date))
            else:
                no_exif_files.append((filename, date_taken))

    print(f"有EXIF拍摄时间的文件数量: {len(with_exif_files)}")
    for file in with_exif_files:
        print(f"{file[0]} \t {file[1]}")
    
    print(f"无EXIF拍摄时间的文件数量: {len(no_exif_files)}")
    for i, file in enumerate(no_exif_files):
        print(f"{i+1}. {file[0]}")

if __name__ == "__main__":
    folder_path = input("请输入文件夹路径: ")
    main(folder_path)
