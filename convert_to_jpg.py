"""
批量将 TIF/TIFF 图片转换为 JPG 格式，输出到同级 converted 文件夹。
用法：修改下方 INPUT_DIR 为你的图片文件夹路径，然后运行脚本。
"""
import os
from PIL import Image

# ===== 在这里填入图片文件夹路径 =====
INPUT_DIR = r'C:\Users\13774\Desktop\DATA\TEM\Ag2Se'
# 例如：INPUT_DIR = r'C:\Users\13774\Python\some_folder\images'

OUTPUT_FORMAT = 'JPEG'  # JPEG 或 BMP
OUTPUT_EXT = '.jpg'     # .jpg 或 .bmp
QUALITY = 95            # JPEG 质量 (1-100)，仅对 JPEG 有效

SUPPORTED_INPUT = ('.tif', '.tiff', '.png', '.bmp')


def main():
    if not INPUT_DIR:
        print('请先在脚本中填入 INPUT_DIR 路径。')
        return

    output_dir = os.path.join(os.path.dirname(INPUT_DIR.rstrip(os.sep)), 'converted')
    os.makedirs(output_dir, exist_ok=True)

    files = [f for f in os.listdir(INPUT_DIR)
             if f.lower().endswith(SUPPORTED_INPUT)]

    if not files:
        print(f'在 {INPUT_DIR} 中未找到支持的图片文件。')
        return

    print(f'找到 {len(files)} 张图片，开始转换...')

    for f in files:
        src = os.path.join(INPUT_DIR, f)
        name = os.path.splitext(f)[0] + OUTPUT_EXT
        dst = os.path.join(output_dir, name)

        img = Image.open(src)
        if img.mode in ('I;16', 'I;16B', 'F'):
            import numpy as np
            arr = np.array(img, dtype=float)
            arr = (arr - arr.min()) / (arr.max() - arr.min() + 1e-9) * 255
            img = Image.fromarray(arr.astype('uint8'))
        if img.mode != 'RGB':
            img = img.convert('RGB')

        if OUTPUT_FORMAT == 'JPEG':
            img.save(dst, OUTPUT_FORMAT, quality=QUALITY)
        else:
            img.save(dst, OUTPUT_FORMAT)

        print(f'  {f} -> {name}')

    print(f'\n完成！共转换 {len(files)} 张图片。')
    print(f'输出目录：{output_dir}')


if __name__ == '__main__':
    main()
