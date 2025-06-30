# 📈 API 迁移说明：从 yfinance 到 Financial Datasets

## 🔄 迁移概述

由于 yfinance 库的不稳定性，我们已将基准数据获取服务从 yfinance 迁移到 [Financial Datasets API](https://financialdatasets.ai)。

## ✅ 迁移完成的更改

### 1. 依赖包更新
- **移除**: `yfinance>=0.2.18`
- **保留**: `requests>=2.28.0`（用于API调用）

### 2. 配置文件更新

#### env.example
新增 Financial Datasets API 密钥配置：
```bash
FINANCIAL_DATASETS_API_KEY=your_financial_datasets_api_key_here
```

#### config.yaml (可选)
新增配置段：
```yaml
financial_datasets:
  api_key: "YOUR_FINANCIAL_DATASETS_API_KEY_HERE"
```

### 3. 核心代码更改

#### benchmark_data.py
- 完全重写了 `BenchmarkDataFetcher` 类
- 使用 Financial Datasets API 端点：`https://api.financialdatasets.ai/prices`
- 保持原有的方法接口，确保向后兼容
- 新增 API 密钥管理和身份验证
- 改进的错误处理和重试机制

#### app.py
- 更新方法调用：`test_yfinance_connection()` → `test_api_connection()`
- 更新UI文本，反映新的API服务

#### README.md
- 更新配置说明，包含 Financial Datasets API 设置
- 更新故障排除指南
- 更新基准数据功能说明

## 🚀 Financial Datasets API 优势

### 相比 yfinance 的改进：
1. **稳定性**: 专业API服务，无网页抓取的不确定性
2. **可靠性**: 官方API支持，减少连接失败
3. **数据质量**: 高质量的金融数据源
4. **性能**: 专为API访问优化，响应更快
5. **支持**: 专业的API文档和客户支持

### 支持的功能：
- ✅ 历史日线数据
- ✅ 实时价格数据
- ✅ 多种时间间隔
- ✅ 全球市场覆盖
- ✅ 高频数据支持

## 🔧 配置步骤

### 1. 获取 API 密钥
1. 访问 [Financial Datasets](https://financialdatasets.ai)
2. 注册账户
3. 获取 API 密钥

### 2. 配置环境变量
编辑 `.env` 文件：
```bash
# 现有的 IBKR 配置
IBKR_FLEX_TOKEN=your_flex_token_here
IBKR_QUERY_ID=your_query_id_here

# 新增的 Financial Datasets API 配置
FINANCIAL_DATASETS_API_KEY=your_financial_datasets_api_key_here
```

### 3. 测试连接
在应用中点击 "🔗 测试 Financial Datasets API 连接" 按钮验证配置。

## 🧪 向后兼容性

### 保持不变的功能：
- ✅ 所有原有的基准数据分析功能
- ✅ 图表显示格式
- ✅ 数据缓存机制
- ✅ 模拟数据生成功能
- ✅ 多基准指数对比

### API 接口兼容：
- ✅ `fetch_benchmark_data()` 方法签名不变
- ✅ 返回的 DataFrame 格式保持一致
- ✅ 所有计算指标（收益率、波动率等）保持不变

## ⚠️ 迁移注意事项

### 1. 成本考虑
- Financial Datasets API 可能需要付费（根据使用量）
- 建议查看其定价政策和免费额度

### 2. 依赖包清理
如果您之前安装了 yfinance，可以选择性移除：
```bash
pip uninstall yfinance
```

### 3. 基准指数符号
部分指数符号可能有差异，已更新的映射：
- 移除：`^GSPC`、`^IXIC`、`^DJI`（Yahoo Finance 特有格式）
- 新增：`SPTM`、`TQQQ`、`UPRO`（标准ETF符号）

## 🔍 故障排除

### 常见问题：

#### 1. API 密钥认证失败
```
❌ API密钥无效或已过期
```
**解决方案**：
- 检查 `.env` 文件中的 API 密钥是否正确
- 确认 Financial Datasets 账户状态
- 验证 API 密钥权限

#### 2. 请求频率限制
```
❌ API请求频率限制，请稍后重试
```
**解决方案**：
- 等待一段时间后重试
- 检查API计划的请求频率限制
- 考虑升级API计划

#### 3. 网络连接问题
```
❌ 网络请求失败
```
**解决方案**：
- 检查网络连接
- 验证防火墙设置
- 使用模拟数据进行功能演示

## 📞 支持

如果在迁移过程中遇到问题：

1. **检查日志**: 查看控制台输出的详细错误信息
2. **测试连接**: 使用应用内的连接测试功能
3. **使用模拟数据**: 在解决API问题时，可以使用模拟数据继续使用其他功能
4. **查看文档**: 参考 Financial Datasets API 官方文档

## 📅 迁移时间线

- ✅ **2024-xx-xx**: 完成代码迁移
- ✅ **2024-xx-xx**: 更新文档和配置
- ✅ **2024-xx-xx**: 测试验证功能完整性

---

**说明**: 此迁移旨在提供更稳定可靠的基准数据服务。如果您在使用过程中发现任何问题，请及时反馈。

# API 迁移和新功能说明

## 版本历史

### v2.0 - TWR时间加权收益率功能 (2024-01)

#### 新增功能
- ⏱️ **时间加权收益率(TWR)分析**: 全面的投资绩效评估功能
- 📊 **NAV数据获取**: 从IBKR Flex API获取每日净资产价值
- 💰 **现金流分析**: 自动识别和处理入金/出金等现金流事件
- 📈 **绩效指标仪表板**: 包含收益率、波动率、夏普比率等关键指标
- 📅 **周期性分析**: 支持月度、季度、年度TWR计算

#### 新增模块
1. **twr_calculator.py**: TWR计算器核心模块
   - `TWRCalculator`: 主计算类
   - `NAVProcessor`: NAV数据处理器
   - `CashFlowProcessor`: 现金流处理器
   - `TimeSeriesProcessor`: 时间序列处理器
   - `PerformanceMetrics`: 绩效指标计算器

2. **扩展的data_fetcher.py**: 
   - `fetch_nav_data()`: 获取NAV数据
   - `fetch_cash_transactions()`: 获取现金流数据
   - `fetch_positions()`: 获取持仓数据

3. **扩展的chart_utils.py**:
   - `create_twr_chart()`: TWR时间序列图表
   - `create_periodic_twr_chart()`: 周期性TWR图表
   - `create_twr_metrics_dashboard()`: 绩效指标仪表板
   - `create_cash_flow_impact_chart()`: 现金流影响分析图表

4. **扩展的app.py**:
   - 新增"⏱️ TWR分析"标签页
   - `show_twr_analysis()`: TWR分析页面
   - 侧边栏TWR数据获取功能

#### API配置要求

为了使用TWR功能，您的IBKR Flex Query需要包含以下数据节点：

```xml
<FlexQuery queryName="TWR_Analysis" queryType="ActivityFlexQuery">
    <!-- 必需数据 -->
    <NetAssetValue>Y</NetAssetValue>        <!-- 每日净资产价值 -->
    <CashTransactions>Y</CashTransactions>  <!-- 现金流数据 -->
    
    <!-- 可选数据 -->
    <Positions>Y</Positions>               <!-- 持仓快照 -->
    <Trades>Y</Trades>                     <!-- 交易记录 -->
    <MTMPerformanceSummary>Y</MTMPerformanceSummary> <!-- MTM汇总 -->
</FlexQuery>
```

#### 技术特性

1. **时间加权收益率计算**
   - 自动识别现金流事件
   - 按现金流分割时间区间
   - 几何连乘计算总收益率
   - 剔除入金/出金时机影响

2. **多维度分析**
   - 总TWR和年化收益率
   - 风险指标（波动率、夏普比率）
   - 最大回撤分析
   - 现金流影响评估

3. **可视化图表**
   - NAV和累计收益率双轴图
   - 现金流事件标记
   - 绩效指标仪表板
   - 周期性收益率柱状图

4. **数据验证和错误处理**
   - 完整的数据清理和验证
   - 缺失值前向填充
   - 边界情况处理
   - 详细错误日志

#### 使用方法

1. **配置Flex Query**
   - 确保包含NetAssetValue和CashTransactions数据
   - 设置适当的日期范围

2. **获取数据**
   - 在侧边栏点击"📈 获取 TWR 数据"
   - 系统自动获取NAV和现金流数据

3. **查看分析**
   - 切换到"⏱️ TWR分析"标签页
   - 查看详细的绩效分析结果

#### 测试验证

包含完整的测试套件 (`test_twr.py`)：
- 基础TWR计算测试
- 现金流处理测试
- 周期性分析测试
- 绩效指标计算测试
- 边界情况处理测试

#### 技术文档

详细的技术规范请参考：
- `TWR_Technical_Specification.md`: 完整的技术实现文档
- 包含算法原理、数据流程、错误处理等详细说明

#### 兼容性

- 保持与现有交易分析功能的完全兼容性
- 不影响原有的数据获取和图表功能
- 可独立使用TWR分析功能

#### 未来规划

- 归因分析功能
- 基准跟踪误差计算
- 风险调整收益率指标
- 移动端界面优化

---

## v1.0 - 基础交易分析功能

### 核心功能
- 📊 交易记录获取和管理
- 📈 交易图表和可视化分析
- 💬 交易评论和复盘功能
- 🆚 基准指数对比分析
- 📋 交易统计报告

### 支持的数据类型
- 交易记录 (Trades)
- 账户信息 (Account Information)
- 基准指数数据

---

此文档将持续更新以反映系统的最新功能和改进。 