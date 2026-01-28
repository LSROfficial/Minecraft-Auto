""" 消息监听 """

# simmc/listeners/message_listener.py
import asyncio
import aiofiles
import re
from typing import AsyncGenerator
from pathlib import Path
from ..schemas.event_registry import get_event
from ..schemas.event import EventRequest
from ..utils.logger import logger
from ..utils.conf_injector import Inject
from ..constants import PATTERNS

@Inject(at={"mode", "enc", "host", "port", "log_path"})
class MinecraftLogListener:
    """
    统一日志监听器：支持从文件（latest.log）或 TCP Socket（Java Agent）读取日志。
    
    - mode="file": 轮询 latest.log 文件（兼容无 Agent 场景）
    - mode="socket": 连接 Java Agent 的日志推送服务（低延迟，推荐）
    """
    # 下面配置会自动注入
    mode: str = "socket"
    enc: str = "gbk"
    host: str = "127.0.0.1"
    port: int = 25334
    log_path: Path = Path("latest.log")

    def __init__(self) -> None:
        self._offset = 0
        self._rule_cache: dict[str, list[re.Pattern]] = {}
        self._needed_cache: dict[str, list[frozenset[str]]] = {}
        self._compile()

    async def listen(self) -> AsyncGenerator[EventRequest]:
        """统一入口：根据 mode 分发到具体监听逻辑"""
        if self.mode == "file":
            async for ev in self._listen_file():
                yield ev
        elif self.mode == "socket":
            async for ev in self._listen_socket():
                yield ev

    async def _listen_file(self) -> AsyncGenerator[EventRequest]:
        """原 MinecraftLogListener.listen() 逻辑"""
        if not self.log_path.exists():
            raise FileNotFoundError(f"此路径: {self.log_path} 没找到MC的 latest.log, 请重新指定。")

        self._offset = self.log_path.stat().st_size

        while True:
            curr_size = self.log_path.stat().st_size
            if curr_size > self._offset:
                async with aiofiles.open(self.log_path, 'rb') as f:
                    await f.seek(self._offset)
                    async for raw in f:
                        line = raw.decode(encoding=self.enc, errors='replace').rstrip()
                        for ev in self._parse(line):
                            yield ev
                    self._offset = await f.tell()
            elif curr_size < self._offset:
                self._offset = 0
            await asyncio.sleep(0.2)

    async def _listen_socket(self) -> AsyncGenerator[EventRequest]:
        """Socket 模式监听，失败后自动降级到文件模式"""
        logger.info(f"📡 尝试连接 Java Agent 日志 Socket: {self.host}:{self.port}")
        
        max_retries = 10
        retry_count = 0

        while retry_count < max_retries:
            try:
                reader, writer = await asyncio.open_connection(self.host, self.port)
                logger.success("✅ 成功连接到 Java Agent 日志流")
                try:
                    while True:
                        raw_line = await reader.readline()
                        if not raw_line:
                            break
                        line = raw_line.decode(self.enc, errors='replace').rstrip()
                        if not line:
                            continue
                        for ev in self._parse(line):
                            yield ev
                finally:
                    writer.close()
                    await writer.wait_closed()
                # 正常退出循环（不应发生），不降级
                return
            except (OSError, ConnectionRefusedError) as e:
                retry_count += 1
                logger.warning(f"⚠️ 连接日志 Socket 失败 ({e})，第 {retry_count}/{max_retries} 次重试...")
                if retry_count < max_retries:
                    await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"❌ Socket 监听异常: {e}")
                await asyncio.sleep(1)

        # 超过重试次数，自动降级到文件模式
        logger.warning("🛑 无法连接 Java Agent，自动降级到文件日志监听模式...")
        async for ev in self._listen_file():
            yield ev

    def _compile(self) -> None:
        """共享：预编译正则规则"""
        self._rule_cache = {}
        self._needed_cache = {}
        for event_rules in PATTERNS:
            key = event_rules["name"]
            patterns, neededs = [], []
            for rule in event_rules["rules"]:
                patterns.append(re.compile(rule["regex"], re.IGNORECASE))
                neededs.append(frozenset(rule["groups"]))
            self._rule_cache[key] = patterns
            self._needed_cache[key] = neededs
            logger.success(f"事件<{key}> 预编译完成，规则数: {len(patterns)}")

    def _parse(self, line: str) -> list[EventRequest]:
        """共享：解析单行日志"""
        events: list[EventRequest] = []
        for key, patterns in self._rule_cache.items():
            for pat in patterns:
                m = pat.search(line)
                if not m:
                    continue
                data = m.groupdict()
                needed = self._needed_cache[key][patterns.index(pat)]
                if needed and set(data) != needed:
                    logger.warning(f"事件: {key} 缺字段，跳过")
                    continue

                EventCls = get_event(key)
                if EventCls is None:
                    logger.warning(f"事件名 '{key}' 未注册，跳过")
                    continue
                events.append(EventRequest(key, EventCls(**data)))
                logger.trace(f"({key}) -> {EventCls.__name__} ({data})")
        return events