# -*- coding: utf-8 -*-
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

def load_ieee_oui_data(data_folder):
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
            # 假设CSV文件格式为：Registry,Assignment,Organization Name,Organization Address
            # 我们主要关心 Assignment (OUI) 和 Organization Name
            # 需要跳过头部行，并根据实际CSV内容调整索引
            header_skipped = False
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
                        # 这些文件可能没有明确的"Assignment"列，而是直接OUI在第一列
                        # 需要更灵活的解析，或者根据文件类型单独处理
                        # 暂时先假设OUI在第二列，厂商名在第三列
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
                    # 如果以上都没有匹配，则尝试跳过第一行，并使用固定索引
                    print(f"无法自动识别 {filename} 的CSV头部，尝试跳过第一行并使用默认索引。")
                    header_skipped = True
                    continue # 跳过当前行，继续处理下一行数据

                if len(row) > max(oui_idx, org_name_idx):
                    oui = row[oui_idx].strip().replace('-', '').upper()
                    org_name = row[org_name_idx].strip()
                    if oui and org_name:
                        oui_mapping[oui] = org_name
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
    oui_mapping = load_ieee_oui_data(DATA_DIR)

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
