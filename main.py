from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult 
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import Node, Plain
from astrbot.api import logger

import os
import re
import time
import asyncio
import pathlib
from typing import List, Dict, Any, Optional

# 导入内部模块
from .src.calculator import HexagramCalculator
from .src.interpreter import HexagramInterpreter 
from .src.glyphs import HexagramRenderer
from .src.history import HistoryManager
from .src.limit import UsageLimit
from . import config

@register("oracle_lang", "errore, original by ydzat", "一个基于易经原理的智能算卦插件。支持多种起卦方式，提供专业的卦象解读。", "1.0.0")
class OracleLangPlugin(Star):
    # 命令前缀
    CMD_PREFIX = "算卦"

    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("OracleLang 插件初始化中...")
        
        # 获取插件所在目录
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 确保数据目录存在
        os.makedirs(os.path.join(self.plugin_dir, "data/history"), exist_ok=True)
        os.makedirs(os.path.join(self.plugin_dir, "data/static"), exist_ok=True)
        os.makedirs(os.path.join(self.plugin_dir, "data/limits"), exist_ok=True)
        
        # 初始化各模块
        self.config = config.load_config(self.plugin_dir)
        self.calculator = HexagramCalculator()
        self.interpreter = HexagramInterpreter(self.config, self.plugin_dir)
        self.renderer = HexagramRenderer()
        self.history = HistoryManager(os.path.join(self.plugin_dir, "data/history"))
        self.limit = UsageLimit(self.config, os.path.join(self.plugin_dir, "data/limits"))
        
        logger.info("OracleLang 插件初始化完成")
        
        # 加载数据
        asyncio.create_task(self._initialize())
    
    async def _initialize(self):
        # 加载静态数据
        logger.info("正在加载卦象数据...")
        await self.interpreter.load_data()
        logger.info("卦象数据加载完成")

    @filter.command(CMD_PREFIX)
    async def oracle(self, event: AstrMessageEvent, text: str = ""):
        """这是一个易经算卦命令""" # 命令描述
        # 清理文本，移除@信息
        msg = event.message_str
        sender_id = event.get_sender_id()
            
        # 清理文本，移除@信息和命令前缀
        cleaned_text = re.sub(r'@\S+\s*', '', msg).strip()
        if not cleaned_text.startswith(self.CMD_PREFIX):
            return
                
        # 提取命令参数
        cmd_args = cleaned_text[len(self.CMD_PREFIX):].strip()
            
        # 处理帮助命令
        if cmd_args.strip() == "帮助":
            await self._show_help(event)
            return
            
        # 处理用户ID查询命令
        if cmd_args.strip() == "我的ID":
            yield event.plain_result(f"您的用户ID是: {sender_id}")
            return
            
        # 处理管理命令（仅管理员可用）
        if self._is_admin(sender_id) and (cmd_args.startswith("设置") or cmd_args.startswith("重置") or cmd_args.startswith("统计")):
            await self._handle_admin_commands(event, cmd_args)
            return
            
        # 检查用户当日使用次数
        if not self.limit.check_user_limit(sender_id):
            remaining_time = self.limit.get_reset_time()
            yield event.plain_result(f"您今日的算卦次数已达上限（{self.config['limit']['daily_max']}次/天），请等待重置。\n"
                                  f"下次重置时间: {remaining_time}")
            return
                
        # 解析命令参数
        method, params, question = self._parse_command(cmd_args)
            
        # 处理历史记录查询
        if method == "历史":
            await self._show_history(event, sender_id)
            return
                
        # 生成卦象
        try:
            logger.info(f"用户 {sender_id} 使用方法 {method} 算卦，参数：{params}，问题：{question}")
            hexagram_data = await self.calculator.calculate(
                method=method,
                input_text=params or question,
                user_id=sender_id
            )
                
            # 生成卦象图示
            style = self.config["display"]["style"]
            visual = self.renderer.render_hexagram(
                hexagram_data["original"],
                hexagram_data["changed"],
                hexagram_data["moving"],
                style=style
            )
                
            # 获取卦象解释
            interpretation = await self.interpreter.interpret(
                hexagram_original=hexagram_data["hexagram_original"],
                hexagram_changed=hexagram_data["hexagram_changed"],
                moving=hexagram_data["moving"],
                question=question,
                use_llm=self.config["llm"]["enabled"]
            )
                
            # 构建响应消息
            result = self._format_response(question, hexagram_data, interpretation, visual)
                
            # 记录到历史
            self.history.save_record(
                user_id=sender_id,
                question=question,
                hexagram_data=hexagram_data,
                interpretation=interpretation
            )
                
            # 更新用户使用次数
            self.limit.update_usage(sender_id)
            remaining = self.limit.get_remaining(sender_id)
                
            # 添加使用次数提示到基本信息中
            result["basic_info"] += f"\n\n今日剩余算卦次数: {remaining}/{self.config['limit']['daily_max']}"
                
            # 检查是否为群消息
            if event.get_group_id() is not None:
                # 使用合并转发消息
                chain = Nodes([])
                chain.nodes.append(Node(
                        uin=event.get_self_id(),
                        name=self.context.get_config().get("nickname", "算命大师"),
                        content=[Plain(header + text)]
                    ))
                chain.nodes.append(Node(
                        uin=self.context.get_self_id(),
                        name=self.context.get_config().get("nickname", "算命大师"),
                        content=[Plain(result["explanation"])]
                    ))

                yield event.chain_result(nodes)
            else:
                # 私聊消息直接发送完整内容
                full_message = f"{result['basic_info']}\n\n{result['explanation']}"
                yield event.plain_result(full_message)
                        uin=self.context.get_self_id(),
                        name=self.context.get_config().get("nickname", "算命大师"),
                        content=[Plain(result["explanation"])]
                    )
                
                yield event.chain_result(nodes)
            else:
                # 私聊消息直接发送完整内容
                full_message = f"{result['basic_info']}\n\n{result['explanation']}"
                yield event.plain_result(full_message)
            event.stop_event()
        except Exception as e:
            logger.error(f"算卦过程出错: {str(e)}")
            yield event.plain_result(f"算卦过程出现错误: {str(e)}\n请稍后再试或联系管理员。")

    @filter.command(CMD_PREFIX)
    async def oracle(self, event: AstrMessageEvent, *args):
        """这是一个易经算卦命令"""
        sender_id = event.get_sender_id()
        # 拼接所有参数为命令内容
        cmd_args = " ".join(args).strip() if args else event.message_str.strip()
        # 清理@信息
        cmd_args = re.sub(r'@\S+\s*', '', cmd_args).strip()

        # 处理帮助命令
        if cmd_args.strip() == "帮助":
            await self._show_help(event)
            return

        # 处理用户ID查询命令
        if cmd_args.strip() == "我的ID":
            yield event.plain_result(f"您的用户ID是: {sender_id}")
            return

        # 处理管理命令（仅管理员可用）
        if self._is_admin(sender_id) and (cmd_args.startswith("设置") or cmd_args.startswith("重置") or cmd_args.startswith("统计")):
            await self._handle_admin_commands(event, cmd_args)
            return

        # 检查用户当日使用次数
        if not self.limit.check_user_limit(sender_id):
            remaining_time = self.limit.get_reset_time()
            yield event.plain_result(f"您今日的算卦次数已达上限（{self.config['limit']['daily_max']}次/天），请等待重置。\n"
                                  f"下次重置时间: {remaining_time}")
            return

        # 解析命令参数
        method, params, question = self._parse_command(cmd_args)

        # 处理历史记录查询
        if method == "历史":
            await self._show_history(event, sender_id)
            return

        # 生成卦象
        try:
            logger.info(f"用户 {sender_id} 使用方法 {method} 算卦，参数：{params}，问题：{question}")
            hexagram_data = await self.calculator.calculate(
                method=method,
                input_text=params or question,
                user_id=sender_id
            )

            # 生成卦象图示
            style = self.config["display"]["style"]
            visual = self.renderer.render_hexagram(
                hexagram_data["original"],
                hexagram_data["changed"],
                hexagram_data["moving"],
                style=style
            )

            # 获取卦象解释
            interpretation = await self.interpreter.interpret(
                hexagram_original=hexagram_data["hexagram_original"],
                hexagram_changed=hexagram_data["hexagram_changed"],
                moving=hexagram_data["moving"],
                question=question,
                use_llm=self.config["llm"]["enabled"]
            )

            # 构建响应消息
            result = self._format_response(question, hexagram_data, interpretation, visual)

            # 记录到历史
            self.history.save_record(
                user_id=sender_id,
                question=question,
                hexagram_data=hexagram_data,
                interpretation=interpretation
            )

            # 更新用户使用次数
            self.limit.update_usage(sender_id)
            remaining = self.limit.get_remaining(sender_id)

            # 添加使用次数提示到基本信息中
            result["basic_info"] += f"\n\n今日剩余算卦次数: {remaining}/{self.config['limit']['daily_max']}"

            # 检查是否为群消息
            if event.get_group_id():
                # 使用合并转发消息
                from astrbot.api.message_components import Node, Plain
                nodes = [
                    Node(
                        uin=self.context.self_id,  # 机器人的ID
                        name="抽取卦象",
                        content=[Plain(result["basic_info"])]
                    ),
                    Node(
                        uin=self.context.self_id,  # 机器人的ID
                        name="解释与建议",
                        content=[Plain(result["explanation"])]
                    )
                ]
                yield event.chain_result(nodes)
            else:
                # 私聊消息直接发送完整内容
                full_message = f"{result['basic_info']}\n\n{result['explanation']}"
                yield event.plain_result(full_message)
        return user_id in admin_list

    async def _show_help(self, event: AstrMessageEvent):
        """显示帮助信息"""
        help_text = [
            "📚 OracleLang 算卦插件使用指南 📚",
            "\n基本用法：",
            "算卦 [问题]  - 使用文本起卦方式进行算卦",
            "例如：算卦 我今天的工作运势如何？",
            "      算卦 近期是否适合投资股票？",
            "      算卦  (不提供问题将随缘生成一卦)",
            "注：只有提供问题，才会有AI分析卦象",
            "\n高级用法：",
            "算卦 数字 [数字] [问题]  - 使用指定数字起卦",
            "例如：算卦 数字 1234 我的事业前景如何",
            "",
            "算卦 时间 [时间] [问题]  - 使用当前时间起卦",
            "例如：算卦 时间 明天 财运",
            "",
            "算卦 历史  - 查看您的最近算卦记录",
            "算卦 我的ID  - 查询您的用户ID",
            "\n管理员命令：",
            "算卦 设置 次数 [数字]  - 设置每日算卦次数限制",
            "算卦 重置 [用户ID]  - 重置特定用户的算卦次数",
            "算卦 统计  - 查看使用统计信息",
            "\n默认每人每日可算卦 {} 次".format(self.config['limit']['daily_max'])
        ]
        
        yield event.plain_result("\n".join(help_text))

    async def terminate(self):
        """插件卸载时触发"""
        try:
            logger.info("OracleLang 插件已卸载")
        except:
            # 避免在卸载过程中出现属性错误
            pass
