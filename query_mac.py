# query_mac.py
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

import xml.etree.ElementTree as ET
import argparse
import re

def standardize_mac_address(mac_address):
    """
    标准化MAC地址，移除所有分隔符并转换为大写。
    支持以下格式：
    - xxxxxxxxxxxx (12位十六进制)
    - xx:xx:xx:xx:xx:xx
    - xx-xx-xx-xx-xx-xx
    - xxxxxx-xxxxxx (交换机上常见格式)
    """
    # 移除所有非十六进制字符
    standardized = re.sub(r'[^0-9a-fA-F]', '', mac_address)
    return standardized.upper()

def main():
    parser = argparse.ArgumentParser(description="MAC地址查询工具")
    parser.add_argument("mac_address", help="要查询的MAC地址")
    args = parser.parse_args()

    mac_to_query = standardize_mac_address(args.mac_address)
    print(f"正在查询标准化MAC地址: {mac_to_query}")

    db_filepath = "macaddress.io-db-enhanced.xml"
    
    # 用于存储最长匹配的OUI和对应的厂商信息
    best_match_oui = ""
    best_match_company_name = "未知厂商"
    best_match_company_address = "未知地址"

    try:
        # 使用iterparse进行流式解析，避免一次性加载大文件
        context = ET.iterparse(db_filepath, events=("start", "end"))
        # 跳过根元素
        event, root = next(context) 

        for event, elem in context:
            if event == "end" and elem.tag == "record":
                oui_element = elem.find("oui")
                company_name_element = elem.find("companyName")
                company_address_element = elem.find("companyAddress")

                if oui_element is not None and oui_element.text:
                    db_oui = standardize_mac_address(oui_element.text)
                    
                    # 检查是否是前缀匹配，并且是目前找到的最长匹配
                    if mac_to_query.startswith(db_oui) and len(db_oui) > len(best_match_oui):
                        best_match_oui = db_oui
                        if company_name_element is not None and company_name_element.text:
                            best_match_company_name = company_name_element.text.strip()
                        if company_address_element is not None and company_address_element.text:
                            best_match_company_address = company_address_element.text.strip()
                
                # 清除已处理的元素，释放内存
                elem.clear()
                root.clear() # 清除根元素的子元素，防止内存泄漏

    except FileNotFoundError:
        print(f"错误: 数据库文件 '{db_filepath}' 未找到。请确保文件存在。")
        return
    except ET.ParseError as e:
        print(f"错误: 解析XML文件时出错: {e}")
        return

    if best_match_oui:
        print("\n--- 查询结果 ---")
        print(f"匹配到的OUI: {best_match_oui}")
        print(f"厂商名称: {best_match_company_name}")
        print(f"厂商地址: {best_match_company_address}")
    else:
        print("\n未找到匹配的厂商信息。")

if __name__ == "__main__":
    main()
