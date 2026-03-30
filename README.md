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

如果想把生成结果直接输出到某个目录，可以使用：

```bash
python3 generate-tools.py -o dist
```

CSS 现在通过 Tailwind CLI 构建，不再使用运行时 CDN：

```bash
npm install
npm run build:css
```

`assets/site.css` 是构建产物，不需要提交到仓库。GitHub Pages 会在 CI 里自动生成；本地如果要预览最新样式，先运行一次 `npm run build:css`。

CI 只会上传 `dist/` 里的发布文件，不再把整个仓库作为 Pages artifact。

## tools.json

`tools.json` 默认放在项目根目录，也就是当前仓库的 `/mnt/data/Project/tools/tools.json`。

`tools.json` 使用 `dict[str, dict]` 结构，顶层 key 作为工具 ID；本地工具默认把这个 key 当作 `folder`，外部工具默认把这个 key 当作 `title`。

- 本地工具：`{"image-stream-generator": {"icon": "🖼️", "type": "Generator"}}`
- 外部工具：`{"openai": {"title": "OpenAI", "url": "https://openai.com", "icon": "🔗", "type": "AI"}}`
- 可选字段：`title`、`folder`、`icon`、`type`。其中 `type` 用于控制卡片右上角的英文标签
