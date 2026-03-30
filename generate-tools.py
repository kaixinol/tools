import json
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from sys import argv

# --- 配置 ---
TOOLS_DIR = Path('.')
INDEX_FILE = Path('index.html')
TOOLS_CONFIG_FILE = Path('tools.json')
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

CARD_TEMPLATE = """
        <a href="{href}" class="tool-card group"{target_attr}{rel_attr}>
            <div class="flex items-start justify-between gap-4">
                <div class="icon-box group-hover:scale-110 transition-transform">{icon}</div>
                <span class="text-[10px] font-bold uppercase tracking-widest text-slate-300 group-hover:text-blue-400 transition-colors">{badge}</span>
            </div>
            <div>
                <h3 class="text-xl font-bold text-slate-800 mb-1 group-hover:text-blue-600 transition-colors">{title}</h3>
                <p class="path-text text-xs text-slate-400 font-mono italic">{path_text}</p>
            </div>
            <div class="mt-2 flex items-center text-sm font-semibold text-blue-500">
                <span>{cta}</span>
                <svg class="w-4 h-4 ml-1 transform group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"></path>
                </svg>
            </div>
        </a>"""


def preserve_doctype(original_content, rewritten_content):
    stripped_original = original_content.lstrip()
    stripped_rewritten = rewritten_content.lstrip()
    if stripped_original.lower().startswith(
        '<!doctype html>'
    ) and not stripped_rewritten.lower().startswith('<!doctype html>'):
        return '<!doctype html>\n' + rewritten_content.lstrip('\n')
    if stripped_rewritten.lower().startswith('<html'):
        return '<!doctype html>\n' + rewritten_content.lstrip('\n')
    return rewritten_content


def build_card_html(tool):
    href = escape(tool['href'], quote=True)
    title = escape(tool['title'])
    path_text = escape(tool['path_text'])
    icon = escape(tool['icon'])
    badge = escape(tool['badge'])
    cta = escape(tool['cta'])
    target_attr = ' target="_blank"' if tool['external'] else ''
    rel_attr = ' rel="noreferrer noopener"' if tool['external'] else ''
    return CARD_TEMPLATE.format(
        href=href,
        target_attr=target_attr,
        rel_attr=rel_attr,
        icon=icon,
        badge=badge,
        title=title,
        path_text=path_text,
        cta=cta,
    )


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
        attr_str = ''.join([
            f' {k}="{v}"' if v is not None else f' {k}' for k, v in attrs
        ])
        self.output += f'<{tag}{attr_str}>'

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

    def handle_comment(self, data):
        self.output += f'<!--{data}-->'

    def handle_decl(self, decl):
        self.output += f'<!{decl}>'


# --- 解析器 3: 重构首页网格 ---
class IndexRewriter(HTMLParser):
    def __init__(self, cards_content):
        super().__init__()
        self.cards_content = cards_content
        self.output = ''
        self.in_grid = False
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        if self.in_grid:
            if tag.lower() == 'div':
                self.depth += 1
            return

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

    def handle_comment(self, data):
        if not self.in_grid:
            self.output += f'<!--{data}-->'

    def handle_decl(self, decl):
        if not self.in_grid:
            self.output += f'<!{decl}>'


def process_head_injection(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'googletagmanager' in content:
        return preserve_doctype(content, content)

    injector = SmartInjector(GOOGLE_SCRIPT)
    injector.feed(content)
    return preserve_doctype(content, injector.output)


def read_tools_config(config_path):
    if not config_path.exists():
        return {}

    with open(config_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError('tools.json 必须是 dict[str, dict]')
    return data


def normalize_local_tool(tool_id, entry, discovered_title):
    folder = (entry.get('folder') or tool_id).strip()
    title = (entry.get('title') or discovered_title or folder).strip()
    return {
        'key': f'local:{folder}',
        'title': title,
        'href': f'./{folder}/index.html',
        'path_text': f'/{folder}',
        'icon': entry.get('icon') or '🛠️',
        'badge': entry.get('type') or 'Utility',
        'cta': '立即查看',
        'external': False,
    }


def normalize_external_tool(tool_id, entry):
    url = (entry.get('url') or '').strip()
    title = (entry.get('title') or tool_id).strip()
    if not url or not title:
        raise ValueError('外部工具必须同时包含 title 和 url')

    return {
        'key': f'external:{url}',
        'title': title,
        'href': url,
        'path_text': url,
        'icon': entry.get('icon') or '🔗',
        'badge': entry.get('type') or 'External',
        'cta': '打开链接',
        'external': True,
    }


def discover_local_tools():
    discovered = {}
    folders = sorted([
        path for path in TOOLS_DIR.iterdir() if path.is_dir() and path.name != 'assets'
    ])

    print('🔍 正在扫描工具目录并注入脚本...')

    for folder in folders:
        index_path = folder / 'index.html'
        if not index_path.exists():
            continue

        updated_sub_content = process_head_injection(index_path)
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(updated_sub_content)

        title_parser = TitleParser()
        title_parser.feed(updated_sub_content)
        title = title_parser.title or folder.name
        discovered[folder.name] = {'folder': folder.name, 'title': title}
        print(f'  ✅ {folder.name}: 已注入脚本并获取标题 "{title}"')

    return discovered


def build_tools_list(discovered, config_entries):
    configured_locals = set()
    ordered_tools = []

    for tool_id, entry in config_entries.items():
        if not isinstance(entry, dict):
            raise ValueError('tools.json 中的每个值都必须是对象')

        if entry.get('url'):
            ordered_tools.append(normalize_external_tool(tool_id, entry))
            continue

        folder = (entry.get('folder') or tool_id).strip()
        if not folder:
            raise ValueError('每个工具都必须提供 folder 或 url')

        configured_locals.add(folder)
        discovered_title = discovered.get(folder, {}).get('title')
        ordered_tools.append(normalize_local_tool(tool_id, entry, discovered_title))

    for folder, meta in discovered.items():
        if folder in configured_locals:
            continue
        ordered_tools.append(normalize_local_tool(folder, {}, meta['title']))

    return ordered_tools


if not INDEX_FILE.exists():
    print(f'❌ 找不到 {INDEX_FILE}')
    raise SystemExit(1)

discovered_tools = discover_local_tools()

try:
    config_entries = read_tools_config(TOOLS_CONFIG_FILE)
    tools = build_tools_list(discovered_tools, config_entries)
except (json.JSONDecodeError, ValueError) as exc:
    print(f'❌ 读取 {TOOLS_CONFIG_FILE} 失败: {exc}')
    raise SystemExit(1)

all_cards_html = ''.join(build_card_html(tool) for tool in tools)

print('\n🏠 正在更新主页...')
main_page_with_script = process_head_injection(INDEX_FILE)

rewriter = IndexRewriter(all_cards_html)
rewriter.feed(main_page_with_script)

target_index = Path(argv[1]) if len(argv) > 1 else INDEX_FILE
with open(target_index, 'w', encoding='utf-8') as f:
    f.write(preserve_doctype(main_page_with_script, rewriter.output))

print(f'\n🚀 成功！共生成 {len(tools)} 个工具卡片，且 {target_index} 已更新。')
