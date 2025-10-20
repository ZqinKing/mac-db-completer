# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 ZqinKing <ZqinKing23@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
MAC地址数据库补全器

该脚本旨在补全 macaddress.io 免费提供的MAC地址数据库中缺失的厂商信息。
它通过整合IEEE官方发布的OUI（组织唯一标识符）数据，来增强现有数据库的准确性和完整性。
"""

import requests
import csv
import xml.etree.ElementTree as ET
import os
import argparse
import json
import re

# 数据源URL
MACADDRESS_IO_DB_URL = "https://macaddress.io/database/macaddress.io-db.xml"
IEEE_OUI_URLS = [
    "http://standards-oui.ieee.org/oui/oui.csv",
    "http://standards-oui.ieee.org/cid/cid.csv",
    "http://standards-oui.ieee.org/iab/iab.csv",
    "http://standards-oui.ieee.org/oui28/mam.csv",
    "http://standards-oui.ieee.org/oui36/oui36.csv",
]

DATA_DIR = "data"
OUTPUT_FILENAME = "macaddress.io-db-enhanced.xml"
SPECIAL_CASES_FILE = "special_cases.json"

# These are applied after punctuation has been removed.
# More examples at https://en.wikipedia.org/wiki/Incorporation_(business)
general_terms = '|'.join([
    ' a +s\\\\b', # A/S and A.S. but not "As" as in "Connect As".
    ' ab\\\\b', # Also follows "Oy", which is covered below.
    ' ag\\\\b',
    ' b ?v\\\\b',
    ' closed joint stock company\\\\b',
    ' co\\\\b',
    ' company\\\\b',
    ' corp\\\\b',
    ' corporation\\\\b',
    ' corporate\\\\b',
    ' de c ?v\\\\b', # Follows "S.A.", which is covered separately below.
    ' gmbh\\\\b',
    ' holding\\\\b',
    ' inc\\\\b',
    ' incorporated\\\\b',
    ' jsc\\\\b',
    ' k k\\\\b', # "K.K." as in "kabushiki kaisha", but not "K+K" as in "K+K Messtechnik".
    ' limited\\\\b',
    ' llc\\\\b',
    ' ltd\\\\b',
    ' n ?v\\\\b',
    ' oao\\\\b',
    ' of\\\\b',
    ' open joint stock company\\\\b',
    ' ooo\\\\b',
    ' oü\\\\b',
    ' oy\\\\b',
    ' oyj\\\\b',
    ' plc\\\\b',
    ' pty\\\\b',
    ' pvt\\\\b',
    ' s ?a ?r ?l\\\\b',
    ' s ?a\\\\b',
    ' s ?p ?a\\\\b',
    ' sp ?k\\\\b',
    ' s ?r ?l\\\\b',
    ' systems\\\\b',
    '\\\\bthe\\\\b',
    ' zao\\\\b',
    ' z ?o ?o\\\\b',
    ' l\\\\b' # Added to handle cases like "i-PRO Co L"
    ])

# Chinese company names tend to start with the location, skip it (non-exhaustive list).
skip_start = [
    'shengzen',
    'shenzhen',
    'beijing',
    'shanghai',
    'wuhan',
    'hangzhou',
    'guangxi',
    'guangdong',
    'chengdu',
    'chongqing',
    'zhejiang'
]

def load_special_cases(filepath):
    """加载特殊厂商名称映射表"""
    if not os.path.exists(filepath):
        print(f"警告: 特殊厂商映射文件 {filepath} 不存在，将使用空映射。")
        return {}
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def simplify_company_name(manuf, special_cases):
    """简化厂商名称"""
    # 1. 检查特殊情况
    if manuf in special_cases:
        return special_cases[manuf]

    # 2. 标准化空白字符
    manuf = ' '.join(manuf.split())
    orig_manuf = manuf

    # 3. 处理大小写 (全大写转为首字母大写)
    if manuf.isupper():
        manuf = manuf.title()

    # 4. 移除括号内容
    manuf = re.sub(r"\\(.*?\\)", '', manuf) # 英文括号
    manuf = re.sub(r"（.*?）", '', manuf) # 全角括号

    # 5. 移除 " a " (例如 "Aruba, a Hewlett [...]")
    manuf = manuf.replace(" a ", " ")

    # 6. 移除标点符号 (保留连字符)
    # 注意：这里移除了 make-manuf.py 中移除的 '/' 和 '&'，因为它们通常不是连字符
    manuf = re.sub(r"[\"',.:()+]", ' ', manuf)
    manuf = re.sub(r"[«»“”]", ' ', manuf) # 双角括号和引号

    # 7. 移除通用公司后缀
    plain_manuf = re.sub(general_terms, ' ', manuf, flags=re.IGNORECASE) # 将匹配到的后缀替换为空格
    if plain_manuf: # 如果清理后不为空，则更新厂商名称
        manuf = plain_manuf

    # 8. 移除地名
    split = manuf.split()
    if len(split) > 1 and split[0].lower() in skip_start:
        manuf = ' '.join(split[1:])

    # 9. 在所有简化完成后，统一进行空格处理
    manuf = ' '.join(manuf.split())

    # 10. 移除截断逻辑 (根据用户反馈，当前项目不需要此功能)
    # trunc_len = 12
    # if len(manuf) > trunc_len:
    #     manuf = manuf[:trunc_len]

    if len(manuf) < 1:
        # 如果简化后为空，则返回原始名称或一个默认值
        return orig_manuf if orig_manuf else "UNKNOWN"

    return manuf

def download_file(url, dest_folder, noupdate=False):
    """从URL下载文件并保存到指定文件夹"""
    os.makedirs(dest_folder, exist_ok=True)
    local_filename = os.path.join(dest_folder, url.split('/')[-1])

    if noupdate and os.path.exists(local_filename):
        print(f"文件 {local_filename} 已存在，跳过下载。")
        return local_filename

    print(f"正在下载 {url} 到 {local_filename}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    with requests.get(url, stream=True, headers=headers) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print(f"下载完成: {local_filename}")
    return local_filename

def load_ieee_oui_data(data_folder, special_cases):
    """加载IEEE OUI数据并构建OUI到厂商名称的映射"""
    oui_mapping = {}
    for url in IEEE_OUI_URLS:
        filename = os.path.join(data_folder, url.split('/')[-1])
        if not os.path.exists(filename):
            print(f"警告: 文件 {filename} 不存在，跳过加载。")
            continue

        print(f"正在加载IEEE OUI数据从 {filename}...")
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            header_skipped = False
            oui_idx = -1
            org_name_idx = -1

            for row in reader:
                if not header_skipped:
                    # 尝试找到包含 "Assignment" 和 "Organization Name" 的行作为头部
                    if "Assignment" in row and "Organization Name" in row:
                        oui_idx = row.index("Assignment")
                        org_name_idx = row.index("Organization Name")
                        header_skipped = True
                        continue
                    # 如果没有找到，则假设第一行是头部，并尝试根据常见位置获取
                    elif len(row) >= 3 and row.strip().upper() == "ASSIGNMENT": # oui.csv
                        oui_idx = 1
                        org_name_idx = 2
                        header_skipped = True
                        continue
                    elif len(row) >= 2 and row.strip().upper() == "REGISTRY": # cid.csv, iab.csv, mam.csv, oui36.csv
                        if "OUI" in row and "Organization" in row:
                            oui_idx = row.index("OUI")
                            org_name_idx = row.index("Organization")
                            header_skipped = True
                            continue
                        elif "Prefix" in row and "Organization" in row: # oui36.csv
                            oui_idx = row.index("Prefix")
                            org_name_idx = row.index("Organization")
                            header_skipped = True
                            continue
                        elif "MAC Prefix" in row and "Vendor" in row: # mam.csv
                            oui_idx = row.index("MAC Prefix")
                            org_name_idx = row.index("Vendor")
                            header_skipped = True
                            continue
                    print(f"无法自动识别 {filename} 的CSV头部，尝试跳过第一行并使用默认索引。")
                    header_skipped = True
                    continue

                if oui_idx != -1 and org_name_idx != -1 and len(row) > max(oui_idx, org_name_idx):
                    oui = row[oui_idx].strip().replace('-', '').upper()
                    org_name = row[org_name_idx].strip()
                    if oui and org_name:
                        simplified_name = simplify_company_name(org_name, special_cases)
                        oui_mapping[oui] = simplified_name
    print(f"加载完成，共 {len(oui_mapping)} 条OUI映射。")
    return oui_mapping

def enhance_mac_database(xml_filepath, oui_mapping):
    """
    补全macaddress.io数据库中厂商信息为"macaddress.io"的条目。
    """
    print(f"正在解析XML文件 {xml_filepath}...")
    tree = ET.parse(xml_filepath)
    root = tree.getroot()
    
    print(f"XML根标签: {root.tag}")
    
    enhanced_count = 0
    total_records = 0

    # 假设 <vendor> 标签可能嵌套在 <record> 标签内
    for record_element in root.findall(".//record"):
        total_records += 1
        vendor_element = record_element.find("companyName") # 更改为 companyName
        oui_element = record_element.find("oui")
        company_address_element = record_element.find("companyAddress") # 添加 companyAddress

        if vendor_element is not None and vendor_element.text:
            vendor_text_lower = vendor_element.text.strip().lower()
            
            # 调试打印
            # print(f"原始厂商名: '{vendor_element.text}'")
            # print(f"处理后厂商名: '{vendor_text_lower}'")

            if vendor_text_lower == "redacted_in_free_version_contact_support@macaddress.io":
                if oui_element is not None and oui_element.text:
                    oui = oui_element.text.strip().replace(':', '').upper()
                    # 调试打印
                    # print(f"原始OUI: '{oui_element.text}'")
                    # print(f"处理后OUI: '{oui}'")
                    # print(f"OUI '{oui}' 是否在映射中: {oui in oui_mapping}")

                    if oui in oui_mapping:
                        new_vendor_name = oui_mapping[oui]
                        vendor_element.text = new_vendor_name
                        enhanced_count += 1
                        # print(f"补全OUI {oui}，从 'REDACTED...' 更改为 '{new_vendor_name}'")
                    
                    # 检查并补全 companyAddress
                    if company_address_element is not None and \
                       company_address_element.text and \
                       company_address_element.text.strip().lower() == "redacted_in_free_version_contact_support@macaddress.io":
                        if oui in oui_mapping:
                            company_address_element.text = oui_mapping[oui] + " (Derived from OUI)" # 简单填充
                            # print(f"补全地址 for OUI {oui}")
    
    print(f"XML文件解析完成。总记录数: {total_records}，补全厂商信息数: {enhanced_count}")
    return tree

def main():
    parser = argparse.ArgumentParser(description="MAC地址数据库补全器")
    parser.add_argument("--noupdate", action="store_true",
                        help="如果数据文件已存在，则跳过下载。")
    args = parser.parse_args()

    print("MAC地址数据库补全器开始运行...")

    # 1. 下载数据文件
    print("\n--- 正在下载数据文件 ---")
    download_file(MACADDRESS_IO_DB_URL, DATA_DIR, args.noupdate)
    for url in IEEE_OUI_URLS:
        download_file(url, DATA_DIR, args.noupdate)

    # 2. 加载IEEE OUI数据
    print("\n--- 正在加载IEEE OUI数据 ---")
    special_cases = load_special_cases(SPECIAL_CASES_FILE)
    oui_mapping = load_ieee_oui_data(DATA_DIR, special_cases)

    # 3. 补全macaddress.io数据库
    print("\n--- 正在补全MAC地址数据库 ---")
    macaddress_io_xml_path = os.path.join(DATA_DIR, MACADDRESS_IO_DB_URL.split('/')[-1])
    if not os.path.exists(macaddress_io_xml_path):
        print(f"错误: 找不到 {macaddress_io_xml_path} 文件，请确保已下载。")
        return

    enhanced_tree = enhance_mac_database(macaddress_io_xml_path, oui_mapping)

    # 4. 保存增强后的XML文件
    output_filepath = OUTPUT_FILENAME
    print(f"\n--- 正在保存补全后的XML文件到 {output_filepath} ---")
    enhanced_tree.write(output_filepath, encoding='utf-8', xml_declaration=True)
    print("脚本运行完成！")

if __name__ == "__main__":
    main()
