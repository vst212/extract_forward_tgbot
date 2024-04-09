"""用于将使用本地文件保存的数据，迁移到 MongoDB 上"""
import os

from pymongo import MongoClient

from configHandle import Config


config = Config("./config.yaml")

store_dir = "./forward_message"

uri = config.mongo_uri
db_name = config.mongo_db
collection_name = config.mongo_collection

client = MongoClient(uri)
db = client[db_name]
collection = db[collection_name]

# collection.delete_one({"user_id": "2082052804"})

# 获取目录下所有文件名（不包括子目录中的文件）
file_names = [f for f in os.listdir(store_dir) if os.path.isfile(os.path.join(store_dir, f))]
names_without_ext = (os.path.splitext(name)[0] for name in file_names if name.endswith(".txt"))

data = []
for file_name, name_without_ext in zip(file_names, names_without_ext):
    if not name_without_ext.endswith("_url"):
        with open(os.path.join(store_dir, file_name), 'r', encoding='utf-8') as f:
            stored = f.read()
        try:
            with open(os.path.join(store_dir, name_without_ext + "_url.txt"), 'r', encoding='utf-8') as f:
                stored_url = f.read()
        except FileNotFoundError:
            stored_url = ""
        
        single_data = {"user_id": name_without_ext, "forward": stored, "forward_url": stored_url}
        data.append(single_data)

# print(data)
result = collection.insert_many(data)
# print(result.inserted_ids)
