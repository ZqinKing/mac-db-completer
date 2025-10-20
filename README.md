# MAC地址数据库补全器 (`mac-db-completer`)

## 简介
这是一个Python脚本，旨在补全 `macaddress.io` 免费提供的MAC地址数据库中缺失的厂商信息。它通过整合IEEE官方发布的OUI（组织唯一标识符）数据，来增强现有数据库的准确性和完整性。

## 功能
*   **自动数据下载**：自动下载 `macaddress.io` 的XML数据库文件和IEEE提供的多个OUI相关CSV数据文件。
*   **数据解析与合并**：解析并合并所有数据源，构建OUI到厂商名称的映射。
*   **厂商信息补全**：识别 `macaddress.io` 数据库中厂商信息被标记为 "redacted_in_free_version_contact_support@macaddress.io" 的条目，并使用IEEE数据中查找到的真实厂商信息替换这些占位符。同时，也会尝试补全缺失的厂商地址。
*   **厂商名称简化**：通过一系列预定义的规则（如移除通用公司后缀、处理大小写、移除括号内容等）和 `special_cases.json` 文件中的特殊映射，对厂商名称进行简化和标准化，以提高匹配准确性。
*   **生成增强数据库**：生成一个包含补全后数据的新XML文件 (`macaddress.io-db-enhanced.xml`)，格式与原始文件保持一致。
*   **MAC地址查询**：提供一个命令行工具，用于查询增强后的数据库，支持多种MAC地址格式的标准化输入，并返回最长匹配的厂商信息。

## 数据源
本项目使用以下数据源进行补全：
*   `macaddress.io` 数据库: `https://macaddress.io/database/macaddress.io-db.xml`
*   IEEE OUI 数据:
    *   `http://standards-oui.ieee.org/oui/oui.csv`
    *   `http://standards-oui.ieee.org/cid/cid.csv`
    *   `http://standards-oui.ieee.org/iab/iab.csv`
    *   `http://standards-oui.ieee.org/oui28/mam.csv`
    *   `http://standards-oui.ieee.org/oui36/oui36.csv`

## 工作流程
本项目主要包含两个独立的Python脚本，它们协同工作以提供完整的MAC地址数据库补全和查询功能：

1.  **`update_mac_database.py`**：负责下载原始数据、整合IEEE OUI数据、补全 `macaddress.io` 数据库，并生成增强后的XML数据库文件。
2.  **`query_mac.py`**：负责加载由 `update_mac_database.py` 生成的增强数据库，并提供命令行接口供用户查询MAC地址对应的厂商信息。

## 使用方法

### 1. 环境准备
确保您的系统已安装 Python 3。
安装所需的Python库：
```bash
pip install requests lxml
```
（注：`lxml` 库虽然在当前脚本中没有直接导入，但 `xml.etree.ElementTree` 是Python标准库的一部分，通常不需要额外安装。如果遇到XML解析问题，`lxml` 是一个更强大的替代品，但目前看来不是必需的。这里保留 `requests` 即可。）

### 2. 更新和生成增强数据库
运行 `update_mac_database.py` 脚本来下载最新的数据并生成增强的MAC地址数据库文件 (`macaddress.io-db-enhanced.xml`)。
```bash
python update_mac_database.py
```
如果您不想每次运行时都重新下载数据文件（例如，当您已经下载过并且只需要重新处理数据时），可以使用 `--noupdate` 参数：
```bash
python update_mac_database.py --noupdate
```
生成的 `macaddress.io-db-enhanced.xml` 文件将位于项目根目录。

### 3. 查询MAC地址
使用 `query_mac.py` 脚本来查询增强数据库中的MAC地址信息。您需要提供一个MAC地址作为参数。
脚本支持多种MAC地址格式，例如：`00:1A:2B:3C:4D:5E`、`00-1A-2B-3C-4D-5E`、`001A2B3C4D5E` 等。

**示例：**
```bash
python query_mac.py 00:1A:2B:3C:4D:5E
```
或者
```bash
python query_mac.py 001A2B
```
脚本将输出匹配到的OUI、厂商名称和厂商地址。

## 许可证
本项目采用 [GNU General Public License v3.0 (GPLv3)](LICENSE) 许可。
