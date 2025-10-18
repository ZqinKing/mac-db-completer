# MAC地址数据库补全器 (`mac-db-completer`)

## 简介
这是一个Python脚本，旨在补全 `macaddress.io` 免费提供的MAC地址数据库中缺失的厂商信息。它通过整合IEEE官方发布的OUI（组织唯一标识符）数据，来增强现有数据库的准确性和完整性。

## 功能
*   自动下载 `macaddress.io` 的XML数据库文件。
*   自动下载IEEE提供的多个OUI相关CSV数据文件。
*   解析并合并所有数据源。
*   识别 `macaddress.io` 数据库中厂商信息被标记为 "macaddress.io" 的条目。
*   使用IEEE数据中查找到的真实厂商信息替换这些占位符。
*   生成一个包含补全后数据的新XML文件，格式与原始文件保持一致。

## 数据源
本项目使用以下数据源进行补全：
*   `macaddress.io` 数据库: `https://macaddress.io/database/macaddress.io-db.xml`
*   IEEE OUI 数据:
    *   `http://standards-oui.ieee.org/oui/oui.csv`
    *   `http://standards-oui.ieee.org/cid/cid.csv`
    *   `http://standards-oui.ieee.org/iab/iab.csv`
    *   `http://standards-oui.ieee.org/oui28/mam.csv`
    *   `http://standards-oui.ieee.org/oui36/oui36.csv`

## 使用方法
（待定：此处将包含如何安装依赖、如何运行脚本以及如何获取输出文件的详细说明。）

## 许可证
本项目采用 [GNU General Public License v3.0 (GPLv3)](LICENSE) 许可。
