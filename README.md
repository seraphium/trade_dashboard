# 📈 IBKR 交易复盘分析平台

基于 Streamlit 的 Interactive Brokers (IBKR) 交易记录管理和分析系统，帮助您轻松进行交易复盘和分析。

## ✨ 功能特性

- 🔗 **自动数据获取**: 通过 IBKR Flex API 自动获取历史交易记录
- 📊 **可视化分析**: 多种图表展示交易表现和趋势
- 📝 **交易评论**: 为每笔交易添加个人评论和分析
- 💾 **数据持久化**: 自动保存评论到本地 JSON 文件
- 🔍 **智能筛选**: 多维度数据过滤和搜索功能
- 📈 **统计报告**: 详细的交易统计和分析报告
- 📱 **响应式设计**: 现代化的 Web 界面，支持各种设备

## 🚀 快速开始

### 1. 环境要求

- Python 3.10 或更高版本
- IBKR 账户（用于获取 Flex API 访问权限）

### 2. 安装依赖

```bash
# 克隆或下载项目到本地
cd trade_dashboard

# 安装 Python 依赖
pip install -r requirements.txt
```

### 3. 配置 IBKR Flex API

#### 3.1 创建 Flex Query

1. 登录您的 [IBKR 账户管理](https://www.interactivebrokers.com/en/index.php)
2. 导航到 **Reports** → **Flex Queries**
3. 点击 **Create** 创建新的 Flex Query
4. 选择以下配置：
   - **Query Type**: Activity Flex Query
   - **Sections**: 勾选 "Trades"
   - **Date Period**: 选择合适的日期范围
   - **Format**: XML
5. 保存 Query 并记录生成的 **Query ID**

#### 3.2 生成 Flex Token

1. 在同一页面，点击 **Generate Token**
2. 记录生成的 **Flex Web Service Token**

#### 3.3 配置应用

编辑 `config.yaml` 文件：

```yaml
ibkr:
  flex_token: "YOUR_FLEX_TOKEN_HERE"  # 替换为您的 Flex Token
  query_id: "YOUR_QUERY_ID_HERE"     # 替换为您的 Query ID
```

### 4. 运行应用

```bash
streamlit run app.py
```

应用将在浏览器中自动打开，通常地址为 `http://localhost:8501`

## 📖 使用指南

### 🔧 配置和连接

1. **首次使用**: 在侧边栏配置您的 IBKR API 信息
2. **测试连接**: 使用"测试连接"功能验证配置
3. **临时配置**: 如果没有 config.yaml，可以在界面中临时输入配置

### 📊 数据获取

1. **选择时间范围**: 使用预设选项或自定义日期范围
2. **获取数据**: 点击"获取交易数据"按钮
3. **查看统计**: 侧边栏会显示基本的数据统计信息

### 📋 交易记录管理

**交易记录** 标签页提供：

- 📝 **可编辑表格**: 直接在表格中添加或编辑交易评论
- 🔍 **多维筛选**: 按标的、买卖方向、价格等条件筛选
- 🔎 **评论搜索**: 在评论中搜索关键词
- 💾 **批量保存**: 一键保存所有评论更改
- 📥 **数据导出**: 导出筛选后的数据为 CSV 格式

### 📈 图表分析

**图表分析** 标签页包含：

- **交易时间线**: 可视化所有交易的时间和价格点
- **盈亏分析**: 累计盈亏趋势图（简化计算）
- **交易量分析**: 每日交易数量和金额统计
- **标的分布**: 各标的交易金额占比
- **评论分析**: 评论分类统计图表

### 💬 评论管理

**评论管理** 标签页功能：

- 📊 **评论统计**: 总评论数、分类统计等
- 📤 **数据导出**: 导出评论为 CSV 格式
- 💾 **数据备份**: 手动备份评论数据

### 📊 统计报告

**统计报告** 标签页提供：

- 📈 **基础指标**: 交易笔数、手续费、交易额等
- 📋 **按标的统计**: 各标的的详细交易统计
- 📅 **时间统计**: 按月度的交易统计

## 🗂️ 文件说明

```
trade_dashboard/
├── app.py                 # 主应用程序
├── data_fetcher.py        # IBKR 数据获取模块
├── comment_manager.py     # 评论管理模块
├── chart_utils.py         # 图表工具模块
├── config.yaml           # 配置文件
├── requirements.txt      # Python 依赖
├── README.md            # 说明文档
├── trade_comments.json  # 评论数据（运行时生成）
└── flex_trade_dashboard_spec.md  # 需求规格文档
```

## ⚠️ 注意事项

1. **API 限制**: IBKR Flex API 有访问频率限制，请避免频繁刷新数据
2. **数据安全**: 配置文件包含敏感信息，请勿分享或提交到版本控制
3. **盈亏计算**: 图表中的盈亏计算是简化版本，实际盈亏请以券商结算为准
4. **数据备份**: 建议定期备份 `trade_comments.json` 文件

## 🔧 高级配置

### 自定义配置

编辑 `config.yaml` 中的其他选项：

```yaml
# 应用配置
app:
  title: "我的交易分析平台"
  page_icon: "📊"
  layout: "wide"

# 数据设置
data:
  comments_file: "my_comments.json"
  cache_timeout: 7200  # 缓存2小时

# 图表设置
charts:
  default_height: 800
  theme: "plotly_dark"  # 或 "plotly_white"
```

### 环境变量

您也可以通过环境变量设置 API 配置：

```bash
export IBKR_FLEX_TOKEN="your_token_here"
export IBKR_QUERY_ID="your_query_id_here"
```

## 🐛 故障排除

### 常见问题

1. **连接失败**
   - 检查 Flex Token 和 Query ID 是否正确
   - 确认 IBKR 账户是否有 Flex Query 权限
   - 检查网络连接

2. **无数据返回**
   - 确认 Flex Query 包含 "Trades" 数据
   - 检查查询的时间范围是否包含交易记录
   - 验证 Query 状态是否为激活状态

3. **评论保存失败**
   - 检查文件写入权限
   - 确认磁盘空间充足

### 日志查看

应用会输出详细的日志信息，如果遇到问题，请查看控制台输出获取更多详情。

## 📞 支持

如有问题或建议，请通过以下方式联系：

- 查看控制台日志获取详细错误信息
- 确认所有依赖包已正确安装
- 验证 IBKR API 配置的正确性

## 📄 许可证

本项目仅供学习和个人使用。使用时请遵守 IBKR 的 API 使用条款。

---

**免责声明**: 本工具仅用于数据分析和记录管理，不构成投资建议。所有投资决策请基于您自己的判断和风险承受能力。 