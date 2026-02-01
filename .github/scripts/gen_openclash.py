import os
import yaml
import re
from urllib.parse import quote
from datetime import datetime

# ================= 配置常量 =================
SOURCE_BASE = "THEYAMLS"
OUTPUT_BASE = "Overwrite/THEOPENCLASH"
INI_BASE = "Overwrite/THEINI"
REPO_RAW = f"https://raw.githubusercontent.com/{os.getenv('GITHUB_REPOSITORY')}/main"

# 这里存放OpenClash官方的完整参数模板（默认全部注释掉，只保留参考价值）
OPENCLASH_PARAMS_TEMPLATE = """
# ==========================================================
# ==== OpenClash 完整参数参考 (如需启用某项，请删除行首的 #) ====
# ==========================================================

# --- 核心与端口 ---
# CORE_TYPE = Meta
# PROXY_PORT = 7890
# HTTP_PORT = 7890
# SOCKS_PORT = 7891
# MIXED_PORT = 7893
# DNS_PORT = 7874
# CN_PORT = 9090

# --- DNS 相关 ---
# ENABLE_REDIRECT_DNS = 1
# ENABLE_CUSTOM_DNS = 1
# APPEND_DEFAULT_DNS = 1
# APPEND_WAN_DNS = 0
# STORE_FAKEIP = 1
# CUSTOM_FAKEIP_FILTER = 1
# CUSTOM_FAKEIP_FILTER_MODE = blacklist
# FAKEIP_RANGE = 198.18.0.1/16
# ENABLE_RESPECT_RULES = 1
# CUSTOM_NAME_POLICY = 1
# CUSTOM_HOST = 1
# CUSTOM_FALLBACK_FILTER = 1

# --- IPv6 相关 ---
# IPV6_ENABLE = 0
# IPV6_DNS = 0
# IPV6_MODE = 0  # 0:TProxy, 1:Redirect, 2:TUN, 3:Mix
# ENABLE_V6_UDP_PROXY = 0

# --- 代理与模式 ---
# EN_MODE = fake-ip-mix
# ENABLE_UDP_PROXY = 1
# ROUTER_SELF_PROXY = 1
# STACK_TYPE = system
# PROXY_MODE = rule

# --- 防火墙与访问控制 ---
# INTRANET_ALLOWED = 1
# BYPASS_GATEWAY_COMPATIBLE = 0
# COMMON_PORTS = 21 22 23 53 80 123 143 194 443 465 587 853 993 995 998 2052 2053 2082 2083 2086 2095 2096 5222 5228 5229 5230 8080 8443 8880 8888 8889

# --- 分流与嗅探 ---
# CHINA_IP_ROUTE = 1
# CHINA_IP6_ROUTE = 0
# CHNR_AUTO_UPDATE = 1
# ENABLE_META_SNIFFER = 1
# ENABLE_META_SNIFFER_CUSTOM = 1
# ENABLE_META_SNIFFER_PURE_IP = 1

# --- 性能与指纹 ---
# ENABLE_TCP_CONCURRENT = 1
# FIND_PROCESS_MODE = off
# GLOBAL_CLIENT_FINGERPRINT = random
# ENABLE_UNIFIED_DELAY = 1

# --- Smart 策略 ---
# AUTO_SMART_SWITCH = 0
# SMART_STRATEGY = sticky-sessions
# SMART_ENABLE_LGBM = 0

# --- 数据库更新 ---
# ENABLE_GEOIP_DAT = 1
# GEODATA_LOADER = standard
# GEOIP_AUTO_UPDATE = 1
# GEOSITE_AUTO_UPDATE = 1

# --- 其他 ---
# SMALL_FLASH_MEMORY = 0
# DISABLE_QUIC_GO_GSO = 1
# DELAY_START = 0
# SKIP_PROXY_ADDRESS = 1
# RESTART = false
"""

# 处理 YAML 中的 ! 标签
yaml.add_multi_constructor("!", lambda loader, suffix, node: None, Loader=yaml.SafeLoader)

def get_current_date():
    return datetime.now().strftime("%Y-%m-%d")

def gen_openclash():
    print("🚀 开始生成 OpenClash 覆写配置...")
    os.makedirs(OUTPUT_BASE, exist_ok=True)
    
    total_count = 0
    categories = {} # 用于存储分类和文件信息

    for root, dirs, files in os.walk(SOURCE_BASE):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            if not file.endswith(('.yaml', '.yml')): continue
            
            full_path = os.path.join(root, file)
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                providers = data.get('proxy-providers', {}) if isinstance(data, dict) else {}
                if not providers: continue
                
                # 计算路径
                rel_dir = os.path.relpath(root, SOURCE_BASE)
                out_dir = os.path.join(OUTPUT_BASE, rel_dir)
                os.makedirs(out_dir, exist_ok=True)
                
                # 准备变量
                raw_url = f"{REPO_RAW}/{quote(f'{SOURCE_BASE}/{rel_dir}/{file}'.replace(os.sep, '/'))}"
                conf_name = os.path.splitext(file)[0] + ".conf"
                out_file = os.path.join(out_dir, conf_name)
                provider_keys = list(providers.keys())
                
                # ==== 生成 .conf 内容 ====
                content_lines = []
                content_lines.append(f"# OpenClash Overwrite Config for {file}")
                content_lines.append(f"# Generated at: {get_current_date()}")
                content_lines.append(f"# Original Source: {raw_url}")
                content_lines.append("")
                
                # 1. 插入完整参考模板 (被注释的完全体)
                content_lines.append(OPENCLASH_PARAMS_TEMPLATE.strip())
                content_lines.append("")
                
                # 2. 插入 [General] 及 默认启用的配置
                content_lines.append("[General]")
                content_lines.append("# -- 必选配置 (已默认启用) --")
                content_lines.append("DISABLE_UDP_QUIC = 1")
                # 下载配置 (每天早上6点自动更新)
                content_lines.append(f"DOWNLOAD_FILE = url={raw_url}, path=/etc/openclash/config/{file}, cron=0 6 * * *, force=false")
                content_lines.append(f"CONFIG_FILE = /etc/openclash/config/{file}")
                content_lines.append("SUB_INFO_URL = $EN_KEY1")
                content_lines.append("")
                
                # 3. 插入 [Overwrite] 部分
                content_lines.append("[Overwrite]")
                content_lines.append("# 自动匹配环境变量 EN_KEY1, EN_KEY2... 到对应的 Provider")
                for idx, name in enumerate(provider_keys, 1):
                    # 使用单引号包裹 YAML 路径，防止特殊字符错误
                    content_lines.append(f'ruby_map_edit "$CONFIG_FILE" "[\'proxy-providers\']" "{name}" "[\'url\']" "$EN_KEY{idx}"')
                
                # 写入文件
                with open(out_file, 'w', encoding='utf-8') as f:
                    f.write("\n".join(content_lines))
                
                # 收集信息用于生成 README
                if rel_dir not in categories:
                    categories[rel_dir] = []
                categories[rel_dir].append({
                    'name': conf_name,
                    'source': file,
                    'providers': provider_keys,
                    'raw_url': f"{REPO_RAW}/{quote(f'{OUTPUT_BASE}/{rel_dir}/{conf_name}'.replace(os.sep, '/'))}"
                })
                
                total_count += 1
                
            except Exception as e:
                print(f"⚠️ 处理出错 {file}: {e}")

    # ==== 生成分类 README (详细版) ====
    for cat, items in categories.items():
        cat_path = os.path.join(OUTPUT_BASE, cat)
        readme_lines = [
            f"# 📁 分类: {cat}",
            "",
            "此目录下的 OpenClash 覆写配置文件，已集成完整的参数参考。",
            "",
            "| 配置文件 (.conf) | 需要填写的订阅源 (Provider) | 操作 |",
            "| :--- | :--- | :--- |"
        ]
        
        for item in sorted(items, key=lambda x: x['name']):
            # 格式化 providers 显示
            prov_str = "<br>".join([f"`$EN_KEY{i+1}`: {p}" for i, p in enumerate(item['providers'])])
            # 构建 Raw 链接
            link = item['raw_url']
            
            readme_lines.append(f"| **{item['name']}** | {prov_str} | [查看源码]({link}) |")
            
        readme_lines.extend(["", "---", f"[🔙 返回总览](../README.md)"])
        
        with open(os.path.join(cat_path, "README.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(readme_lines))

    # ==== 生成主 README (索引版) ====
    main_readme = [
        "# 📦 OpenClash 覆写配置仓库",
        "",
        "自动生成基于 Mihomo 内核的 OpenClash 覆写文件。每个文件包含完整的 OpenClash 参数参考（默认注释），仅启用了最基础的更新和订阅覆写功能。",
        "",
        "## 📂 目录总览",
        "",
        "| 分类目录 | 包含配置数 | 说明 |",
        "| :--- | :--- | :--- |"
    ]
    
    for cat in sorted(categories.keys()):
        count = len(categories[cat])
        main_readme.append(f"| 📁 **[{cat}](./{cat}/README.md)** | {count} 个 | [点击浏览详细列表](./{cat}/README.md) |")
        
    main_readme.extend([
        "",
        "## 🚀 使用方法",
        "1. 进入上方分类目录找到需要的 `.conf` 文件。",
        "2. 复制文件 URL (Raw Link)。",
        "3. 在 OpenClash -> 配置文件管理 -> 下载配置文件中粘贴 URL。",
        "4. **重要**：在 OpenClash 插件设置 -> 覆写设置 -> 开发者选项 (或根据提示) 中设置对应订阅链接的环境变量 (`EN_KEY1`, `EN_KEY2` 等)。",
        "",
        "[🏠 返回项目主页](../../README.md)"
    ])
    
    with open(os.path.join(OUTPUT_BASE, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(main_readme))
        
    print(f"✅ 生成完毕！共处理 {total_count} 个 OpenClash 配置文件。")

def gen_ini_docs():
    # 保持原有的 INI 生成逻辑，略微优化输出提示
    script_path = ".github/scripts/download-ini.sh"
    if not os.path.exists(script_path): return
    
    print("🚀 开始生成 INI 文档...")
    try:
        with open(script_path, 'r', encoding='utf-8') as f: content = f.read()
        urls = re.findall(r'https?://[^\s"\']+', content)
        cats = {"ACL4SSR": [], "Airport": [], "General": []}
        
        for url in urls:
            cat = "ACL4SSR" if 'ACL4SSR' in url else ("Airport" if any(x in url for x in ['jklolixxs', 'customized', 'airports']) else "General")
            # 简单的作者提取逻辑优化
            parts = url.split('/')
            author = parts[3] if 'github.com' in url else parts[2].split('.')[0]
            cats[cat].append({'author': author, 'file': parts[-1], 'url': url})
        
        os.makedirs(INI_BASE, exist_ok=True)
        lines = ["# 📂 INI 覆写配置集合", "", "来源于项目的下载脚本自动抓取。", "", "| 分类 | 数量 | 说明 |", "| :--- | :--- | :--- |"]
        names = {"ACL4SSR": "ACL4SSR 系列", "Airport": "机场定制", "General": "通用配置"}
        
        for k, v in cats.items():
            if v: lines.append(f"| **{names.get(k, k)}** | {len(v)} 个 | [跳转详情](#{k.lower()}) |")
        
        lines.append("")
        for k, items in cats.items():
            if items:
                lines.extend([f"<h3 id='{k.lower()}'>{names.get(k, k)}</h3>", "", "| 作者 | 文件名 | 原始链接 |", "| :--- | :--- | :--- |"])
                for item in items: lines.append(f"| {item['author']} | `{item['file']}` | [Source]({item['url']}) |")
                lines.append("")
                
        with open(os.path.join(INI_BASE, "README.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print("✅ INI 文档生成完毕")
    except Exception as e:
        print(f"⚠️ INI 文档生成失败: {e}")

if __name__ == "__main__":
    gen_openclash()
    gen_ini_docs()
