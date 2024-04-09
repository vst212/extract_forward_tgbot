import shutil
import os
from abc import ABC, abstractmethod

import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient


def backup_file(taskfile, backup_path, append_str, clear=False):
    """若 clear 为 true，备份后清空原文件"""
    # 确保备份目录存在
    os.makedirs(backup_path, exist_ok=True)

    # 获取文件名和扩展名
    filename, extension = os.path.splitext(os.path.basename(taskfile))

    # 构建备份文件名
    backup_filename = f"{filename}{append_str}{extension}"

    # 构建备份文件路径
    backup_file_path = os.path.join(backup_path, backup_filename)

    try:
        # 复制文件到备份目录
        shutil.copy2(taskfile, backup_file_path)
        print(f"成功将 {taskfile} 复制到 {backup_file_path}")
    except Exception as e:
        print(f"复制文件失败: {e}")
    
    if clear:
        with open(taskfile, 'w'):
            pass


class LocalReadWrite:
    """读取和保存到本地文件"""
    def __init__(self):
        self.path = ''

    def read(self, path):
        """读取原本的数据"""
        with open(path, 'r', encoding='utf-8') as f:
            old = f.read()
        return old

    def write(self, path, content):
        """把数据存储"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    def write_behind(self, path, content):
        """把数据存储"""
        with open(path, 'a', encoding='utf-8') as f:
            f.write(content)

    def write_in_front(self, path, content):
        """把文本添加到本地的一个文件里，添加在开头"""
        old = self.read()
        content += old
        self.write(content)
    
    def clear(self, path):
        with open(path, 'w'):
            pass


class WebnoteReadWrite:
    """读取和提交到 webnote"""
    def read(self, url):
        """提取原本的数据"""
        old = ""
        response = requests.get(url, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')
        textarea = soup.find('textarea', {'id': 'content'})
        if textarea:
            old = textarea.text
        return old

    def write(self, url, content):
        """把数据提交上去"""
        data = {"text": content}
        requests.post(url, data=data, verify=False)

    def write_behind(self, url, content):
        """把数据提交上去"""
        old = self.read(url)
        old += content
        self.write(url, old)

    def write_in_front(self, url, content):
        """把文本添加到 webnote 里，添加在开头，先读取，再提交"""
        old = self.read(url)
        content += old
        self.write(url, content)


class AbstractReadWrite(ABC):
    """读取和保存内容到某个地方"""
    def __init__(self, somewhere):
        """初始化存储路径的信息，和连接等"""
        self.somewhere = somewhere

    @abstractmethod
    def read(self, address: str) -> str:
        """接收某个用户的位置，然后返回读取的数据"""
        raise NotImplementedError

    @abstractmethod
    def _write(self, address: str, content: str):
        """接收某个用户的位置，把数据覆盖存储"""
        raise NotImplementedError

    @abstractmethod
    def insert(self, address: str, content: str, insertion_point: int):
        """把数据插入到指定位置，按字符计，负数则是倒着数"""
        raise NotImplementedError
    
    @abstractmethod
    def append(self, address: str, content: str):
        """先读取原本的数据，然后缝合，再覆盖写入"""
        raise NotImplementedError

    @abstractmethod
    def write_in_front(self, address: str, content: str):
        """把文本添加添加在开头"""
        raise NotImplementedError

    @abstractmethod
    def clear(self, address: str):
        """清空内容"""
        raise NotImplementedError

    @abstractmethod
    def del_data(self, address: str):
        """彻底删除用户数据"""
        raise NotImplementedError

class MongoDBReadWrite(AbstractReadWrite):
    """读取和保存到 MongoDB，传入地址，针对的是一个 collection 的读写，其他 collection 则再实例"""
    def __init__(self, uri: str, db_name: str, collection_name: str, field: str="forward"):
        client = MongoClient(uri)
        db = client[db_name]
        self.collection = db[collection_name]
        # 针对一行中的某个字段编辑
        self.field = field
        try:
            client.admin.command('ping')
            print("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            print(e)

    def read(self, address: str) -> str:
        """接收 user_id ，然后返回 field 中的数据"""
        user_id = address
        if row := self.collection.find_one({"user_id": user_id}):
            # 如果有该用户的数据
            content = row[self.field]
            return content
        else:
            print(f"mongo_rw return: 不存在 {user_id}")
            return ""

    def _write(self, address: str, content: str):
        """接收 user_id ，把数据覆盖存储"""
        user_id = address
        if self.collection.find_one({"user_id": user_id}):
            # 更新这条数据
            data = {self.field: content}
            self.collection.update_one({"user_id": user_id}, {'$set': data})
        else:
            # 尚未有此用户
            row = {"user_id": user_id, self.field: content}
            self.collection.insert_one(row)

    def insert(self, address: str, insert_content: str, insertion_point: int):
        """把数据插入到指定位置，按字符计，负数则是倒着数"""
        user_id = address
        original_content = self.read(user_id)
        if insertion_point == -1:
            # 追加到结尾
            new_content = original_content + insert_content
        elif insertion_point == 0:
            # 在开头插入
            new_content = insert_content + original_content
        else:
            raise IndexError("temporarily not support this insertion_point")
        
        self._write(user_id, new_content)
    
    def append(self, address: str, content: str):
        """先读取原本的数据，然后缝合，再覆盖写入"""
        self.insert(address, content, -1)

    def write_in_front(self, address: str, content: str):
        """把文本添加添加在开头"""
        self.insert(address, content, 0)

    def clear(self, address: str):
        user_id = address
        self._write(user_id, "")

    def del_data(self, address: str):
        """彻底删除用户数据"""
        self.collection.delete_one({"user_id": address})



if __name__ == "__main__":
    from configHandle import Config

    config = Config("./config.yaml")
    uri = config.mongo_uri
    db_name = config.mongo_db
    collection_name = config.mongo_collection
    user_id = config.chat_id

    mongodb_rw = MongoDBReadWrite(uri, db_name, collection_name, field="forward")

    content = mongodb_rw.read(user_id)
    print("----------")

    string = "first add content\n第一次插入内容"
    mongodb_rw.append(user_id, string)
    content = mongodb_rw.read(user_id)
    print(content)
    print("----------")

    string = "second add content\n第二次插入内容"
    mongodb_rw.append(user_id, string)
    content = mongodb_rw.read(user_id)
    print(content)
    print("----------")

    string = "third add content\n第三次插入内容"
    mongodb_rw.write_in_front(user_id, string)
    content = mongodb_rw.read(user_id)
    print(content)
    print("----------")

    mongodb_rw.clear(user_id)
    content = mongodb_rw.read(user_id)
    print(content)
    print("----------")

    mongodb_rw.del_data(user_id)
    content = mongodb_rw.read(user_id)
