import os
from abc import ABC, abstractmethod

import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient




class LocalReadWrite:
    """读取和保存到本地文件"""
    def __init__(self, rootpath_of_store: str, suffix: str=""):
        self.rootpath = rootpath_of_store
        self.suffix = suffix

    def get_path(self, address, bak: str="") -> str:
        return os.path.join(self.rootpath, f"{address}{bak}{self.suffix}")
    
    def read(self, address):
        """读取原本的数据"""
        try:
            with open(self.get_path(address), 'r', encoding='utf-8') as f:
                old = f.read()
            return old
        except FileNotFoundError:
            return ""

    def _write(self, address, content, bak: str=""):
        """把数据存储"""
        with open(self.get_path(address, bak=bak), 'w', encoding='utf-8') as f:
            f.write(content)

    def append(self, address, content):
        """追加数据"""
        with open(self.get_path(address), 'a', encoding='utf-8') as f:
            f.write(content)

    def write_in_front(self, address, content):
        """把文本添加到本地的一个文件里，添加在开头"""
        old = self.read(address)
        content += old
        self._write(address, content)
    
    def clear(self, address):
        with open(self.get_path(address), 'w'):
            pass

    def backup(self, address: str):
        """备份内容"""
        content = self.read(address)
        self._write(address, content)

    def del_data(self, address: str):
        """彻底删除用户数据"""
        os.remove(self.get_path(address))


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
    def __init__(self, rootpath_of_store):
        """初始化存储路径的信息，和连接等"""
        self.rootpath = rootpath_of_store

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
    def backup(self, address: str):
        """备份内容"""
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
            content = row.get(self.field, "")
            return content
        else:
            print(f"mongo_rw return: 不存在 {user_id}")
            return ""

    def _write(self, address: str, content: str, field: str=None):
        """接收 user_id ，把数据覆盖存储"""
        user_id = address
        field = field if field else self.field
        if self.collection.find_one({"user_id": user_id}):
            # 更新这条数据
            data = {field: content}
            self.collection.update_one({"user_id": user_id}, {'$set': data})
        else:
            # 尚未有此用户
            row = {"user_id": user_id, field: content}
            self.collection.insert_one(row)
            print(f"mongo_rw return: 已新建 {user_id}")

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

    def backup(self, address: str):
        """备份内容"""
        user_id = address
        content = self.read(user_id)
        self._write(user_id, content, field=self.field+"_bak")
    
    def del_data(self, address: str):
        """彻底删除用户数据"""
        self.collection.delete_one({"user_id": address})



if __name__ == "__main__":
    from configHandle import Config

    config = Config("./config.yaml")

    # 测试 MongoDBReadWrite 功能
    uri = config.mongo_uri
    db_name = config.mongo_db
    collection_name = config.mongo_collection
    user_id = "1111111111"

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
