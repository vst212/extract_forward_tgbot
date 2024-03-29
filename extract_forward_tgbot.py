"""
路由和注册，以及运行
"""

import sys
import json

from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

import preprocess
# 从 tgbotBehavior.py 导入定义机器人动作的函数
from tgbotBehavior import start, transfer, clear, push, unknown, earliest_msg, sure_clear, delete_last_msg, image_get, shutdown, reload_config
from multi import set_config


if __name__ == '__main__':
    application = ApplicationBuilder().token(preprocess.config.bot_token).build()

    # 注册 start_handler ，以便调度
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler((~filters.COMMAND), transfer))   # 转存
    application.add_handler(CommandHandler('image', image_get))    # 处理图片
    application.add_handler(CommandHandler('clear', sure_clear))   # 确认删除转存内容
    # 删除转存内容 或回复不删
    application.add_handler(CallbackQueryHandler(clear))

    application.add_handler(CommandHandler('push', push))   # 推送到
    application.add_handler(CommandHandler('emsg', earliest_msg))   # 显示最早的一条信息
    application.add_handler(CommandHandler('dmsg', delete_last_msg))   # 删除最新的一条信息
    application.add_handler(CommandHandler('set', set_config))   # 设置参数，如网址路径
    application.add_handler(CommandHandler('reload', reload_config))   # 重载配置文件
    application.add_handler(CommandHandler('shutdown', shutdown))   # 停止机器人

    # 未知命令回复。必须放到最后，会先判断前面的命令，都不是才会执行这个
    unknown_handler = MessageHandler(filters.COMMAND, unknown)
    application.add_handler(unknown_handler)

    # 启动，直到按 Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

    # 在程序停止运行时将字典保存回文件
    with open(preprocess.config.json_file, 'w') as file:
        json.dump(preprocess.config.path_dict, file)

