"""
tg机器人的多人版相关命令行为
"""
from telegram import Update
from telegram.ext import CallbackContext

from preprocess import config


async def is_valid_str(string, context: CallbackContext, chat_id) -> int:
    # 长度限制3个到26个，字符限制仅字母和数字
    if not (string.isalnum() and 2 < len(string) < 27):
        await context.bot.send_message(chat_id=chat_id, text="路径只能使用字母和数字，长度在 [3,26]")
        return False
    return True
    
async def set_config(update: Update, context: CallbackContext):
    user_key = str(update.effective_chat.id)   # 是 int 型
    args = context.args   # 字符串列表

    not_valid = True
    if args:
        if len(args) == 1 and args[0] != "persistent":
            netstr = args[0]   # 取网址路径
            if await is_valid_str(netstr, context, update.effective_chat.id):
                not_valid = False
            reply = set_netstr(netstr, user_key)
        elif len(args) == 2 and args[0] == "persistent":
            persistent_webnote_url = args[1]
            if await is_valid_str(persistent_webnote_url, context, update.effective_chat.id):
                not_valid = False
            reply = set_persistent_webnote_url(persistent_webnote_url, user_key)

    # 如果 args 为不合格式，直接结束
    if not_valid:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="格式为： /set pathstring ，只能使用字母和数字，长度在 [3,26]\n 或者使用 /set persistent <path_str> 设置一个同步保存内容的记事本路径")
        return

    await context.bot.send_message(chat_id=update.effective_chat.id, text=reply)


def set_netstr(netstr, user_key) -> str:
    """设置推送到是路径"""
    # 如果路径是 random，则从字典中删除键值对，也就是恢复随机路径
    if netstr == "random":
        user_value = config.path_dict.pop(user_key, "already random")
        reply = f"the last path is {user_value}, now is set to random"
    else:
        config.path_dict[user_key] = netstr
        reply = f"网址路径设置为 {config.path_dict[user_key]}， 若要恢复随机，设置路径为 random"
    return reply


def set_persistent_webnote_url(persistent_webnote_url, user_key) -> str:
    """设置同步路径"""
    user_key += "_psw"
    # 如果路径是 delete，不再使用同步
    if persistent_webnote_url == "delete":
        user_value = config.path_dict.pop(user_key, "already deleted")
        reply = f"the persistent_webnote_url was {user_value}, now was deleted"
    else:
        config.path_dict[user_key] = persistent_webnote_url
        reply = f"同步路径设置为 {config.path_dict[user_key]}， 若不再使用同步，设置路径为 delete"
    return reply
