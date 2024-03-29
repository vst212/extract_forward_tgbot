"""需要安装 ffmpeg"""
import io, os
import subprocess
import re
import asyncio
import aiofiles
from concurrent.futures import ProcessPoolExecutor

from urllib.parse import urlparse
import httpx


async def download_video(url: list, temp_file: str) -> None:
    """用异步下载单个视频到指定目录"""
    print(f"start to download file {url}")
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        print(f"video {url} has been downloaded")
        async with aiofiles.open(temp_file, 'wb') as video_f:
            await video_f.write(response.content)
            print(f"video {url} has been saved")

async def save_video_from_various(video_path: list | str, temp_store: str) -> list:
    """
    根据传入视频的路径的不同，如本地路径，网络路径，使用不同方式保存视频，并返回本地路径
    :param video_path:   可以是单个路径，也能是路径列表，列表的话，必须是同种地址
    :param temp_store:
    :return:   传入列表，返回列表，传入单个路径，返回路径
    """
    # 本文件不考虑删除的事情，如果后面调用中，出问题，不删除，再调用，就不必下载了。返回一个句柄，点一下就删除

    video_path_list = [video_path] if isinstance(video_path, str) else video_path

    path = video_path_list[0]
    if os.path.exists(path):
        temp_files = video_path_list
    elif urlparse(path).scheme in ('http', 'https'):
        # base_name = urlparse(url).path.split("/")[-1]
        temp_files = [os.path.join(temp_store, urlparse(url).path.split("/")[-1]) for url in video_path_list]
        missing_temp_files = [temp_file for temp_file in temp_files if not os.path.exists(temp_file)]
        funcs = (download_video(url, temp_file) for url, temp_file in zip(video_path_list, missing_temp_files))
        await asyncio.gather(*funcs)
    else:
        print("Unknown video list")
        temp_files = ["Unknown"]

    return temp_files[0] if isinstance(video_path, str) else temp_files



def get_video_resolution(video_path):
    output = '/dev/null'
    command = ['ffmpeg', '-i', video_path, '-f', 'null', 'output.mp4']
    output = subprocess.check_output(command, stderr=subprocess.STDOUT).decode()

    # 使用正则表达式从输出中提取视频分辨率信息
    pattern = r'Stream.*Video.* ([0-9]{2,})x([0-9]{2,})'
    match = re.search(pattern, output)

    if match:
        width = int(match.group(1))
        height = int(match.group(2))
        return width, height
    else:
        return None


def convert_video_to_gif(video_path, gif_path, gif_fps=15, gif_scale=320):
    # 使用 subprocess 调用 FFmpeg 命令行工具将视频转为 GIF
    subprocess.call(["ffmpeg", "-i", video_path, "-vf", f"fps={gif_fps},scale={gif_scale}:-1:flags=lanczos", gif_path, '-y'])


async def video2gif(video_local_path: list, temp_store: str, res: tuple=(), max_width=400):
    """
    只处理一个视频，返回字节流 gif_io = io.BytesIO() 和本地的 gif 文件路径
    """
    # 提取文件名，包含后缀
    filename = os.path.basename(video_local_path)
    # 分离文件名和扩展名，并取第一部分即为不含后缀的文件名
    filename_without_ext = os.path.splitext(filename)[0]
    temp_gif_path = os.path.join(temp_store, f"{filename_without_ext}.gif")

    resolution = res if res else get_video_resolution(video_local_path)
    if resolution:
        width, height = resolution
        print(f"视频的长：{height}，宽：{width}, start to transform")
        width = min(max_width, width)
        # 调用函数进行转换，需要提供输入视频的路径和输出 GIF 的路径
        loop = asyncio.get_event_loop()
        with ProcessPoolExecutor() as pool:
            await loop.run_in_executor(pool, convert_video_to_gif, video_local_path, temp_gif_path, 10, width)
            print(f"finish to transform")
        async with aiofiles.open(temp_gif_path, 'rb') as video_f:
            bytes_data = await video_f.read()
            print(f"video2BytesIO")
            gif_io = io.BytesIO(bytes_data)
        return gif_io, temp_gif_path
    else:
        print("无法获取视频分辨率")
        return False, False


# 测试用
async def main(video_paths: list[str], temp_store: str):
    video_local_path = await save_video_from_various(video_paths, temp_store)
    gif_io_and_gif_path = await asyncio.gather(*(video2gif(vp, temp_store) for vp in video_local_path))
    for _, gif_path in gif_io_and_gif_path:
        print(gif_path)


if __name__ == "__main__":
    temp_store = "forward_message"
    video_paths = ["https://ib.ahfei.blog/videobed/lightningrod-vid_wg_720p.mp4",
                   "https://ib.ahfei.blog/videobed/IOSAppStoreChangeID.mp4"]
    asyncio.run(main(video_paths, temp_store))
    