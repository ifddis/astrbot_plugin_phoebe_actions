"""菲比丘比行为表情插件。素材引用 Phoebe-Hub，不随代码再分发。"""
import asyncio
import json
import random
import re
import time
from pathlib import Path
from urllib.parse import quote, urlparse

import aiohttp
import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, StarTools
from astrbot.core import AstrBotConfig

INDEX = 'https://kato-shoko705.github.io/Phoebe-Hub/data/memes.json'
BACKUP_INDEX = 'https://raw.githubusercontent.com/Kato-Shoko705/Phoebe-Hub/main/data/memes.json'
IMAGE_BASE = 'https://kato-shoko705.github.io/Phoebe-Hub/'
BACKUP_BASE = 'https://raw.githubusercontent.com/Kato-Shoko705/Phoebe-Hub/main/'
EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
BEHAVIORS = {
    'haqi': (('哈气', '哈——', '哈气！'), ('哈气', '炸毛', '威吓', '嘶')), 
    'punch': (('菲比乱拳！啪叽啪叽！', '丘比乱拳，启动！'), ('乱拳', '打拳', '拳击', '乱打')),
    'cake': (('给丘比的蛋糕？！速速呈上！', '丘比已经闻到了蛋糕香！'), ('蛋糕', '甜点', '吃', '美食')),
    'angry': (('丘比震怒！！', '圆滚滚的是气势，不是胖！'), ('生气', '愤怒', '震怒', '炸毛')),
    'hello': (('菲比丘比！啾比啾比！', '丘比闪亮登场！'), ('菲比', '丘比', '可爱')),
}
TRIGGERS = [
    ('haqi', re.compile(r'哈气|哈——|哈气模式')),
    ('punch', re.compile(r'乱拳|打拳|揍一拳')),
    ('cake', re.compile(r'蛋糕|小蛋糕|甜点')),
    ('angry', re.compile(r'胖|生气|震怒|炸毛')),
    ('hello', re.compile(r'菲比|丘比|啾比')),
]


class PhoebeActions(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.data_dir = Path(StarTools.get_data_dir('astrbot_plugin_phoebe_actions'))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir = self.data_dir / 'images'
        self.cache_dir.mkdir(exist_ok=True)
        self._session = None
        self._memes = []
        self._fetched = 0.0
        self._lock = asyncio.Lock()
        self._cooldowns = {}

    async def _http(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))
        return self._session

    async def _read(self, url: str, max_bytes: int):
        # Only fetch the two pinned trusted repositories / hosts; no arbitrary URL loading.
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname not in {
            'kato-shoko705.github.io', 'raw.githubusercontent.com'
        }:
            return None
        try:
            session = await self._http()
            async with session.get(url, allow_redirects=False) as r:
                if r.status != 200:
                    return None
                if int(r.headers.get('Content-Length', '0')) > max_bytes:
                    return None
                data = bytearray()
                async for part in r.content.iter_chunked(65536):
                    data.extend(part)
                    if len(data) > max_bytes:
                        return None
                return bytes(data)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
            logger.warning(f'菲比资源获取失败: {e}')
            return None

    async def _index(self):
        if self._memes and time.monotonic() - self._fetched < 21600:
            return self._memes
        async with self._lock:
            if self._memes and time.monotonic() - self._fetched < 21600:
                return self._memes
            saved = self.data_dir / 'memes.json'
            raw = await self._read(INDEX, 5 * 1024 * 1024)
            if raw is None:
                raw = await self._read(BACKUP_INDEX, 5 * 1024 * 1024)
            if raw:
                try:
                    decoded = json.loads(raw)
                    entries = decoded.get('memes', []) if isinstance(decoded, dict) else decoded
                    if isinstance(entries, list):
                        self._memes = [m for m in entries if isinstance(m, dict) and m.get('url')]
                        saved.write_bytes(raw)
                except (ValueError, OSError) as e:
                    logger.warning(f'菲比索引解析失败: {e}')
            if not self._memes and saved.exists():
                try:
                    decoded = json.loads(saved.read_text('utf-8'))
                    entries = decoded.get('memes', []) if isinstance(decoded, dict) else decoded
                    self._memes = [m for m in entries if isinstance(m, dict) and m.get('url')]
                except (ValueError, OSError, TypeError):
                    pass
            self._fetched = time.monotonic()
            return self._memes

    def _choose(self, entries, action: str):
        # priority 1: explicit IDs from the plugin config; priority 2: title/tags keyword
        mapping = self.config.get('behavior_ids', {}) or {}
        explicit = {str(i).strip() for i in mapping.get(action, [])} if isinstance(mapping, dict) else set()
        if explicit:
            found = [m for m in entries if str(m.get('id')) in explicit]
            if found:
                return random.choice(found)
        words = BEHAVIORS[action][1]
        found = []
        for m in entries:
            title = str(m.get('title', ''))
            tags = ' '.join(str(t) for t in (m.get('tags') or []))
            name = str(m.get('url', '')).rsplit('/', 1)[-1]
            text = (title + ' ' + tags + ' ' + name).lower()
            if any(w.lower() in text for w in words):
                found.append(m)
        # Strict mode: no unrelated random image when behavior can't be verified.
        return random.choice(found) if found else None

    async def _image_path(self, meme):
        path = str(meme.get('url', '')).lstrip('/')
        parsed = urlparse(path)
        if parsed.scheme or '..' in Path(path).parts or not path.startswith('images/'):
            return None
        ext = Path(path).suffix.lower()
        if ext not in EXTS:
            return None
        import hashlib
        key = hashlib.sha256(path.encode('utf-8')).hexdigest()[:24]
        target = self.cache_dir / f'{key}{ext}'
        if target.exists() and target.stat().st_size:
            return target
        escaped = quote(path, safe='/')
        for base in (IMAGE_BASE, BACKUP_BASE):
            binary = await self._read(base + escaped, 8 * 1024 * 1024)
            if binary:
                temp = target.with_suffix(target.suffix + '.part')
                await asyncio.to_thread(temp.write_bytes, binary)
                await asyncio.to_thread(temp.replace, target)
                return target
        return None

    @filter.regex(r'菲比|丘比|啾比|哈气|乱拳|打拳|蛋糕|甜点|震怒|炸毛')
    async def on_phoebe_message(self, event: AstrMessageEvent):
        try:
            if not event.get_group_id():
                return
            allowed = self.config.get('group_allowlist', []) or []
            if allowed and str(event.get_group_id()) not in {str(v).strip() for v in allowed}:
                return
            msg = event.message_str or ''
            action = next((a for a, pat in TRIGGERS if pat.search(msg)), None)
            if not action:
                return
            chance = min(1.0, max(0.0, float(self.config.get('trigger_probability', 0.45))))
            if random.random() >= chance:
                return
            group = str(event.get_group_id())
            now = time.monotonic()
            cooldown = max(0, int(self.config.get('cooldown_seconds', 45)))
            if now - self._cooldowns.get(group, -1e10) < cooldown:
                return
            entries = await self._index()
            chosen = self._choose(entries, action)
            if not chosen:
                logger.info(f'菲比行为 {action} 未找到可确认的图片，请在插件配置 behavior_ids 中指定 ID')
                return
            filepath = await self._image_path(chosen)
            if filepath is None:
                return
            caption = random.choice(BEHAVIORS[action][0])
            await event.send(event.chain_result([
                Comp.Plain(caption), Comp.Image.fromFileSystem(str(filepath.absolute()))
            ]))
            self._cooldowns[group] = time.monotonic()
        except Exception as e:
            logger.error(f'菲比行为插件错误: {e}')

    async def terminate(self):
        if self._session and not self._session.closed:
            await self._session.close()
