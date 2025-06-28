# Flex-Based Trade Review Dashboard Specification

## 一、项目目标

利用 IBKR 提供的 Flex Web API ，构建一个无需前端编码的交易复盘平台。系统支持:

- 从 Flex Web API 自动拉取账户历史交易记录;
- 在交易图上表示各笔交易;
- 允许用户为每笔交易填写事后评价 (comments);
- 支持以 Streamlit系统为前端表示界面;
- 将评论保存为本地 CSV 或 JSON;
- 支持不同经纪期间的查询和分析。

---

## 二、功能需求

### 1. 数据获取

- 从 IBKR Flex Web API 拉取指定 query\_id 和 token 对应的历史数据;
- 支持指定时间范围 (start\_date, end\_date);
- 支持拉取 Trades (Historical Executions)、Account Summary 、P&L 等模块;
- 给出数据输入解析失败的提示和日志输出;

### 2. 表格显示和交互

- 在一个可搜索和排序的表格中显示交易记录;
- 每条记录包括: 时间，标的，买卖，数量，成交价，费用，等等;
- 允许用户在表格中直接填写“评论”列，表示个人交易心得;
- 提供上传或保存评论按钮，将评论与交易 ID 绑定并按时保存。

### 3. 图表显示

- 以 Plotly 或 Altair 绘制交易时间序列图；
- 按照交易时间和价格点时间点，显示展示评论滑窗；
- 支持按名称/标的/时间过滤图形;

### 4. 评论持久化

- 用户填写的 comments 保存为本地 JSON 或 CSV ，绑定交易 ID；
- 每次启动项目时，自动读取已有评论文件，重新进行合并;

---

## 三、技术设计

### 1. 运行环境

- Python 3.10+
- 包含以下包:
  - streamlit
  - ibflex
  - pandas
  - plotly / altair
  - pyyaml / json / csv

### 2. 部署方案

- 本地运行：对接 IB Gateway API / Flex API；
- cloud 部署：只限 Flex API，需用户先在 IBKR 编辑好 query\_id + token;

### 3. 数据结构

- Trades 表格：ID，datetime，symbol，side，qty，price，commission，comment
- Comments 保存文件：

```json
[
  {"trade_id": "123456789", "comment": "补付觉得很输", "timestamp": "2024-05-01T12:30:00"},
  ...
]
```

---

## 四、后续扩展构思

- 支持别名帐号/账户类型分别处理
- 增加惊识性分析（如超走分析，利润并线比较）
- 支持 comment 分类标签（好交易，失败，过早/过晚）
- 评论与合算性表现（如给出后悔率，或手势错误率）

