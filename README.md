# 菲比丘比行为表情包插件

AstrBot >=4.16 / OneBot v11 / NapCat。基于用户消息的**行为关键词**从 [Phoebe-Hub](https://github.com/Kato-Shoko705/Phoebe-Hub) 公共索引选择符合标题、标签或配置 ID 的图片。和 DeepSeek 的文本人格可以同时运行；本插件自身无需 API Key。

## 安装

1. GitHub 上创建公开仓库 `astrbot_plugin_phoebe_actions`，上传本目录全部文件到仓库根目录。
2. AstrBot WebUI → 插件 → 从 GitHub 仓库链接安装，输入 `https://github.com/你的用户名/astrbot_plugin_phoebe_actions`。
3. 安装 `requirements.txt` 依赖（若后台未自动安装），启用插件，确保 QQ/OneBot 已连通。
4. 测试群发送 `菲比哈气`、`菲比乱拳`、`给你蛋糕` 等。默认有 45% 概率和 45 秒冷却，测试可将触发概率改为 1、冷却改为 0。
5. 如果日志出现“未找到可确认的图片”，给 `behavior_ids` 配置来自 `memes.json` 的图片 ID。比如 `{ "haqi": ["5"], "punch": [], "cake": [], "angry": [], "hello": [] }`。**ID 5 仅为语法示例，并非确认是哈气图片**。请先在 [图库索引](https://kato-shoko705.github.io/Phoebe-Hub/data/memes.json) 按 `title` 和 `id` 检查。

## 规则

- `haqi`: 哈气/哈气模式；图片标题、标签或文件名匹配“哈气”等
- `punch`: 乱拳/打拳；图片匹配“乱拳”等
- `cake`: 蛋糕/甜点；图片匹配“蛋糕”等
- `angry`: 震怒/胖/炸毛；图片匹配“生气”等
- `hello`: 菲比/丘比；图片匹配“菲比”等

优先级：管理员定义的 `behavior_ids` → 标题/标签/文件名关键词。严格匹配失败时**不发送不相关图片**。缓存索引和图片位于 `data/plugin_data/astrbot_plugin_phoebe_actions`，插件更新不会覆盖数据。仅处理群聊，不会直接调用 DeepSeek。若群里同时开启 AI 自动回复，可能一条消息同时触发两种回复，请在 AstrBot 中调整规则。

## 图片和许可

本仓库**不包含、批量下载或再分发** Phoebe-Hub 素材，仅在触发时按需请求并作本地缓存。图片的著作权归各自作者。使用前请核实来源和使用许可，不要把上游 MIT 代码许可误认为图片的再分发许可。要公开发布带图片资源的衍生库需单独取得相应许可。

代码为独立实现，技术思路参考 [wjn1121/astrbot_plugin_phoebe](https://github.com/wjn1121/astrbot_plugin_phoebe)（MIT），官方接口参考 [AstrBot 插件开发文档](https://docs.astrbot.app/dev/star/plugin-new.html)。
