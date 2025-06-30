# 时间加权收益率(TWR)技术规范文档

## 1. 概述

本文档详细描述了在IBKR交易面板中实现时间加权收益率(TWR)计算的技术方案。TWR是评估投资策略本身表现的关键指标，通过剔除现金流的影响，提供更准确的投资绩效评估。

## 2. 核心概念

### 2.1 TWR vs MWR 对比

| 指标 | 适用场景 | 现金流影响 | 计算方式 |
|------|----------|------------|----------|
| 时间加权收益率(TWR) | 评估投资策略本身表现 | 剔除入金/出金影响 | 几何连乘：∏(1+r_i)-1 |
| 资金加权收益率(MWR/IRR) | 评估投资者资金配置时机 | 包含入金/出金影响 | 内部收益率求解 |

### 2.2 TWR 计算原理

TWR通过将投资期间按现金流事件分割为多个子区间，计算每个子区间的收益率，然后几何连乘得到总收益率：

```
TWR = ∏(1 + r_i) - 1
```

其中：
- r_i = (NAV_i^- - NAV_{i-1}) / NAV_{i-1}
- NAV_i^- 是现金流发生前的净资产价值
- NAV_{i-1} 是上一个时点的净资产价值

## 3. 数据需求

### 3.1 必需的Flex API数据

| 数据类型 | Flex Section | 字段说明 | 用途 |
|----------|--------------|----------|------|
| 每日净资产 | EQUT | Net Asset Value (交易日) | 计算每日收益率 |
| 现金流 | CTRN | Cash Transactions | 识别现金流事件 |
| 持仓快照 | POST/POSS | Positions | 验证NAV计算 |
| MTM汇总 | MTMP | MTM Performance Summary | 结果对比验证 |

### 3.2 Flex Query 配置要求

```xml
<FlexQueryRequest>
    <FlexQuery queryName="TWR_Analysis" queryType="ActivityFlexQuery">
        <date>YYYYMMDD</date>
        <period>YYYYMMDD;YYYYMMDD</period>
        <NetAssetValue>Y</NetAssetValue>
        <CashTransactions>Y</CashTransactions>
        <Positions>Y</Positions>
        <MTMPerformanceSummary>Y</MTMPerformanceSummary>
    </FlexQuery>
</FlexQueryRequest>
```

## 4. 实现架构

### 4.1 核心模块

```
twr_calculator.py
├── TWRCalculator (主计算类)
├── NAVProcessor (NAV数据处理)
├── CashFlowProcessor (现金流处理)  
├── TimeSeriesProcessor (时间序列处理)
└── PerformanceMetrics (绩效指标计算)
```

### 4.2 数据流程

```
Flex API → XML Response → Data Parsing → NAV Series + Cash Flows → TWR Calculation → Results
```

## 5. 实现细节

### 5.1 数据获取扩展

在现有的`IBKRDataFetcher`基础上，新增以下方法：

```python
def fetch_nav_data(self, start_date: str, end_date: str) -> pd.DataFrame
def fetch_cash_transactions(self, start_date: str, end_date: str) -> pd.DataFrame
def fetch_positions(self, start_date: str, end_date: str) -> pd.DataFrame
def fetch_mtm_summary(self, start_date: str, end_date: str) -> pd.DataFrame
```

### 5.2 TWR计算步骤

1. **数据预处理**
   - 获取完整的NAV时间序列
   - 识别并标记所有现金流事件
   - 处理缺失值和异常值

2. **时间区间分割**
   - 按现金流事件将时间线分割为子区间
   - 每个子区间内无现金流影响

3. **子区间收益率计算**
   - 计算每个子区间的收益率
   - 处理多币种和汇率转换

4. **TWR汇总**
   - 几何连乘得到总TWR
   - 计算月度、季度、年度TWR

### 5.3 现金流处理

现金流类型包括：
- 入金/出金 (Deposits/Withdrawals)
- 股息分红 (Dividends)
- 利息收入 (Interest)
- 费用支出 (Fees)

### 5.4 多币种支持

- 所有计算以基准货币为准
- 使用IBKR提供的汇率数据
- 支持实时汇率更新

## 6. 性能优化

### 6.1 数据缓存策略

- 使用Streamlit缓存机制
- NAV数据缓存1小时
- 现金流数据缓存24小时

### 6.2 计算优化

- 使用pandas向量化计算
- 并行处理多个时间序列
- 增量更新机制

## 7. 错误处理

### 7.1 常见问题及解决方案

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| NAV数据缺失 | 非交易日或数据延迟 | 前向填充或线性插值 |
| 现金流时间戳不匹配 | 时区差异 | 标准化为UTC时间 |
| 多币种汇率问题 | 汇率数据缺失 | 使用备用汇率源 |
| 期货日结算 | 特殊的计价方式 | 特殊处理期货MTM |

## 8. 验证与测试

### 8.1 数据验证

- 与IBKR官方PortfolioAnalyst对比
- 月度/季度TWR误差应<0.01%
- 现金流事件完整性检查

### 8.2 单元测试

```python
class TestTWRCalculator:
    def test_simple_twr_calculation()
    def test_with_cash_flows()
    def test_multi_currency()
    def test_edge_cases()
```

## 9. 用户界面

### 9.1 新增功能模块

- TWR分析页面
- 收益率曲线图表
- 现金流影响分析
- 与基准对比

### 9.2 图表组件

- 月度/季度TWR柱状图
- 累计收益率曲线
- 现金流时间线
- 收益率分解图

## 10. 部署与维护

### 10.1 配置要求

- 新增TWR相关的Flex Query模板
- 配置文件扩展
- 依赖包更新

### 10.2 监控指标

- API调用成功率
- 计算准确性
- 性能指标
- 用户使用情况

## 11. 未来扩展

### 11.1 高级功能

- 归因分析
- 风险调整收益率
- 基准跟踪误差
- 滚动窗口分析

### 11.2 可视化增强

- 交互式图表
- 自定义报告
- 数据导出功能
- 移动端适配

---

本技术规范为TWR功能的完整实现提供了详细的指导方针，确保功能的准确性、可靠性和可扩展性。 