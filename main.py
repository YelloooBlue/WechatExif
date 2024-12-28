# 根据微信命名规则添加照片的EXIF拍摄时间

import os
from PIL import Image
import piexif
from datetime import datetime, timedelta
from pymediainfo import MediaInfo
# pip install pillow piexif pymediainfo -i https://pypi.mirrors.ustc.edu.cn/simple

def get_exif_date_taken(image_path):
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

def get_exif_date_taken_video(video_path):
    """获取视频的EXIF拍摄时间"""
    media_info = MediaInfo.parse(video_path)
    for track in media_info.tracks:
        if track and track.track_type == "General":
            tagged_date = track.tagged_date
            if tagged_date:
                return tagged_date
    return None

def add_exif_date_taken(image_path, date_taken):
    """根据文件名添加EXIF拍摄时间，而不重新编码图像"""
    try:
        
        exif_dict = piexif.load(image_path) # 读取现有的EXIF数据
        exif_dict['Exif'][36867] = date_taken.encode('utf-8')  # # 更新拍摄时间 36867 是 DateTimeOriginal tag
        exif_bytes = piexif.dump(exif_dict) # 直接将更新后的EXIF数据写入图片文件中
        
        # 将EXIF数据写回文件，而不修改图片本身
        piexif.insert(exif_bytes, image_path)
        print(f"已添加EXIF拍摄时间: {date_taken} 到 {image_path}")
    except Exception as e:
        print(f"无法添加EXIF数据: {e}")


# ====================================== 提取文件名中的日期 ======================================

def extract_timestamp_from_filename_tail(filename, length=13, datetime_start=None, datetime_end=None):
    """从文件名尾部提取时间戳（倒数13位数字）"""

    base_name = os.path.splitext(filename)[0]
    timestamp = None
    if len(base_name) >= 13 and base_name[-13:].isdigit():
        timestamp = base_name[-13:]
    else:
        return None

    # 将时间戳转换为整数
    try:
        timestamp = int(timestamp)
    except ValueError:
        return None
        
    # 将时间戳转换为日期时间
    timestamp = datetime.fromtimestamp(timestamp / 1000)

    # 判断日期是否在指定范围内（可选）
    if datetime_start and timestamp < datetime_start:
        return None
    if datetime_end and timestamp > datetime_end:
        return None

    return timestamp

def extract_timestamp_from_filename_regex(filename, length=13, datetime_start=None, datetime_end=None):
    """从文件名中提取时间戳（正则表达式）"""
    import re
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


# ====================================== 主函数 ======================================

def main(folder_path):

    files = os.listdir(folder_path)
    with_exif_files = []
    no_exif_files = []
    for filename in files:
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')): # 过滤
            image_path = os.path.join(folder_path, filename)
            if get_exif_date_taken(image_path) is None:
                no_exif_files.append(filename)
            else:
                tmp = {"filename": filename, "date_taken": get_exif_date_taken(image_path)}
                with_exif_files.append(tmp)

        #视频
        if filename.lower().endswith(('.mp4', '.mov', '.avi', '.3gp')):
            video_path = os.path.join(folder_path, filename)
            if get_exif_date_taken_video(video_path) is None:
                no_exif_files.append(filename)
            else:
                tmp = {"filename": filename, "date_taken": get_exif_date_taken_video(video_path)}
                with_exif_files.append(tmp)

    print(f"有EXIF拍摄时间的文件数量: {len(with_exif_files)}")
    for file in with_exif_files:
        print(f"{file['filename']} \t {file['date_taken']}")
    
    print(f"无EXIF拍摄时间的文件数量: {len(no_exif_files)}")
    for i, file in enumerate(no_exif_files):
        print(f"{i+1}. {file}")

    if no_exif_files:
        user_input = input("是否根据文件名添加EXIF拍摄时间？(y/n): ")
        if user_input.lower() == 'y':
            for i, photo in enumerate(no_exif_files):
                image_path = os.path.join(folder_path, photo)
                # date_taken = extract_timestamp_from_filename_tail(photo) # 更稳健(读取文件名尾部的13位时间戳)
                date_taken = extract_timestamp_from_filename_regex(photo) # 更兼容(正则表达式提取时间戳)
                print(f"{i+1}. {date_taken}")                


                # if date_taken:
                #     add_exif_date_taken(image_path, date_taken.strftime('%Y:%m:%d %H:%M:%S'))

if __name__ == "__main__":
    folder_path = input("请输入照片文件夹路径: ")
    main(folder_path)
