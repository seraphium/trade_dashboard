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

有两种配置方式（推荐使用 `.env` 文件）：

**方式一：使用 .env 文件（推荐）**

1. 复制 `env.example` 文件为 `.env`：
   ```bash
   cp env.example .env
   ```

2. 编辑 `.env` 文件：
   ```
   IBKR_FLEX_TOKEN=your_actual_flex_token_here
   IBKR_QUERY_ID=your_actual_query_id_here
   FINANCIAL_DATASETS_API_KEY=your_financial_datasets_api_key_here
   ```

3. 获取 Financial Datasets API 密钥：
   - 访问 [Financial Datasets](https://financialdatasets.ai)
   - 创建账户并获取 API 密钥
   - 将密钥填入 `.env` 文件中

**方式二：使用 config.yaml 文件**

编辑 `config.yaml` 文件：
```yaml
ibkr:
  flex_token: "YOUR_FLEX_TOKEN_HERE"  # 替换为您的 Flex Token
  query_id: "YOUR_QUERY_ID_HERE"     # 替换为您的 Query ID

financial_datasets:
  api_key: "YOUR_FINANCIAL_DATASETS_API_KEY_HERE"  # 替换为您的 Financial Datasets API 密钥
```

> **注意：** 如果同时存在 `.env` 和 `config.yaml`，系统将优先使用 `.env` 文件中的配置。

### 4. 运行应用

推荐使用启动脚本：

```bash
python start_app.py
```

或者直接使用 streamlit：

```bash
streamlit run app.py
```

应用将在浏览器中自动打开，通常地址为 `http://localhost:8501`

> **提示**: 启动脚本会自动检查依赖并提供更友好的错误提示

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
├── benchmark_data.py      # 基准指数数据获取模块
├── config.yaml           # 配置文件
├── config.example.yaml   # 配置文件示例
├── env.example           # 环境变量配置示例
├── requirements.txt      # Python 依赖
├── README.md            # 说明文档
├── .gitignore           # Git 忽略文件
├── trade_comments.json  # 评论数据（运行时生成）
└── flex_trade_dashboard_spec.md  # 需求规格文档
```

## ⚠️ 注意事项

1. **API 限制**: IBKR Flex API 有访问频率限制，请避免频繁刷新数据
2. **数据安全**: 
   - `.env` 和 `config.yaml` 文件包含敏感的 API 信息，请勿分享或提交到版本控制
   - `.env` 文件已自动添加到 `.gitignore` 中
   - 建议使用 `.env` 文件而非 `config.yaml` 来存储敏感信息
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

### 配置优先级

应用程序按以下优先级加载配置：

1. **环境变量**（最高优先级）
2. **`.env` 文件**
3. **`config.yaml` 文件**（最低优先级）

您可以通过环境变量临时覆盖配置：

```bash
export IBKR_FLEX_TOKEN="your_token_here"
export IBKR_QUERY_ID="your_query_id_here"
export FINANCIAL_DATASETS_API_KEY="your_api_key_here"
streamlit run app.py
```

## 🐛 故障排除

### 常见问题

1. **IBKR 连接失败**
   - 检查 Flex Token 和 Query ID 是否正确
   - 确认 IBKR 账户是否有 Flex Query 权限
   - 检查网络连接

2. **无交易数据返回**
   - 确认 Flex Query 包含 "Trades" 数据
   - 检查查询的时间范围是否包含交易记录
   - 验证 Query 状态是否为激活状态

3. **基准数据获取失败**
   - **问题现象**: 显示 API 连接失败或认证错误
   - **解决方案**:
     1. 点击 "🔗 测试 Financial Datasets API 连接" 按钮检查连接状态
     2. 检查 API 密钥是否正确配置在 `.env` 文件中
     3. 确认 Financial Datasets API 账户余额和权限
     4. 如果API连接失败，可以勾选 "🧪 使用模拟数据（演示模式）" 进行功能演示
     5. 验证网络连接，确保能访问 financialdatasets.ai
     6. 手动测试 API 连接：
        ```bash
        # 设置您的API密钥
        export FINANCIAL_DATASETS_API_KEY="your_api_key_here"
        python -c "
        import requests
        headers = {'X-API-KEY': 'your_api_key_here'}
        response = requests.get('https://api.financialdatasets.ai/prices?ticker=SPY&interval=day&limit=1', headers=headers)
        print(response.status_code, response.text[:200])
        "
        ```

4. **评论保存失败**
   - 检查文件写入权限
   - 确认磁盘空间充足

### 基准数据功能说明

**🆚 基准对比** 功能使用 Financial Datasets API 获取高质量的市场数据：

- **实时数据**: 获取真实的市场指数数据（SPY、QQQ 等）
- **高质量数据**: Financial Datasets API 提供更稳定可靠的金融数据服务
- **模拟数据**: 如果 API 连接有问题，可使用模拟数据进行功能演示
- **重试机制**: 自动重试失败的数据获取，提高成功率
- **多指数支持**: 支持同时获取多个基准指数进行对比
- **API 优势**: 相比传统的网页抓取方式，API 访问更稳定，数据质量更高

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