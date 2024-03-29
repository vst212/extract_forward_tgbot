import os.path
import glob
import asyncio
import zipfile
import io
from concurrent.futures import ProcessPoolExecutor

from PIL import Image

from process_images import generate_gif, merge_multi_images, add_text, open_image_from_various, merge_images_according_array


async def test(img_list: list[str], array=None):
    duration_time = 3000
    middle_interval = 10
    text = "#ll示例文字"
    loop = asyncio.get_event_loop()

    is_gif = False
    # 测试
    with ProcessPoolExecutor() as pool:
        # 使用 ProcessPoolExecutor，也就是新起进程执行图片处理
        if array:
            gif_io = await loop.run_in_executor(pool, merge_images_according_array, middle_interval, array)
        else:
            if len(img_list) == 1:
                # 添加文本
                gif_io = await loop.run_in_executor(pool, add_text, img_list, text)
            elif len(img_list) in {2, 3, 4}:
                # 合并
                gif_io = await loop.run_in_executor(pool, merge_multi_images, img_list, middle_interval)
            elif len(img_list) > 4:
                # GIF
                is_gif = True
                gif_io = await loop.run_in_executor(pool, generate_gif, img_list, duration_time)
            else:
                gif_io = None
                print("check test")
    
    # 展示图片
    if gif_io and not is_gif:
        with Image.open(gif_io) as new_image:
            new_image.show()
    elif gif_io and is_gif:
        # 文件是 GIF，则保存
        zip_obj = io.BytesIO()
        with zipfile.ZipFile(zip_obj, mode='w') as zf:
            # 将 BytesIO 对象添加到 ZIP 文件中
            zf.writestr("555.gif", gif_io.getvalue())
        # 保存到文件
        with open('my_gif.gif', 'wb') as f:
            f.write(gif_io.read())
        # 保存压缩包
        with open("compressed.zip", "wb") as zip_file:
            # 将 my_bytes 写入文件
            zip_file.write(zip_obj.getvalue())
    
    # 关闭图像文件
    for img in img_list:
        img.close()

    gif_io = None


async def main():
    # 指定图片文件夹路径
    folder_path = 'images'   # 生成 GIF 的图片例子
    # folder_path = os.path.join('images', 'text_images')   # 补充字的的图片例子
    # folder_path = os.path.join('images', 'merge_images')   # 合并的图片例子

    # 获取所有图片文件名，包括jpg, png格式的图片
    image_files = glob.glob(os.path.join(folder_path, "*.[jJ][pP][gG]")) \
                + glob.glob(os.path.join(folder_path, "*.[pP][nN][gG]"))
    # 打印出所有图片文件名
    # for image_file in image_files:
    #     print(image_file)

    # 网络图片
    # image_files = [
    # "https://ib.ahfei.blog:443/imagesbed/202403271252926-24-03-31.png",
    # "https://ib.ahfei.blog:443/imagesbed/202403271237688-24-03-45.png",
    # "https://ib.ahfei.blog:443/imagesbed/202403271235910-24-03-41.png",
    # "https://ib.ahfei.blog:443/imagesbed/202403271234538-24-03-11.png",
    # "https://ib.ahfei.blog:443/imagesbed/202403271223863-24-03-35.png",]

    print("first")
    img_list = await open_image_from_various(image_files)
    print("first2")
    await test(img_list)


if __name__ == '__main__':
    # array = (1,2,0),(3,0,4),(0,5,6)
    asyncio.run(main())