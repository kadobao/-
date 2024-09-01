import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import os
from tqdm import tqdm
import traceback
from collections import OrderedDict

# 设置代理
proxies = {
    'http': 'http://127.0.0.1:7899',
    'https': 'http://127.0.0.1:7899'
}

# 获取链接列表
def get_links(url):
    response = requests.get(url, proxies=proxies)
    
    if response.status_code != 200:
        print(f"无法获取网页内容。状态码: {response.status_code}")
        return [], None
    
    soup = BeautifulSoup(response.text, 'lxml')
    links = [f"{url}{link.get('href')}" for link in soup.select('#list > dl > dd > a')]
    book_title = soup.select_one('div#info > h1').get_text()
    
    return links, book_title

# 任务函数：获取网页内容
def get_content(link, book_title, failed_links):
    try:
        response = requests.get(link, proxies=proxies)

        if response.status_code != 200:
            print(f"无法获取网页内容。状态码: {response.status_code}")
            failed_links[link] = response.status_code
            return False
        
        soup = BeautifulSoup(response.text, 'lxml')

        # 获取标题
        title_div = soup.select_one('div.bookname > h1')
        title = title_div.get_text()

        # 使用选择器获取 div 的内容
        content_div = soup.select_one('div#content[name="content"]')
        # 获取内容并去除第一行
        text_content = content_div.get_text(separator="\n")
        lines = text_content.split('\n')
        text_content_without_first_line = '\n'.join(lines[1:])

        # 去除标题中的非法字符
        safe_title = re.sub(r'[\\/:*?"<>|]', '', title)

        # 保存内容到txt文件
        with open(f"{book_title}/{safe_title}.txt", 'w', encoding='utf-8') as file:
            file.write(text_content_without_first_line)

        return True
    except Exception as e:
        print(f"处理链接 {link} 时出错: {e}")
        traceback.print_exc()
        failed_links[link] = str(e)
        return False

# 主函数：使用线程池并发执行任务
def main():
    url = 'https://www.xbiqugew.com/book/53237/'
    links, book_title = get_links(url)
    
    # 去除书名中的非法字符
    safe_book_title = re.sub(r'[\\/:*?"<>|]', '', book_title)
    
    # 创建文件夹
    if not os.path.exists(safe_book_title):
        os.makedirs(safe_book_title)
    
    success_count = 0
    failure_count = 0
    failed_links = OrderedDict()

    with ThreadPoolExecutor(max_workers=300) as executor:
        futures = [executor.submit(get_content, link, safe_book_title, failed_links) for link in links]
        
        with tqdm(total=len(futures), desc="下载中", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{percentage:.2f}%]') as pbar:
            for future in as_completed(futures):
                if future.result():
                    success_count += 1
                    pbar.update(1)  # 仅在成功下载时更新进度条
                else:
                    failure_count += 1

    print(f"总共下载文件数: {success_count}")
    print(f"总共失败文件数: {failure_count}")

    # 重试失败的链接
    retry_success_count = 0
    retry_failure_count = 0

    with ThreadPoolExecutor(max_workers=23) as executor:
        retry_futures = [executor.submit(get_content, link, safe_book_title, failed_links) for link in failed_links.keys()]
        
        with tqdm(total=len(retry_futures), desc="重试中", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{percentage:.2f}%]') as pbar:
            for future in as_completed(retry_futures):
                if future.result():
                    retry_success_count += 1
                    pbar.update(1)  # 仅在成功下载时更新进度条
                else:
                    retry_failure_count += 1

    print(f"总共重试并下载文件数: {retry_success_count}")
    print(f"总共重试并失败文件数: {retry_failure_count}")

if __name__ == "__main__":
    main()
