import os
from html.parser import HTMLParser
from sys import argv

# --- 配置 ---
TOOLS_DIR = '.'
INDEX_FILE = 'index.html'
GRID_ID = 'tools-grid'

# 在此处替换你的 Google 脚本内容
GOOGLE_SCRIPT = """
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-QPCXH7NF4W"></script>
    <script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-QPCXH7NF4W');
    </script>
"""

# 卡片 HTML 片段模板
CARD_TEMPLATE = """
        <a href="./{folder}/index.html" class="tool-card group">
            <div class="flex items-start justify-between">
                <div class="icon-box group-hover:scale-110 transition-transform">🛠️</div>
                <span class="text-[10px] font-bold uppercase tracking-widest text-slate-300 group-hover:text-blue-400 transition-colors">Utility</span>
            </div>
            <div>
                <h3 class="text-xl font-bold text-slate-800 mb-1 group-hover:text-blue-600 transition-colors">{title}</h3>
                <p class="path-text text-xs text-slate-400 font-mono italic">/{folder}</p>
            </div>
            <div class="mt-2 flex items-center text-sm font-semibold text-blue-500">
                <span>立即查看</span>
                <svg class="w-4 h-4 ml-1 transform group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"></path>
                </svg>
            </div>
        </a>"""


# --- 解析器 1: 提取工具标题 ---
class TitleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ''
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'title':
            self.in_title = True

    def handle_data(self, data):
        if self.in_title:
            self.title = data.split('|')[0].split('-')[0].strip()

    def handle_endtag(self, tag):
        if tag.lower() == 'title':
            self.in_title = False


# --- 解析器 2: 脚本注入器 (用于 Head) ---
class SmartInjector(HTMLParser):
    def __init__(self, script_content):
        super().__init__()
        self.script_content = script_content
        self.output = ''
        self.script_injected = False

    def handle_starttag(self, tag, attrs):
        # 保持原始标签属性
        attr_str = ''.join([
            f' {k}="{v}"' if v is not None else f' {k}' for k, v in attrs
        ])
        self.output += f'<{tag}{attr_str}>'

        # 在 head 标签后立即插入
        if tag.lower() == 'head' and not self.script_injected:
            self.output += self.script_content
            self.script_injected = True

    def handle_endtag(self, tag):
        self.output += f'</{tag}>'

    def handle_startendtag(self, tag, attrs):
        attr_str = ''.join([
            f' {k}="{v}"' if v is not None else f' {k}' for k, v in attrs
        ])
        self.output += f'<{tag}{attr_str} />'

    def handle_data(self, data):
        self.output += data


# --- 解析器 3: 重构首页网格 ---
class IndexRewriter(HTMLParser):
    def __init__(self, cards_content):
        super().__init__()
        self.cards_content = cards_content
        self.output = ''
        self.in_grid = False
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        attr_str = ''.join([
            f' {k}="{v}"' if v is not None else f' {k}' for k, v in attrs
        ])
        self.output += f'<{tag}{attr_str}>'

        if attr_dict.get('id') == GRID_ID:
            self.in_grid = True
            self.depth = 0
            self.output += self.cards_content

    def handle_endtag(self, tag):
        if self.in_grid:
            if tag.lower() == 'div' and self.depth == 0:
                self.in_grid = False
            else:
                if tag.lower() == 'div':
                    self.depth -= 1
                return

        if not self.in_grid:
            self.output += f'</{tag}>'

    def handle_startendtag(self, tag, attrs):
        if not self.in_grid:
            attr_str = ''.join([
                f' {k}="{v}"' if v is not None else f' {k}' for k, v in attrs
            ])
            self.output += f'<{tag}{attr_str} />'

    def handle_data(self, data):
        if not self.in_grid:
            self.output += data


# --- 辅助函数：注入脚本到文件 ---
def process_head_injection(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 简单的去重检查：如果包含 googletagmanager 就不再重复注入
    if 'googletagmanager' in content:
        return content

    injector = SmartInjector(GOOGLE_SCRIPT)
    injector.feed(content)
    return injector.output


# --- 执行流程 ---

if not os.path.exists(INDEX_FILE):
    print(f'❌ 找不到 {INDEX_FILE}')
    raise SystemExit(1)

# 1. 扫描文件夹、处理子页面 Head 并生成卡片列表
all_cards_html = ''
folders = sorted([
    f
    for f in os.listdir(TOOLS_DIR)
    if os.path.isdir(os.path.join(TOOLS_DIR, f)) and f != 'assets'
])

print('🔍 正在扫描工具目录并注入脚本...')

for folder in folders:
    index_path = os.path.join(TOOLS_DIR, folder, 'index.html')
    if os.path.exists(index_path):
        # A. 给子页面注入 Google 脚本
        updated_sub_content = process_head_injection(index_path)
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(updated_sub_content)

        # B. 提取标题用于首页卡片
        t_parser = TitleParser()
        t_parser.feed(updated_sub_content)
        title = t_parser.title or folder
        all_cards_html += CARD_TEMPLATE.format(folder=folder, title=title)
        print(f'  ✅ {folder}: 已注入脚本并获取标题 "{title}"')

# 2. 处理首页：注入脚本 + 更新网格
print('\n🏠 正在更新主页...')
# 先注入脚本到首页内容中
main_page_with_script = process_head_injection(INDEX_FILE)

# 再进行网格内容的替换
rewriter = IndexRewriter(all_cards_html)
rewriter.feed(main_page_with_script)

# 3. 写回首页文件
target_index = argv[1] if len(argv) > 1 else INDEX_FILE
with open(target_index, 'w', encoding='utf-8') as f:
    f.write(rewriter.output)

print(f'\n🚀 成功！所有页面已注入 Google 脚本，且 {target_index} 已更新。')
