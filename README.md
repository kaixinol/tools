# tools
自制的一些网页小工具

## 首页生成

运行下面的命令会：

- 给首页和各个工具页注入 Google Analytics 脚本
- 根据根目录的 `tools.json` 生成首页卡片
- 自动补齐 `tools.json` 中未声明但目录下存在的本地工具

仓库中的 `index.html` 保持为模板；GitHub Pages 会在 CI 里运行生成脚本后再发布产物。

```bash
python3 generate-tools.py
```

## tools.json

`tools.json` 默认放在项目根目录，也就是当前仓库的 `/mnt/data/Project/tools/tools.json`。

`tools.json` 使用 `dict[str, dict]` 结构，顶层 key 作为工具 ID；本地工具默认把这个 key 当作 `folder`，外部工具默认把这个 key 当作 `title`。

- 本地工具：`{"image-stream-generator": {"icon": "🖼️", "type": "Generator"}}`
- 外部工具：`{"openai": {"title": "OpenAI", "url": "https://openai.com", "icon": "🔗", "type": "AI"}}`
- 可选字段：`title`、`folder`、`icon`、`type`。其中 `type` 用于控制卡片右上角的英文标签
