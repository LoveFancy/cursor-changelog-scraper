import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re

def clean_text(text):
    """清理文本，移除多余的空白字符"""
    return re.sub(r'\s+', ' ', text).strip()

def extract_update_info(text):
    """提取更新信息中的特殊说明"""
    update_match = re.search(r'UPDATE\s*\((.*?)\):\s*(.*)', text)
    if update_match:
        return {
            'update_versions': update_match.group(1).strip(),
            'update_description': update_match.group(2).strip()
        }
    return None

def parse_date(date_str):
    """解析日期字符串"""
    # 尝试多种日期格式
    date_formats = [
        '%b %d, %Y',    # Mar 14, 2024
        '%B %d, %Y',    # March 14, 2024
        '%Y-%m-%d',     # 2024-03-14
        '%d %b %Y',     # 14 Mar 2024
        '%d %B %Y'      # 14 March 2024
    ]
    
    for date_format in date_formats:
        try:
            return datetime.strptime(date_str, date_format).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return date_str

def scrape_changelog():
    # 发送请求获取页面内容
    url = 'https://www.cursor.com/cn/changelog'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 存储所有变更记录
        changelog_entries = []
        
        # 查找所有版本块
        version_blocks = soup.find_all(['h2', 'h1'])
        
        for block in version_blocks:
            # 跳过不相关的标题
            if not any(x in block.text.lower() for x in ['v', '.', 'version']):
                continue
                
            version_info = {}
            
            # 获取版本号
            version_text = block.text.strip()
            version_match = re.search(r'([0-9]+\.[0-9]+(?:\.[0-9]+)?(?:-[a-zA-Z]+(?:\.[0-9]+)?)?)', version_text)
            
            if version_match:
                version_info['version'] = version_match.group(1)
            else:
                continue
            
            # 查找日期 - 尝试多种方式查找日期
            date_element = None
            # 查找包含日期的div
            date_container = block.find_parent('article')
            if date_container:
                # 查找包含日期的div
                date_divs = date_container.find_all('div', {'class': lambda x: x and all(c in x for c in ['inline-flex', 'items-center', 'font-mono'])})
                for div in date_divs:
                    p_tag = div.find('p', {'class': lambda x: x and 'uppercase' in x})
                    if p_tag:
                        date_text = clean_text(p_tag.text)
                        if re.search(r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}', date_text):
                            date_element = p_tag
                            break
            
            if date_element:
                date_text = clean_text(date_element.text)
                # 从文本中提取日期
                date_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),?\s+(\d{4})', date_text)
                if date_match:
                    month = date_match.group(1)
                    day = date_match.group(2)
                    year = date_match.group(3)
                    # 将月份名转换为数字
                    month_dict = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
                    month_num = month_dict[month]
                    version_info['date'] = f"{year}-{month_num:02d}-{int(day):02d}"
                else:
                    version_info['date'] = 'N/A'
            else:
                version_info['date'] = 'N/A'
            
            # 获取更新内容
            content = []
            simple_updates = []
            current = block.find_next_sibling()
            
            while current and current.name not in ['h1', 'h2']:
                if current.name in ['p', 'ul', 'li']:
                    text = clean_text(current.text)
                    if text:
                        # 检查是否包含UPDATE信息
                        update_info = extract_update_info(text)
                        if update_info:
                            version_info['update_versions'] = update_info['update_versions']
                            version_info['update_description'] = update_info['update_description']
                        # 检查是否是简单的更新说明
                        simple_update_match = re.match(r'Update:\s*(.+)', text, re.IGNORECASE)
                        if simple_update_match:
                            simple_updates.append(simple_update_match.group(1))
                        else:
                            content.append(text)
                current = current.find_next_sibling()
            
            version_info['content'] = content
            if simple_updates:
                version_info['simple_updates'] = simple_updates
            changelog_entries.append(version_info)
        
        # 将结果保存为JSON文件
        with open('cursor_changelog.json', 'w', encoding='utf-8') as f:
            json.dump(changelog_entries, f, ensure_ascii=False, indent=2)
            
        print(f"成功抓取 {len(changelog_entries)} 条更新记录")
        return changelog_entries
        
    except requests.exceptions.RequestException as e:
        print(f"抓取失败: {e}")
        return None

if __name__ == "__main__":
    changelog_data = scrape_changelog()
    if changelog_data:
        # 打印最新的几条更新记录作为示例
        print("\n最新的更新记录:")
        for entry in changelog_data[:3]:
            print(f"\n版本: {entry['version']}")
            print(f"日期: {entry['date']}")
            if 'update_versions' in entry:
                print(f"更新版本范围: {entry['update_versions']}")
                print(f"更新说明: {entry['update_description']}")
            print("更新内容:")
            for item in entry['content']:
                print(f"- {item}")