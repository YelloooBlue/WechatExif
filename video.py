import subprocess
import json
import re
import os
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# pip install tqdm
# install exiftool from https://exiftool.org/

def get_exif_data(file_path):
    # 调用 ExifTool
    result = subprocess.run(['exiftool', '-json', file_path], capture_output=True, text=True)
    
    # 检查是否有错误
    if result.returncode != 0:
        print("Error:", result.stderr)
        return None
    
    # 解析 JSON 输出
    exif_data = json.loads(result.stdout)
    return exif_data

# ====================================== 【视频】EXIF - 获取和设置拍摄时间 ======================================

def get_video_exif_date(file_path):
    """获取视频文件的拍摄时间"""
    exif_data = get_exif_data(file_path)
    if exif_data:
        # 获取视频文件的拍摄时间
        create_date = exif_data[0].get('CreateDate')
        media_create_date = exif_data[0].get('MediaCreateDate')
        track_create_date = exif_data[0].get('TrackCreateDate')
        
        # 优先使用 MediaCreateDate
        date = None
        if media_create_date:
            date = media_create_date
        elif create_date:
            date = create_date
        elif track_create_date:
            date = track_create_date

        # 转换为 datetime 对象, 并确定不是0000:00:00 00:00:00
        if date and date != '0000:00:00 00:00:00':
            date = datetime.strptime(date, '%Y:%m:%d %H:%M:%S')
            return date
        
    return None
        
def set_video_exif_date(file_path, date_str):
    """设置视频文件的拍摄时间"""

    # 调用 ExifTool
    result = subprocess.run(['exiftool', file_path, f'-CreateDate={date_str}', f'-MediaCreateDate={date_str}', f'-MediaModifyDate={date_str}', f'-TrackCreateDate={date_str}', f'-TrackModifyDate={date_str}', '-overwrite_original', '-xmp='], capture_output=True, text=True)
    
    # 检查是否有错误
    if result.returncode != 0:
        print(f"无法添加EXIF数据: {result.stderr} {file_path}")

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

def process_file(video_path):
    """处理单个文件，获取EXIF日期并根据文件名设置EXIF日期"""
    exif_date = get_video_exif_date(video_path)
    if exif_date:
        return (os.path.basename(video_path), exif_date, None)
    else:
        date_taken = extract_timestamp_from_filename_regex(os.path.basename(video_path))
        if date_taken:
            # !!! 与照片不同，视频需要将时间戳转换为UTC时区
            utc_time = datetime.fromtimestamp(date_taken.timestamp(), tz=timezone.utc)
            set_video_exif_date(video_path, utc_time.strftime('%Y:%m:%d %H:%M:%S'))
            
            return (os.path.basename(video_path), None, date_taken)
    return (os.path.basename(video_path), None, None)

# ====================================== 主函数 ======================================

def main(folder_path):
    files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv'))]
    
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
    for file in no_exif_files:
        print(f"{file[0]} \t {file[1]}")

if __name__ == "__main__":
    folder_path = input("请输入文件夹路径: ")
    main(folder_path)
