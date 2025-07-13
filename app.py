"""
IBKR 交易复盘分析平台
基于 Streamlit 的交易记录管理和分析系统
"""
import streamlit as st
import pandas as pd
import yaml
from datetime import datetime, date, timedelta
import logging
from io import StringIO

# 导入自定义模块
from data_fetcher import IBKRDataFetcher, test_connection
from comment_manager import CommentManager
from chart_utils import ChartGenerator
from benchmark_data import BenchmarkDataFetcher
from twr_calculator import TWRCalculator

# 配置页面
st.set_page_config(
    page_title="交易复盘分析平台",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_trades_data_types(df: pd.DataFrame) -> pd.DataFrame:
    """验证并修正交易数据的数据类型"""
    if df.empty:
        return df
    
    df = df.copy()
    
    # 确保comment列为字符串类型 - 特别处理CSV加载时的NaN值
    if 'comment' in df.columns:
        # 将NaN和'nan'字符串都转换为空字符串
        df['comment'] = df['comment'].fillna('').astype(str)
        df['comment'] = df['comment'].replace('nan', '')
        df['comment'] = df['comment'].replace('None', '')
    else:
        df['comment'] = ''
    
    # 确保comment_category列为字符串类型
    if 'comment_category' in df.columns:
        df['comment_category'] = df['comment_category'].fillna('Neutral').astype(str)
        df['comment_category'] = df['comment_category'].replace('nan', 'Neutral')
        df['comment_category'] = df['comment_category'].replace('None', 'Neutral')
    else:
        df['comment_category'] = 'Neutral'
    
    # 确保其他字符串列的数据类型
    string_columns = ['trade_id', 'symbol', 'side', 'currency', 'exchange']
    for col in string_columns:
        if col in df.columns:
            df[col] = df[col].fillna('').astype(str)
            df[col] = df[col].replace('nan', '')
            df[col] = df[col].replace('None', '')
    
    # 确保数值列的数据类型
    numeric_columns = ['quantity', 'price', 'proceeds', 'commission']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 确保日期时间列的数据类型
    if 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
    
    logger.debug(f"数据类型验证完成 - comment列类型: {df['comment'].dtype if 'comment' in df.columns else 'N/A'}")
    
    return df

# 初始化会话状态
def init_session_state():
    """初始化会话状态变量"""
    if 'data_fetcher' not in st.session_state:
        st.session_state.data_fetcher = IBKRDataFetcher()
    if 'comment_manager' not in st.session_state:
        st.session_state.comment_manager = CommentManager()
    if 'chart_generator' not in st.session_state:
        st.session_state.chart_generator = ChartGenerator()
    if 'benchmark_fetcher' not in st.session_state:
        st.session_state.benchmark_fetcher = BenchmarkDataFetcher()
    if 'trades_df' not in st.session_state:
        st.session_state.trades_df = pd.DataFrame()
    if 'benchmark_data' not in st.session_state:
        st.session_state.benchmark_data = {}
    if 'portfolio_data' not in st.session_state:
        st.session_state.portfolio_data = pd.DataFrame()
    if 'twr_calculator' not in st.session_state:
        st.session_state.twr_calculator = TWRCalculator()
    if 'nav_data' not in st.session_state:
        st.session_state.nav_data = pd.DataFrame()
    if 'cash_flow_data' not in st.session_state:
        st.session_state.cash_flow_data = pd.DataFrame()
    if 'twr_result' not in st.session_state:
        st.session_state.twr_result = {}
    
    # 启动时自动加载本地缓存数据
    load_cached_data()

def load_cached_data():
    """加载本地缓存的CSV数据"""
    import os
    
    # 创建数据目录
    data_dir = "cached_data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # 定义文件路径
    trades_file = os.path.join(data_dir, "trades_data.csv")
    nav_file = os.path.join(data_dir, "nav_data.csv")
    cash_flow_file = os.path.join(data_dir, "cash_flow_data.csv")
    benchmark_file = os.path.join(data_dir, "benchmark_data.csv")
    twr_file = os.path.join(data_dir, "twr_result.csv")
    
    try:
        # 加载交易数据
        if os.path.exists(trades_file):
            trades_df = pd.read_csv(trades_file)
            if not trades_df.empty:
                # 验证并修正数据类型
                trades_df = validate_trades_data_types(trades_df)
                st.session_state.trades_df = trades_df
                logger.info(f"✅ 加载缓存交易数据: {len(trades_df)} 条记录")
        
        # 加载NAV数据
        if os.path.exists(nav_file):
            nav_df = pd.read_csv(nav_file)
            if not nav_df.empty:
                # 转换日期列
                if 'reportDate' in nav_df.columns:
                    nav_df['reportDate'] = pd.to_datetime(nav_df['reportDate'])
                elif 'date' in nav_df.columns:
                    nav_df['date'] = pd.to_datetime(nav_df['date'])
                st.session_state.nav_data = nav_df
                logger.info(f"✅ 加载缓存NAV数据: {len(nav_df)} 条记录")
        
        # 加载现金流数据
        if os.path.exists(cash_flow_file):
            cash_df = pd.read_csv(cash_flow_file)
            if not cash_df.empty:
                # 转换日期列
                if 'reportDate' in cash_df.columns:
                    cash_df['reportDate'] = pd.to_datetime(cash_df['reportDate'])
                if 'dateTime' in cash_df.columns:
                    cash_df['dateTime'] = pd.to_datetime(cash_df['dateTime'])
                st.session_state.cash_flow_data = cash_df
                logger.info(f"✅ 加载缓存现金流数据: {len(cash_df)} 条记录")
        
        # 加载基准数据
        if os.path.exists(benchmark_file):
            benchmark_df = pd.read_csv(benchmark_file)
            if not benchmark_df.empty:
                # 转换日期列
                if 'Date' in benchmark_df.columns:
                    benchmark_df['Date'] = pd.to_datetime(benchmark_df['Date'])
                
                # 按symbol分组重建benchmark_data字典
                benchmark_data = {}
                for symbol in benchmark_df['Symbol'].unique():
                    symbol_data = benchmark_df[benchmark_df['Symbol'] == symbol].copy()
                    symbol_data = symbol_data.drop('Symbol', axis=1)
                    benchmark_data[symbol] = symbol_data
                
                st.session_state.benchmark_data = benchmark_data
                logger.info(f"✅ 加载缓存基准数据: {len(benchmark_data)} 个指数")
        
        # 加载TWR结果
        if os.path.exists(twr_file):
            twr_df = pd.read_csv(twr_file)
            if not twr_df.empty:
                # 重建TWR结果字典
                twr_result = {}
                for _, row in twr_df.iterrows():
                    twr_result[row['key']] = row['value']
                
                # 转换数值类型
                numeric_keys = ['total_twr', 'annualized_return', 'volatility', 'sharpe_ratio', 'max_drawdown', 'days']
                for key in numeric_keys:
                    if key in twr_result:
                        try:
                            twr_result[key] = float(twr_result[key])
                        except (ValueError, TypeError):
                            pass
                
                # 加载TWR时间序列数据
                twr_timeseries_file = os.path.join(data_dir, "twr_timeseries.csv")
                if os.path.exists(twr_timeseries_file):
                    try:
                        twr_timeseries = pd.read_csv(twr_timeseries_file)
                        if not twr_timeseries.empty:
                            # 转换日期列
                            twr_timeseries['date'] = pd.to_datetime(twr_timeseries['date'])
                            twr_result['twr_timeseries'] = twr_timeseries
                            logger.info(f"✅ 加载TWR时间序列数据: {len(twr_timeseries)} 条记录")
                    except Exception as e:
                        logger.error(f"加载TWR时间序列失败: {e}")
                
                st.session_state.twr_result = twr_result
                logger.info(f"✅ 加载缓存TWR结果")
        
        # 如果有交易数据，重新计算投资组合表现
        if not st.session_state.trades_df.empty:
            portfolio_data = st.session_state.benchmark_fetcher.calculate_portfolio_performance(
                st.session_state.trades_df, 100000  # 使用默认初始资金
            )
            st.session_state.portfolio_data = portfolio_data
        
        # 如果有NAV和现金流数据，但没有TWR结果，重新计算
        if (not st.session_state.nav_data.empty and 
            not st.session_state.twr_result and 
            st.session_state.twr_calculator):
            try:
                twr_result = st.session_state.twr_calculator.calculate_twr(
                    st.session_state.nav_data, 
                    st.session_state.cash_flow_data
                )
                st.session_state.twr_result = twr_result
                logger.info("✅ 重新计算TWR结果")
            except Exception as e:
                logger.warning(f"重新计算TWR失败: {e}")
        
    except Exception as e:
        logger.error(f"加载缓存数据时出错: {e}")
        # 如果加载失败，确保session state为空
        st.session_state.trades_df = pd.DataFrame()
        st.session_state.nav_data = pd.DataFrame()
        st.session_state.cash_flow_data = pd.DataFrame()
        st.session_state.benchmark_data = {}
        st.session_state.twr_result = {}

def save_data_to_csv():
    """保存数据到CSV文件"""
    import os
    
    # 创建数据目录
    data_dir = "cached_data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    try:
        # 保存交易数据
        if not st.session_state.trades_df.empty:
            trades_file = os.path.join(data_dir, "trades_data.csv")
            
            # 确保数据类型正确再保存
            trades_df_to_save = validate_trades_data_types(st.session_state.trades_df)
            
            trades_df_to_save.to_csv(trades_file, index=False)
            logger.info(f"💾 保存交易数据到 {trades_file}")
        
        # 保存NAV数据
        if not st.session_state.nav_data.empty:
            nav_file = os.path.join(data_dir, "nav_data.csv")
            st.session_state.nav_data.to_csv(nav_file, index=False)
            logger.info(f"💾 保存NAV数据到 {nav_file}")
        
        # 保存现金流数据
        if not st.session_state.cash_flow_data.empty:
            cash_flow_file = os.path.join(data_dir, "cash_flow_data.csv")
            st.session_state.cash_flow_data.to_csv(cash_flow_file, index=False)
            logger.info(f"💾 保存现金流数据到 {cash_flow_file}")
        
        # 保存基准数据
        if st.session_state.benchmark_data:
            benchmark_file = os.path.join(data_dir, "benchmark_data.csv")
            # 合并所有基准数据
            all_benchmark_data = []
            for symbol, data in st.session_state.benchmark_data.items():
                if not data.empty:
                    data_copy = data.copy()
                    data_copy['Symbol'] = symbol
                    all_benchmark_data.append(data_copy)
            
            if all_benchmark_data:
                benchmark_df = pd.concat(all_benchmark_data, ignore_index=True)
                benchmark_df.to_csv(benchmark_file, index=False)
                logger.info(f"💾 保存基准数据到 {benchmark_file}")
        
        # 保存TWR结果
        if st.session_state.twr_result:
            twr_file = os.path.join(data_dir, "twr_result.csv")
            twr_timeseries_file = os.path.join(data_dir, "twr_timeseries.csv")
            
            # 分别保存基本数据和时间序列数据
            twr_data = []
            for key, value in st.session_state.twr_result.items():
                # 跳过复杂对象，只保存基本数据类型
                if isinstance(value, (int, float, str, bool)):
                    twr_data.append({'key': key, 'value': value})
                elif key == 'twr_timeseries' and isinstance(value, pd.DataFrame) and not value.empty:
                    # 单独保存TWR时间序列数据
                    try:
                        value.to_csv(twr_timeseries_file, index=False)
                        logger.info(f"💾 保存TWR时间序列到 {twr_timeseries_file}")
                    except Exception as e:
                        logger.error(f"保存TWR时间序列失败: {e}")
            
            if twr_data:
                twr_df = pd.DataFrame(twr_data)
                twr_df.to_csv(twr_file, index=False)
                logger.info(f"💾 保存TWR结果到 {twr_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"保存数据到CSV时出错: {e}")
        return False

def get_cached_data_info():
    """获取缓存数据信息"""
    import os
    from datetime import datetime
    
    data_dir = "cached_data"
    info = {}
    
    files = {
        'trades_data.csv': '交易数据',
        'nav_data.csv': 'NAV数据',
        'cash_flow_data.csv': '现金流数据',
        'benchmark_data.csv': '基准数据',
        'twr_result.csv': 'TWR结果',
        'twr_timeseries.csv': 'TWR时间序列'
    }
    
    for filename, description in files.items():
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath):
            stat = os.stat(filepath)
            info[description] = {
                'exists': True,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            }
        else:
            info[description] = {'exists': False}
    
    return info

def main():
    """主函数"""
    init_session_state()
    
    # 主标题
    st.title("📈 IBKR 交易复盘分析平台")
    
    # 显示缓存数据加载状态
    cache_info = get_cached_data_info()
    cached_files = [name for name, info in cache_info.items() if info['exists']]
    
    if cached_files:
        st.success(f"✅ 已加载本地缓存数据: {', '.join(cached_files)}")
    else:
        st.info("ℹ️ 未找到本地缓存数据，请在侧边栏获取新数据")
    
    st.markdown("---")
    
    # 侧边栏配置
    with st.sidebar:
        st.header("⚙️ 配置")
        
        # API 配置检查
        trades_config_ok = st.session_state.data_fetcher.validate_config('trades')
        performance_config_ok = st.session_state.data_fetcher.validate_config('performance')
        
        if not trades_config_ok or not performance_config_ok:
            if not trades_config_ok:
                st.error("❌ 缺少交易数据配置")
            if not performance_config_ok:
                st.error("❌ 缺少性能数据配置")
                
            st.info("请在 config.yaml 中设置 flex_token、trades_query_id 和 performance_query_id")
            
            # 允许在界面中输入配置
            st.subheader("临时配置")
            flex_token = st.text_input("Flex Token", type="password", help="从 IBKR 账户管理中获取")
            
            col1, col2 = st.columns(2)
            with col1:
                trades_query_id = st.text_input("Trades Query ID", help="用于获取交易数据的 Query ID")
            with col2:
                performance_query_id = st.text_input("Performance Query ID", help="用于获取TWR数据的 Query ID")
            
            # 测试不同的连接
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔗 测试交易数据连接", key="test_trades_connection"):
                    if flex_token and trades_query_id:
                        with st.spinner("正在测试交易数据连接..."):
                            success, message = test_connection(flex_token, trades_query_id)
                            if success:
                                st.success(f"✅ {message}")
                                # 临时更新配置
                                st.session_state.data_fetcher.flex_token = flex_token
                                st.session_state.data_fetcher.trades_query_id = trades_query_id
                            else:
                                st.error(f"❌ {message}")
                    else:
                        st.warning("请输入 Token 和 Trades Query ID")
            
            with col2:
                if st.button("📈 测试性能数据连接", key="test_performance_connection"):
                    if flex_token and performance_query_id:
                        with st.spinner("正在测试性能数据连接..."):
                            success, message = test_connection(flex_token, performance_query_id)
                            if success:
                                st.success(f"✅ {message}")
                                # 临时更新配置
                                st.session_state.data_fetcher.flex_token = flex_token
                                st.session_state.data_fetcher.performance_query_id = performance_query_id
                            else:
                                st.error(f"❌ {message}")
                    else:
                        st.warning("请输入 Token 和 Performance Query ID")
            
            # 错误解决方案提示
            st.markdown("""
            **🔧 配置指南：**
            1. 登录 [IBKR 账户管理](https://www.interactivebrokers.com)
            2. 导航到 Reports → Flex Queries
            3. 创建两个不同的 Flex Query：
               - **Trades Query**: 包含 "Trades" 数据节点
               - **Performance Query**: 包含 "EquitySummaryByReportDateInBase", "CashTransactions", "OpenPositions" 等节点
            4. 确保两个 Query 状态都为 "Active"
            5. 生成 Flex Token（一个 Token 可用于多个 Query）
            """)
        else:
            st.success("✅ API 配置已就绪")
            
            # 显示配置状态
            if trades_config_ok:
                st.success(f"🔄 交易数据: Query ID {st.session_state.data_fetcher.trades_query_id}")
            if performance_config_ok:
                st.success(f"📈 性能数据: Query ID {st.session_state.data_fetcher.performance_query_id}")
        
        st.markdown("---")
        
        # 数据获取设置
        st.subheader("📅 数据范围")
        
        # 预设时间范围选项
        time_range = st.selectbox(
            "选择时间范围",
            ["自定义", "最近7天", "最近30天", "最近90天", "今年至今"]
        )
        
        end_date = date.today()
        if time_range == "最近7天":
            start_date = end_date - timedelta(days=7)
        elif time_range == "最近30天":
            start_date = end_date - timedelta(days=30)
        elif time_range == "最近90天":
            start_date = end_date - timedelta(days=90)
        elif time_range == "今年至今":
            start_date = date(end_date.year, 1, 1)
        else:  # 自定义
            start_date = st.date_input("开始日期", value=end_date - timedelta(days=30))
        
        if time_range == "自定义":
            end_date = st.date_input("结束日期", value=end_date)
        
        # 基准指数选择
        st.subheader("📊 基准指数")
        available_benchmarks = list(st.session_state.benchmark_fetcher.BENCHMARKS.keys())
        selected_benchmarks = st.multiselect(
            "选择基准指数",
            available_benchmarks,
            default=['SPY', 'QQQ'],
            help="选择用于比较的基准指数"
        )
        
        # 初始资金设置
        initial_capital = st.number_input(
            "初始资金 (USD)",
            value=100000,
            min_value=1000,
            step=1000,
            help="用于计算投资组合表现的初始资金"
        )
        
        # 获取所有数据的统一按钮
        st.markdown("---")
        st.subheader("🔄 数据获取")
        
        # 数据获取选项
        col1, col2 = st.columns(2)
        with col1:
            get_trades = st.checkbox("📋 获取交易数据", value=True, help="获取交易记录和投资组合表现")
            get_twr = st.checkbox("📈 获取TWR数据", value=True, help="获取NAV和现金流数据，计算时间加权收益率")
        with col2:
            get_benchmark = st.checkbox("📊 获取基准数据", value=True, help="获取基准指数数据进行对比")
            use_mock_data = st.checkbox("🧪 使用模拟数据", value=False, help="如果网络连接有问题，可以使用模拟数据进行功能演示")
        
        # 统一的数据获取按钮
        if st.button("🚀 获取所有数据", key="fetch_all_data", use_container_width=True, type="primary"):
            success_count = 0
            total_operations = sum([get_trades, get_twr, get_benchmark])
            
            if total_operations == 0:
                st.warning("请至少选择一种数据类型")
                return
            
            # 创建进度条
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 1. 获取交易数据
            if get_trades:
                status_text.text("🔄 正在获取交易数据...")
                if st.session_state.data_fetcher.validate_config('trades'):
                    try:
                        trades_df = st.session_state.data_fetcher.fetch_trades(
                            start_date=start_date.strftime("%Y-%m-%d"),
                            end_date=end_date.strftime("%Y-%m-%d")
                        )
                        if not trades_df.empty:
                            # 合并评论
                            trades_df = st.session_state.comment_manager.merge_comments_with_trades(trades_df)
                            # 验证数据类型
                            trades_df = validate_trades_data_types(trades_df)
                            st.session_state.trades_df = trades_df
                            
                            # 计算投资组合表现
                            portfolio_data = st.session_state.benchmark_fetcher.calculate_portfolio_performance(
                                trades_df, initial_capital
                            )
                            st.session_state.portfolio_data = portfolio_data
                            
                            st.success(f"✅ 交易数据：成功获取 {len(trades_df)} 条交易记录")
                            success_count += 1
                        else:
                            st.warning("⚠️ 交易数据：未获取到数据")
                    except Exception as e:
                        st.error(f"❌ 交易数据获取失败：{str(e)}")
                        logger.error(f"交易数据获取错误: {e}")
                else:
                    st.error("❌ 交易数据：请先配置交易数据 API 信息")
                
                progress_bar.progress(1 / total_operations)
            
            # 2. 获取TWR数据
            if get_twr:
                status_text.text("📈 正在获取TWR数据...")
                if st.session_state.data_fetcher.validate_config('performance'):
                    try:
                        # 获取NAV数据
                        nav_data = st.session_state.data_fetcher.fetch_nav_data(
                            start_date=start_date.strftime("%Y-%m-%d"),
                            end_date=end_date.strftime("%Y-%m-%d")
                        )
                        
                        # 获取现金流数据
                        cash_data = st.session_state.data_fetcher.fetch_cash_transactions(
                            start_date=start_date.strftime("%Y-%m-%d"),
                            end_date=end_date.strftime("%Y-%m-%d")
                        )
                        
                        nav_success = False
                        cash_success = False
                        
                        if not nav_data.empty:
                            st.session_state.nav_data = nav_data
                            st.success(f"✅ NAV数据：获取 {len(nav_data)} 条记录")
                            nav_success = True
                        else:
                            st.warning("⚠️ NAV数据：未获取到数据")
                        
                        if not cash_data.empty:
                            st.session_state.cash_flow_data = cash_data
                            st.success(f"✅ 现金流数据：获取 {len(cash_data)} 条记录")
                            cash_success = True
                        else:
                            st.info("ℹ️ 现金流数据：未获取到数据（可能期间无现金流动）")
                            cash_success = True  # 没有现金流也算成功
                        
                        # 如果有NAV数据，计算TWR
                        if nav_success:
                            try:
                                status_text.text("🧮 正在计算TWR...")
                                twr_result = st.session_state.twr_calculator.calculate_twr(
                                    nav_data, cash_data
                                )
                                st.session_state.twr_result = twr_result
                                
                                if twr_result:
                                    total_twr = twr_result.get('total_twr', 0)
                                    annualized_return = twr_result.get('annualized_return', 0)
                                    days = twr_result.get('days', 0)
                                    
                                    st.success(f"🎯 TWR计算：总TWR = {total_twr:.4f}% ({days}天), 年化收益率 = {annualized_return:.2f}%")
                                    success_count += 1
                                else:
                                    st.error("❌ TWR计算失败")
                            except Exception as e:
                                st.error(f"❌ TWR计算出错: {e}")
                                logger.error(f"TWR计算错误: {e}")
                        
                    except Exception as e:
                        st.error(f"❌ TWR数据获取失败：{str(e)}")
                        logger.error(f"TWR数据获取错误: {e}")
                else:
                    st.error("❌ TWR数据：请先配置性能数据 API 信息")
                
                progress_bar.progress(2 / total_operations if total_operations > 1 else 1.0)
            
            # 3. 获取基准数据
            if get_benchmark and selected_benchmarks:
                status_text.text("📊 正在获取基准数据...")
                try:
                    if use_mock_data:
                        # 使用模拟数据
                        st.info("📊 使用模拟数据进行演示")
                        benchmark_data = {}
                        for symbol in selected_benchmarks:
                            mock_data = st.session_state.benchmark_fetcher.generate_mock_benchmark_data(
                                symbol,
                                start_date.strftime("%Y-%m-%d"),
                                end_date.strftime("%Y-%m-%d")
                            )
                            if not mock_data.empty:
                                benchmark_data[symbol] = mock_data
                        
                        st.session_state.benchmark_data = benchmark_data
                        if benchmark_data:
                            st.success(f"✅ 基准数据：生成了 {len(benchmark_data)} 个基准指数的模拟数据: {', '.join(benchmark_data.keys())}")
                            success_count += 1
                        else:
                            st.error("❌ 基准数据：生成模拟数据失败")
                    else:
                        # 使用真实数据
                        if not st.session_state.benchmark_fetcher.test_api_connection():
                            st.error("❌ 基准数据：Financial Datasets API 连接失败")
                            st.info("💡 提示：请检查您的API密钥配置，或勾选'使用模拟数据'进行演示")
                        else:
                            benchmark_data = st.session_state.benchmark_fetcher.get_multiple_benchmarks(
                                selected_benchmarks,
                                start_date.strftime("%Y-%m-%d"),
                                end_date.strftime("%Y-%m-%d")
                            )
                            st.session_state.benchmark_data = benchmark_data
                            
                            successful_symbols = [symbol for symbol, data in benchmark_data.items() if not data.empty]
                            failed_symbols = [symbol for symbol in selected_benchmarks if symbol not in successful_symbols]
                            
                            if successful_symbols:
                                st.success(f"✅ 基准数据：成功获取 {len(successful_symbols)} 个基准指数: {', '.join(successful_symbols)}")
                                success_count += 1
                            
                            if failed_symbols:
                                st.warning(f"⚠️ 基准数据：以下指数获取失败: {', '.join(failed_symbols)}")
                            
                            if not benchmark_data:
                                st.error("❌ 基准数据：未能获取任何基准数据")
                                
                except Exception as e:
                    st.error(f"❌ 基准数据获取失败：{str(e)}")
                    logger.error(f"基准数据获取错误: {e}")
                
                progress_bar.progress(1.0)
            elif get_benchmark and not selected_benchmarks:
                st.warning("⚠️ 基准数据：请先选择基准指数")
            
            # 完成状态
            progress_bar.progress(1.0)
            status_text.text(f"✅ 数据获取完成！成功获取 {success_count}/{total_operations} 类数据")
            
            # 保存数据到CSV文件
            if success_count > 0:
                status_text.text("💾 正在保存数据到本地文件...")
                if save_data_to_csv():
                    st.success("✅ 数据已保存到本地CSV文件")
                else:
                    st.warning("⚠️ 数据保存失败，但内存中的数据仍可使用")
            
            # 清理进度显示
            import time
            time.sleep(2)
            progress_bar.empty()
            status_text.empty()
        
        # 单独的API连接测试按钮
        with st.expander("🔧 API连接测试", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔗 测试交易数据API", key="test_trades_api"):
                    if st.session_state.data_fetcher.validate_config('trades'):
                        with st.spinner("测试中..."):
                            success, message = test_connection(
                                st.session_state.data_fetcher.flex_token,
                                st.session_state.data_fetcher.trades_query_id
                            )
                            if success:
                                st.success(f"✅ {message}")
                            else:
                                st.error(f"❌ {message}")
                    else:
                        st.error("❌ 请先配置交易数据API信息")
                
                if st.button("📈 测试TWR数据API", key="test_twr_api"):
                    if st.session_state.data_fetcher.validate_config('performance'):
                        with st.spinner("测试中..."):
                            success, message = test_connection(
                                st.session_state.data_fetcher.flex_token,
                                st.session_state.data_fetcher.performance_query_id
                            )
                            if success:
                                st.success(f"✅ {message}")
                            else:
                                st.error(f"❌ {message}")
                    else:
                        st.error("❌ 请先配置性能数据API信息")
            
            with col2:
                if st.button("📊 测试基准数据API", key="test_benchmark_api"):
                    with st.spinner("测试中..."):
                        if st.session_state.benchmark_fetcher.test_api_connection():
                            st.success("✅ Financial Datasets API 连接正常")
                        else:
                            st.error("❌ Financial Datasets API 连接失败")
        
        # 数据缓存管理
        with st.expander("💾 数据缓存管理", expanded=False):
            st.write("**本地缓存状态:**")
            
            cache_info = get_cached_data_info()
            
            for data_type, info in cache_info.items():
                if info['exists']:
                    file_size = info['size'] / 1024  # 转换为KB
                    st.write(f"✅ **{data_type}**: {file_size:.1f} KB (更新于 {info['modified']})")
                else:
                    st.write(f"❌ **{data_type}**: 无缓存文件")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 重新加载缓存", key="reload_cache"):
                    with st.spinner("正在重新加载缓存数据..."):
                        load_cached_data()
                        st.success("✅ 缓存数据重新加载完成")
                        st.rerun()
            
            with col2:
                if st.button("🗑️ 清除缓存", key="clear_cache"):
                    import os
                    import shutil
                    
                    data_dir = "cached_data"
                    if os.path.exists(data_dir):
                        try:
                            shutil.rmtree(data_dir)
                            # 清空session state
                            st.session_state.trades_df = pd.DataFrame()
                            st.session_state.nav_data = pd.DataFrame()
                            st.session_state.cash_flow_data = pd.DataFrame()
                            st.session_state.benchmark_data = {}
                            st.session_state.twr_result = {}
                            st.session_state.portfolio_data = pd.DataFrame()
                            
                            st.success("✅ 缓存已清除")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 清除缓存失败: {e}")
                    else:
                        st.info("ℹ️ 没有缓存文件需要清除")
            
            # 手动保存当前数据
            if st.button("💾 保存当前数据", key="save_current_data", use_container_width=True):
                if save_data_to_csv():
                    st.success("✅ 当前数据已保存到CSV文件")
                else:
                    st.error("❌ 保存失败")
        
        st.markdown("---")
        
        # 数据统计
        if not st.session_state.trades_df.empty:
            st.subheader("📊 数据统计")
            df = st.session_state.trades_df
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("交易笔数", len(df))
                st.metric("交易标的", df['symbol'].nunique())
            with col2:
                total_volume = df['proceeds'].abs().sum()
                st.metric("总交易额", f"${total_volume:,.2f}")
                commented_trades = len(df[df['comment'] != ''])
                st.metric("已评论", commented_trades)
            
            # TWR数据统计
            if st.session_state.twr_result:
                st.markdown("**TWR分析:**")
                twr_result = st.session_state.twr_result
                total_twr = twr_result.get('total_twr', 0)
                annualized_return = twr_result.get('annualized_return', 0)
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("总TWR", f"{total_twr:.2f}%")
                with col2:
                    st.metric("年化收益率", f"{annualized_return:.2f}%")
            
            # 基准数据统计
            if st.session_state.benchmark_data:
                st.markdown("**基准指数数据:**")
                for symbol, data in st.session_state.benchmark_data.items():
                    if not data.empty:
                        latest_return = data['Cumulative_Return'].iloc[-1]
                        st.metric(f"{symbol}", f"{latest_return:+.2f}%")
    
    # 主内容区域
    if st.session_state.trades_df.empty:
        # 检查是否有其他类型的缓存数据
        has_nav_data = not st.session_state.nav_data.empty
        has_benchmark_data = bool(st.session_state.benchmark_data)
        has_twr_result = bool(st.session_state.twr_result)
        
        if has_nav_data or has_benchmark_data or has_twr_result:
            st.info("📊 检测到部分缓存数据，但缺少交易数据。请在侧边栏获取完整数据或仅查看可用的分析。")
        else:
            st.info("👈 请在侧边栏配置 API 并获取数据，或者应用会自动加载本地缓存数据")
        
        # 显示使用说明
        st.subheader("📖 使用说明")
        
        with st.expander("1. 配置 IBKR Flex API", expanded=True):
            st.markdown("""
            1. 登录您的 IBKR 账户管理
            2. 进入 "Reports" → "Flex Queries"
            3. 创建新的 Flex Query，选择 "Trades" 数据类型
            4. 生成 Token 并记录 Query ID
            5. 在 config.yaml 中配置这些信息
            """)
        
        with st.expander("2. 功能特性"):
            st.markdown("""
            - 📊 **自动数据获取**: 从 IBKR Flex API 获取历史交易
            - 📝 **交易评论**: 为每笔交易添加复盘评论
            - 📈 **可视化分析**: 多种图表展示交易表现
            - 💾 **数据持久化**: 自动保存数据到本地CSV文件
            - 🔍 **数据筛选**: 支持多维度数据过滤和搜索
            - 🚀 **快速启动**: 启动时自动加载缓存数据
            """)
        
        with st.expander("3. 数据缓存功能"):
            st.markdown("""
            - 📁 **自动缓存**: 获取的数据自动保存到 `cached_data/` 目录
            - 🔄 **快速加载**: 下次启动时自动加载缓存数据
            - 💾 **离线使用**: 有缓存数据时可离线分析
            - 🗑️ **缓存管理**: 可手动清除或重新加载缓存
            """)
        
        # 如果有部分数据，仍然显示标签页让用户查看
        if not (has_nav_data or has_benchmark_data or has_twr_result):
            return
    
    # 创建标签页
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 交易记录", "📈 图表分析", "🆚 TWR & 基准对比", "💬 评论管理", "📊 统计报告"])
    
    with tab1:
        show_trades_table()
    
    with tab2:
        show_charts()
    
    with tab3:
        show_twr_benchmark_analysis()

    with tab4:
        show_comment_management()

    with tab5:
        show_statistics()

def show_trades_table():
    """显示交易记录表格"""
    st.subheader("📋 交易记录")
    
    df = st.session_state.trades_df.copy()
    
    # 确保数据类型正确（防止从CSV加载时类型错误）
    df = validate_trades_data_types(df)
    
    # 过滤控件
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        symbols = ['全部'] + sorted(df['symbol'].unique().tolist())
        selected_symbol = st.selectbox("标的筛选", symbols)
    
    with col2:
        sides = ['全部', 'BUY', 'SELL']
        selected_side = st.selectbox("买卖方向", sides)
    
    with col3:
        categories = ['全部', 'Good', 'Bad', 'Neutral']
        selected_category = st.selectbox("评论分类", categories)
    
    with col4:
        min_price = st.number_input("最低价格", value=0.0, step=0.01)
    
    with col5:
        search_text = st.text_input("搜索评论", placeholder="输入关键词...")
    
    # 应用过滤
    if selected_symbol != '全部':
        df = df[df['symbol'] == selected_symbol]
    
    if selected_side != '全部':
        df = df[df['side'] == selected_side]
    
    if selected_category != '全部':
        df = df[df['comment_category'] == selected_category]
    
    if min_price > 0:
        df = df[df['price'] >= min_price]
    
    if search_text:
        df = df[df['comment'].str.contains(search_text, case=False, na=False)]
    
    st.info(f"显示 {len(df)} 条记录（共 {len(st.session_state.trades_df)} 条）")
    
    # 可编辑的数据表格
    if not df.empty:
        # 重新排列列的顺序，让评论列更明显
        display_columns = ['datetime', 'symbol', 'side', 'quantity', 'price', 'proceeds', 'commission', 'comment', 'comment_category']
        display_df = df[display_columns].copy()
        
        # 格式化显示
        display_df['datetime'] = display_df['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
        display_df['price'] = display_df['price'].round(4)
        display_df['proceeds'] = display_df['proceeds'].round(2)
        display_df['commission'] = display_df['commission'].round(2)
        
        # 使用 data_editor 来允许编辑评论
        edited_df = st.data_editor(
            display_df,
            column_config={
                "datetime": "时间",
                "symbol": "标的",
                "side": "方向",
                "quantity": "数量",
                "price": "价格",
                "proceeds": "金额",
                "commission": "手续费",
                "comment": st.column_config.TextColumn(
                    "评论",
                    help="添加您的交易评论",
                    max_chars=500,
                    width="medium"
                ),
                "comment_category": st.column_config.SelectboxColumn(
                    "评论分类",
                    help="选择评论分类",
                    options=["Good", "Bad", "Neutral"],
                    width="small"
                )
            },
            disabled=["datetime", "symbol", "side", "quantity", "price", "proceeds", "commission"],
            hide_index=True,
            use_container_width=True,
            height=400
        )
        
        # 保存评论按钮
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("💾 保存更改", key="save_trade_changes", use_container_width=True):
                # 比较原始数据和编辑后的数据
                original_comments = dict(zip(df['trade_id'], df['comment']))
                edited_comments = dict(zip(df['trade_id'], edited_df['comment']))
                
                original_categories = dict(zip(df['trade_id'], df['comment_category']))
                edited_categories = dict(zip(df['trade_id'], edited_df['comment_category']))
                
                comment_updates = {}
                category_updates = {}
                
                for trade_id in original_comments:
                    if original_comments[trade_id] != edited_comments[trade_id]:
                        comment_updates[trade_id] = edited_comments[trade_id]
                    if original_categories[trade_id] != edited_categories[trade_id]:
                        category_updates[trade_id] = edited_categories[trade_id]
                
                total_updates = 0
                
                if comment_updates:
                    if st.session_state.comment_manager.bulk_update_comments(comment_updates):
                        total_updates += len(comment_updates)
                    else:
                        st.error("❌ 评论保存失败")
                        
                if category_updates:
                    if st.session_state.comment_manager.bulk_update_categories(category_updates):
                        total_updates += len(category_updates)
                    else:
                        st.error("❌ 分类保存失败")
                
                if total_updates > 0:
                    st.success(f"✅ 成功更新 {len(comment_updates)} 条评论和 {len(category_updates)} 条分类")
                    # 重新加载数据
                    st.session_state.trades_df = st.session_state.comment_manager.merge_comments_with_trades(
                        st.session_state.trades_df
                    )
                    st.rerun()
                else:
                    st.info("没有需要保存的更改")
        
        with col2:
            # 导出数据
            csv_data = df.to_csv(index=False)
            st.download_button(
                "📥 导出 CSV",
                data=csv_data,
                file_name=f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )

def show_charts():
    """显示图表分析"""
    st.subheader("📈 图表分析")
    
    df = st.session_state.trades_df
    chart_gen = st.session_state.chart_generator
    
    # 图表选择
    chart_type = st.selectbox(
        "选择图表类型",
        ["交易时间线", "盈亏分析", "交易量分析", "标的分布", "评论分析"]
    )
    
    if chart_type == "交易时间线":
        # 检查是否有TWR数据
        if st.session_state.twr_result:
            # 使用基于TWR曲线的交易时间线
            fig = chart_gen.create_twr_with_trades_timeline(st.session_state.twr_result, df)
            st.plotly_chart(fig, use_container_width=True)

            st.info("💡 提示：交易标记显示在TWR曲线上，可以直观看到每笔交易对投资组合表现的影响")
        else:
            # 如果没有TWR数据，使用传统的交易时间线
            fig = chart_gen.create_trade_timeline(df)
            st.plotly_chart(fig, use_container_width=True)

            st.warning("⚠️ 未获取TWR数据，显示传统交易时间线。建议在侧边栏获取TWR数据以查看更准确的分析。")
            st.info("💡 提示：点击图例可以显示/隐藏特定标的，鼠标悬停查看详细信息")
    
    elif chart_type == "盈亏分析":
        fig = chart_gen.create_pnl_chart(df)
        st.plotly_chart(fig, use_container_width=True)
        
        st.warning("⚠️ 注意：这是简化的盈亏计算，实际盈亏请以券商结算为准")
    
    elif chart_type == "交易量分析":
        fig = chart_gen.create_trading_volume_chart(df)
        st.plotly_chart(fig, use_container_width=True)
    
    elif chart_type == "标的分布":
        fig = chart_gen.create_symbol_distribution(df)
        st.plotly_chart(fig, use_container_width=True)
    
    elif chart_type == "评论分析":
        fig = chart_gen.create_comment_analysis(df)
        st.plotly_chart(fig, use_container_width=True)

def show_comment_management():
    """显示评论管理"""
    st.subheader("💬 评论管理")
    
    comment_mgr = st.session_state.comment_manager
    
    # 评论统计
    stats = comment_mgr.get_comment_statistics()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总评论数", stats['total_comments'])
    with col2:
        st.metric("评论分类", len(stats['categories']))
    with col3:
        if stats['latest_update']:
            st.metric("最近更新", stats['latest_update'][:10])
    
    st.markdown("---")
    
    # 评论分类统计
    if stats['categories']:
        st.subheader("📊 评论分类统计")
        categories_df = pd.DataFrame([
            {'分类': k, '数量': v} for k, v in stats['categories'].items()
        ])
        st.dataframe(categories_df, use_container_width=True)
    
    # 评论导出
    st.subheader("📤 导出评论")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("导出评论为 CSV", key="export_comments_csv"):
            csv_data = comment_mgr.export_comments_csv()
            if csv_data:
                st.download_button(
                    "📥 下载 CSV 文件",
                    data=csv_data,
                    file_name=f"comments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("没有评论数据可导出")
    
    with col2:
        if st.button("备份评论数据", key="backup_comments"):
            if comment_mgr.save_comments():
                st.success("✅ 评论数据已备份")
            else:
                st.error("❌ 备份失败")

def show_statistics():
    """显示统计报告"""
    st.subheader("📊 统计报告")
    
    df = st.session_state.trades_df
    
    if df.empty:
        st.warning("暂无数据")
        return
    
    # 基础统计
    st.subheader("📈 基础指标")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("总交易笔数", len(df))
        st.metric("买入笔数", len(df[df['side'] == 'BUY']))
    
    with col2:
        st.metric("卖出笔数", len(df[df['side'] == 'SELL']))
        st.metric("交易标的数", df['symbol'].nunique())
    
    with col3:
        total_commission = df['commission'].sum()
        st.metric("总手续费", f"${total_commission:.2f}")
        avg_commission = df['commission'].mean()
        st.metric("平均手续费", f"${avg_commission:.2f}")
    
    with col4:
        total_volume = df['proceeds'].abs().sum()
        st.metric("总交易额", f"${total_volume:,.2f}")
        avg_volume = df['proceeds'].abs().mean()
        st.metric("平均交易额", f"${avg_volume:.2f}")
    
    st.markdown("---")
    
    # 按标的统计
    st.subheader("📋 按标的统计")
    
    symbol_stats = df.groupby('symbol').agg({
        'trade_id': 'count',
        'quantity': 'sum',
        'proceeds': lambda x: abs(x).sum(),
        'commission': 'sum'
    }).rename(columns={
        'trade_id': '交易次数',
        'quantity': '总数量',
        'proceeds': '总金额',
        'commission': '总手续费'
    }).round(2)
    
    symbol_stats = symbol_stats.sort_values('总金额', ascending=False)
    st.dataframe(symbol_stats, use_container_width=True)
    
    st.markdown("---")
    
    # 按时间统计
    st.subheader("📅 按时间统计")
    
    # 按月统计
    monthly_stats = df.groupby(df['datetime'].dt.to_period('M')).agg({
        'trade_id': 'count',
        'proceeds': lambda x: abs(x).sum(),
        'commission': 'sum'
    }).rename(columns={
        'trade_id': '交易次数',
        'proceeds': '交易金额',
        'commission': '手续费'
    }).round(2)
    
    st.subheader("月度统计")
    st.dataframe(monthly_stats, use_container_width=True)



def show_twr_benchmark_analysis():
    """显示TWR分析与基准对比的合并页面"""
    st.subheader("🆚 TWR分析 & 基准对比")

    # 检查数据可用性
    has_twr_data = bool(st.session_state.twr_result)
    has_benchmark_data = bool(st.session_state.benchmark_data)

    if not has_twr_data and not has_benchmark_data:
        st.info("请先在侧边栏获取 TWR 数据和基准指数数据")

        # 显示使用指南
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📖 TWR 分析说明")
            with st.expander("什么是时间加权收益率(TWR)?", expanded=True):
                st.markdown("""
                **时间加权收益率(Time-Weighted Return, TWR)**是一种投资绩效评估方法：

                **核心特点:**
                - 剔除现金流（入金/出金）的影响
                - 真实反映投资策略本身的表现
                - 适合评估投资管理能力

                **计算原理:**
                - 将投资期间按现金流事件分割为多个子区间
                - 计算每个子区间的收益率
                - 将各子区间收益率几何连乘

                **数据需求:**
                - 每日净资产价值(NAV)
                - 现金流记录(入金/出金)
                - 持仓快照(可选)
                """)

        with col2:
            st.subheader("📊 基准对比说明")
            with st.expander("如何进行基准对比分析", expanded=True):
                st.markdown("""
                1. **获取交易数据**: 在侧边栏点击"🔄 获取交易数据"
                2. **获取TWR数据**: 点击"📈 获取 TWR 数据"
                3. **选择基准指数**: 选择如 SPY、QQQ 等基准指数
                4. **获取基准数据**: 点击"📈 获取基准数据"

                **支持的基准指数:**
                - **SPY**: S&P 500 ETF
                - **QQQ**: 纳斯达克 100 ETF
                - **VTI**: 全市场 ETF
                - **IWM**: 小盘股 ETF
                """)

        return

    # 如果有TWR数据，显示核心指标
    if has_twr_data:
        twr_result = st.session_state.twr_result

        # 核心指标展示
        st.subheader("📊 核心绩效指标")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "总时间加权收益率",
                f"{twr_result.get('total_twr', 0):.2%}",
                help="整个投资期间的时间加权收益率"
            )

        with col2:
            st.metric(
                "年化收益率",
                f"{twr_result.get('annualized_return', 0):.2%}",
                help="基于投资天数计算的年化收益率"
            )

        with col3:
            st.metric(
                "年化波动率",
                f"{twr_result.get('volatility', 0):.2%}",
                help="收益率的年化标准差"
            )

        with col4:
            st.metric(
                "夏普比率",
                f"{twr_result.get('sharpe_ratio', 0):.3f}",
                help="风险调整后的收益率指标"
            )

        # 最大回撤信息
        if twr_result.get('max_drawdown', 0) > 0:
            st.warning(f"📉 最大回撤: {twr_result['max_drawdown']:.2%}")
            if twr_result.get('max_drawdown_start') and twr_result.get('max_drawdown_end'):
                st.info(f"回撤期间: {twr_result['max_drawdown_start'].strftime('%Y-%m-%d')} 至 {twr_result['max_drawdown_end'].strftime('%Y-%m-%d')}")

        st.markdown("---")

    # 主要对比图表
    if has_twr_data and has_benchmark_data:
        st.subheader("📈 TWR vs 基准指数收益率对比")
        chart_gen = st.session_state.chart_generator

        # 使用新的TWR基准对比图
        fig_comparison = chart_gen.create_twr_benchmark_comparison(
            st.session_state.twr_result,
            st.session_state.benchmark_data
        )
        st.plotly_chart(fig_comparison, use_container_width=True)

    elif has_twr_data:
        # 只有TWR数据时，显示TWR时间序列
        st.subheader("📈 TWR 时间序列分析")
        chart_gen = st.session_state.chart_generator
        fig_twr = chart_gen.create_twr_chart(st.session_state.twr_result)
        st.plotly_chart(fig_twr, use_container_width=True)

        st.info("💡 获取基准指数数据以查看对比分析")

    elif has_benchmark_data:
        # 只有基准数据时，提示获取TWR数据
        st.info("💡 获取 TWR 数据以查看准确的投资组合表现对比")

    # 表现指标对比
    if has_twr_data and has_benchmark_data:
        st.subheader("📊 表现指标对比")

        twr_result = st.session_state.twr_result
        benchmark_fetcher = st.session_state.benchmark_fetcher

        # 计算基准指标
        benchmark_metrics = {}
        for symbol, data in st.session_state.benchmark_data.items():
            if not data.empty:
                benchmark_metrics[symbol] = benchmark_fetcher.calculate_performance_metrics(
                    data['Cumulative_Return']
                )

        # 显示指标对比表格
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**投资组合表现 (TWR):**")
            twr_metrics_df = pd.DataFrame([{
                '指标': '总收益率 (%)',
                '值': f"{twr_result.get('total_twr', 0) * 100:.2f}"
            }, {
                '指标': '年化收益率 (%)',
                '值': f"{twr_result.get('annualized_return', 0) * 100:.2f}"
            }, {
                '指标': '年化波动率 (%)',
                '值': f"{twr_result.get('volatility', 0) * 100:.2f}"
            }, {
                '指标': '最大回撤 (%)',
                '值': f"{twr_result.get('max_drawdown', 0) * 100:.2f}"
            }, {
                '指标': '夏普比率',
                '值': f"{twr_result.get('sharpe_ratio', 0):.3f}"
            }])
            st.dataframe(twr_metrics_df, hide_index=True, use_container_width=True)

        with col2:
            st.markdown("**基准指数表现:**")
            benchmark_summary = []
            for symbol, metrics in benchmark_metrics.items():
                benchmark_summary.append({
                    '指数': symbol,
                    '总收益率 (%)': f"{metrics.get('total_return', 0):.2f}",
                    '年化收益率 (%)': f"{metrics.get('annualized_return', 0):.2f}",
                    '波动率 (%)': f"{metrics.get('volatility', 0):.2f}",
                    '最大回撤 (%)': f"{metrics.get('max_drawdown', 0):.2f}",
                    '夏普比率': f"{metrics.get('sharpe_ratio', 0):.3f}"
                })

            if benchmark_summary:
                benchmark_df = pd.DataFrame(benchmark_summary)
                st.dataframe(benchmark_df, hide_index=True, use_container_width=True)

    # TWR详细分析部分
    if has_twr_data:
        twr_result = st.session_state.twr_result
        chart_gen = st.session_state.chart_generator

        st.markdown("---")

        # 指标仪表板
        st.subheader("🎛️ 绩效指标仪表板")
        fig_dashboard = chart_gen.create_twr_metrics_dashboard(twr_result)
        st.plotly_chart(fig_dashboard, use_container_width=True)

        # 现金流分析
        external_cash_flows = twr_result.get('external_cash_flows')
        if external_cash_flows is not None and not external_cash_flows.empty:
            st.subheader("💰 现金流影响分析")
            fig_cf = chart_gen.create_cash_flow_impact_chart(twr_result)
            st.plotly_chart(fig_cf, use_container_width=True)

            # 现金流详情表
            with st.expander("现金流详情", expanded=False):
                cf_df = twr_result['external_cash_flows'].copy()
                cf_df['date'] = cf_df['date'].dt.strftime('%Y-%m-%d')

                # 转换枚举类型为字符串，避免Arrow序列化错误
                if 'description' in cf_df.columns:
                    cf_df['description'] = cf_df['description'].astype(str)
                if 'type' in cf_df.columns:
                    cf_df['type'] = cf_df['type'].astype(str)

                cf_df = cf_df.rename(columns={
                    'date': '日期',
                    'type': '类型',
                    'amount': '金额',
                    'description': '描述'
                })
                st.dataframe(cf_df, use_container_width=True, hide_index=True)

    # 相关性分析（如果有基准数据）
    if has_twr_data and has_benchmark_data and len(st.session_state.benchmark_data) == 1:
        st.subheader("📊 相关性分析")
        benchmark_symbol = list(st.session_state.benchmark_data.keys())[0]
        benchmark_data = st.session_state.benchmark_data[benchmark_symbol]

        # 需要将TWR数据转换为适合相关性分析的格式
        if 'nav_data' in twr_result and not twr_result['nav_data'].empty:
            nav_data = twr_result['nav_data'].copy()
            initial_nav = nav_data['nav'].iloc[0]
            nav_data['portfolio_return'] = (nav_data['nav'] / initial_nav - 1) * 100
            nav_data = nav_data.rename(columns={'date': 'datetime'})

            fig_corr = chart_gen.create_rolling_correlation(nav_data, benchmark_data)
            st.plotly_chart(fig_corr, use_container_width=True)

            st.info("💡 相关性说明：\n- 接近 1：高度正相关\n- 接近 0：无相关性\n- 接近 -1：高度负相关")

    # 基准指数信息
    if has_benchmark_data:
        st.subheader("ℹ️ 基准指数信息")
        benchmark_fetcher = st.session_state.benchmark_fetcher
        for symbol in st.session_state.benchmark_data.keys():
            info = benchmark_fetcher.get_benchmark_info(symbol)
            with st.expander(f"{symbol} - {info['name']}"):
                st.write(f"**货币:** {info['currency']}")
                st.write(f"**交易所:** {info['exchange']}")
                if info['description']:
                    st.write(f"**描述:** {info['description']}")

def show_twr_analysis():
    """显示TWR分析页面"""
    st.subheader("⏱️ 时间加权收益率(TWR)分析")
    
    # 检查是否有TWR数据
    if not st.session_state.twr_result:
        st.info("请先在侧边栏获取 TWR 数据")
        
        st.subheader("📖 TWR 分析说明")
        with st.expander("什么是时间加权收益率(TWR)?", expanded=True):
            st.markdown("""
            **时间加权收益率(Time-Weighted Return, TWR)**是一种投资绩效评估方法：
            
            **核心特点:**
            - 剔除现金流（入金/出金）的影响
            - 真实反映投资策略本身的表现
            - 适合评估投资管理能力
            
            **计算原理:**
            - 将投资期间按现金流事件分割为多个子区间
            - 计算每个子区间的收益率
            - 将各子区间收益率几何连乘
            
            **与MWR的区别:**
            - TWR：评估策略表现，排除入金时机影响
            - MWR：评估整体决策，包含入金时机
            
            **数据需求:**
            - 每日净资产价值(NAV)
            - 现金流记录(入金/出金)
            - 持仓快照(可选)
            """)
        
        with st.expander("如何获取TWR数据"):
            st.markdown("""
            1. **配置Flex Query**: 确保您的Flex Query包含以下数据：
               - Net Asset Value (NAV)
               - Cash Transactions  
               - Positions (可选)
               
            2. **点击获取**: 在侧边栏点击"📈 获取 TWR 数据"按钮
            
            3. **自动计算**: 系统将自动计算TWR及相关指标
            """)
        
        return
    
    twr_result = st.session_state.twr_result
    chart_gen = st.session_state.chart_generator
    
    # 核心指标展示
    st.subheader("📊 核心绩效指标")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "总时间加权收益率",
            f"{twr_result.get('total_twr', 0):.2%}",
            help="整个投资期间的时间加权收益率"
        )
    
    with col2:
        st.metric(
            "年化收益率", 
            f"{twr_result.get('annualized_return', 0):.2%}",
            help="基于投资天数计算的年化收益率"
        )
    
    with col3:
        st.metric(
            "年化波动率",
            f"{twr_result.get('volatility', 0):.2%}",
            help="收益率的年化标准差"
        )
    
    with col4:
        st.metric(
            "夏普比率",
            f"{twr_result.get('sharpe_ratio', 0):.3f}",
            help="风险调整后的收益率指标"
        )
    
    # 最大回撤信息
    if twr_result.get('max_drawdown', 0) > 0:
        st.warning(f"📉 最大回撤: {twr_result['max_drawdown']:.2%}")
        if twr_result.get('max_drawdown_start') and twr_result.get('max_drawdown_end'):
            st.info(f"回撤期间: {twr_result['max_drawdown_start'].strftime('%Y-%m-%d')} 至 {twr_result['max_drawdown_end'].strftime('%Y-%m-%d')}")
    
    st.markdown("---")
    
    # TWR主图表
    st.subheader("📈 TWR 时间序列分析")
    fig_twr = chart_gen.create_twr_chart(twr_result)
    st.plotly_chart(fig_twr, use_container_width=True)
    
    # 指标仪表板
    st.subheader("🎛️ 绩效指标仪表板")
    fig_dashboard = chart_gen.create_twr_metrics_dashboard(twr_result)
    st.plotly_chart(fig_dashboard, use_container_width=True)
    
    # 现金流分析
    external_cash_flows = twr_result.get('external_cash_flows')
    if external_cash_flows is not None and not external_cash_flows.empty:
        st.subheader("💰 现金流影响分析")
        fig_cf = chart_gen.create_cash_flow_impact_chart(twr_result)
        st.plotly_chart(fig_cf, use_container_width=True)
        
        # 现金流详情表
        with st.expander("现金流详情", expanded=False):
            cf_df = twr_result['external_cash_flows'].copy()
            cf_df['date'] = cf_df['date'].dt.strftime('%Y-%m-%d')

            # 转换枚举类型为字符串，避免Arrow序列化错误
            if 'description' in cf_df.columns:
                cf_df['description'] = cf_df['description'].astype(str)
            if 'type' in cf_df.columns:
                cf_df['type'] = cf_df['type'].astype(str)

            cf_df = cf_df.rename(columns={
                'date': '日期',
                'amount': '金额',
                'type': '类型',
                'description': '描述'
            })
            st.dataframe(cf_df, use_container_width=True, hide_index=True)
    
    # 周期性收益率
    st.subheader("📅 周期性收益率分析")
    
    frequency_options = {
        'M': '月度',
        'Q': '季度',
        'Y': '年度'
    }
    
    selected_freq = st.selectbox(
        "选择分析频率",
        options=list(frequency_options.keys()),
        format_func=lambda x: frequency_options[x]
    )
    
    if st.button(f"计算{frequency_options[selected_freq]}TWR", key="calc_periodic_twr"):
        with st.spinner(f"正在计算{frequency_options[selected_freq]}TWR..."):
            periodic_twr = st.session_state.twr_calculator.calculate_periodic_twr(
                st.session_state.nav_data,
                st.session_state.cash_flow_data,
                frequency=selected_freq
            )
            
            if not periodic_twr.empty:
                # 周期性TWR图表
                fig_periodic = chart_gen.create_periodic_twr_chart(periodic_twr, selected_freq)
                st.plotly_chart(fig_periodic, use_container_width=True)
                
                # 周期性TWR表格
                with st.expander(f"{frequency_options[selected_freq]}TWR详情"):
                    display_df = periodic_twr.copy()
                    display_df['period'] = display_df['period'].dt.strftime('%Y-%m' if selected_freq == 'M' else '%Y')
                    display_df['return'] = display_df['return'].apply(lambda x: f"{x:.2%}")
                    display_df['start_nav'] = display_df['start_nav'].round(2)
                    display_df['end_nav'] = display_df['end_nav'].round(2)
                    display_df['cash_flows'] = display_df['cash_flows'].round(2)
                    
                    display_df = display_df.rename(columns={
                        'period': '时期',
                        'start_nav': '期初NAV',
                        'end_nav': '期末NAV',
                        'cash_flows': '现金流',
                        'return': '收益率'
                    })
                    
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.warning(f"无法计算{frequency_options[selected_freq]}TWR，数据不足")
    
    # 详细计算信息
    with st.expander("🔍 计算详情", expanded=False):
        st.write("**计算参数:**")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"- 分析期间: {twr_result['start_date']} 至 {twr_result['end_date']}")
            st.write(f"- 总天数: {twr_result['total_days']} 天")
            st.write(f"- 计算区间数: {twr_result['period_count']} 个")
        
        with col2:
            st.write(f"- NAV数据点: {len(twr_result['nav_data'])} 个")
            st.write(f"- 现金流事件: {len(twr_result['external_cash_flows'])} 个")
            st.write(f"- 风险无风险利率: 2% (年化)")
        
        if twr_result.get('period_returns'):
            st.write("**分期收益率:**")
            for i, ret in enumerate(twr_result['period_returns']):
                st.write(f"- 第{i+1}期: {ret:.4%}")
        
        # 添加TWR时间序列调试信息
        if 'twr_timeseries' in twr_result and not twr_result['twr_timeseries'].empty:
            st.write("**TWR时间序列调试:**")
            twr_ts = twr_result['twr_timeseries']
            
            # 显示前几天和后几天的数据
            st.write("前5天数据:")
            debug_cols = ['date', 'nav', 'adjusted_nav', 'daily_return', 'twr_return', 'cash_flow']
            available_cols = [col for col in debug_cols if col in twr_ts.columns]
            if len(twr_ts) >= 5:
                st.dataframe(twr_ts[available_cols].head(), hide_index=True)
            
            st.write("后5天数据:")
            if len(twr_ts) >= 5:
                st.dataframe(twr_ts[available_cols].tail(), hide_index=True)
            
            # 检查异常波动
            if 'daily_return' in twr_ts.columns:
                large_changes = twr_ts[abs(twr_ts['daily_return']) > 0.1]  # 超过10%的日收益率
                if not large_changes.empty:
                    st.warning(f"⚠️ 发现 {len(large_changes)} 天的日收益率超过10%，可能存在数据异常:")
                    st.dataframe(large_changes[available_cols], hide_index=True)

        # 数据验证和异常检测
        with st.expander("🔍 数据验证和异常检测", expanded=False):
            st.write("**NAV数据验证:**")
            
            # NAV数据统计
            nav_data = twr_result.get('nav_data', pd.DataFrame())
            if not nav_data.empty:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("NAV数据点", len(nav_data))
                    st.metric("最小NAV", f"${nav_data['nav'].min():,.2f}")
                with col2:
                    st.metric("最大NAV", f"${nav_data['nav'].max():,.2f}")
                    st.metric("NAV变化范围", f"{((nav_data['nav'].max() / nav_data['nav'].min() - 1) * 100):.2f}%")
                with col3:
                    st.metric("平均NAV", f"${nav_data['nav'].mean():,.2f}")
                    st.metric("NAV标准差", f"${nav_data['nav'].std():,.2f}")
                
                # 检测异常波动
                st.write("**异常波动检测:**")
                
                # 计算日收益率
                nav_data_sorted = nav_data.sort_values('date')
                daily_returns = nav_data_sorted['nav'].pct_change().dropna()
                
                # 找出异常波动（>10%的单日变化）
                extreme_returns = daily_returns[abs(daily_returns) > 0.1]
                
                if not extreme_returns.empty:
                    st.warning(f"⚠️ 发现 {len(extreme_returns)} 个异常波动日（单日变化>10%）:")
                    
                    for date, return_rate in extreme_returns.items():
                        date_idx = nav_data_sorted[nav_data_sorted['date'] == date].index[0]
                        if date_idx > 0:
                            prev_nav = nav_data_sorted.iloc[date_idx-1]['nav']
                            curr_nav = nav_data_sorted.iloc[date_idx]['nav']
                            nav_change = curr_nav - prev_nav
                            
                            # 检查是否有现金流
                            cf_on_date = twr_result.get('external_cash_flows', pd.DataFrame())
                            if not cf_on_date.empty:
                                cf_on_date = cf_on_date[cf_on_date['date'].dt.date == date.date()]
                                cf_amount = cf_on_date['amount'].sum() if not cf_on_date.empty else 0
                            else:
                                cf_amount = 0
                            
                            st.write(f"📅 **{date.strftime('%Y-%m-%d')}**: "
                                   f"NAV从 ${prev_nav:,.2f} 变为 ${curr_nav:,.2f} "
                                   f"(变化: ${nav_change:,.2f}, {return_rate*100:.2f}%)")
                            
                            if cf_amount != 0:
                                st.write(f"   💰 当日现金流: ${cf_amount:,.2f}")
                            else:
                                st.write(f"   ⚠️ 当日无现金流，可能是：")
                                st.write(f"   - 投资收益/损失")
                                st.write(f"   - 数据错误")
                                st.write(f"   - 遗漏的现金流记录")
                else:
                    st.success("✅ 未发现异常波动，NAV数据看起来正常")
                
                # 显示最大的几个单日变化
                st.write("**最大单日变化Top 5:**")
                top_changes = daily_returns.abs().nlargest(5)
                for date, abs_return in top_changes.items():
                    actual_return = daily_returns[date]
                    date_idx = nav_data_sorted[nav_data_sorted['date'] == date].index[0]
                    if date_idx > 0:
                        prev_nav = nav_data_sorted.iloc[date_idx-1]['nav']
                        curr_nav = nav_data_sorted.iloc[date_idx]['nav']
                        st.write(f"📅 {date.strftime('%Y-%m-%d')}: "
                               f"{actual_return*100:+.2f}% "
                               f"(${prev_nav:,.2f} → ${curr_nav:,.2f})")
            else:
                st.error("❌ 没有NAV数据可供验证")
            
            # 现金流数据验证
            st.write("**现金流数据验证:**")
            external_cf = twr_result.get('external_cash_flows', pd.DataFrame())
            if not external_cf.empty:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("现金流事件", len(external_cf))
                    st.metric("现金流入总额", f"${external_cf[external_cf['amount'] > 0]['amount'].sum():,.2f}")
                with col2:
                    st.metric("现金流出总额", f"${abs(external_cf[external_cf['amount'] < 0]['amount'].sum()):,.2f}")
                    st.metric("净现金流", f"${external_cf['amount'].sum():,.2f}")
                
                # 显示现金流明细
                st.write("**现金流明细:**")
                for _, cf in external_cf.iterrows():
                    st.write(f"📅 {cf['date'].strftime('%Y-%m-%d')}: "
                           f"${cf['amount']:+,.2f} ({cf['type']})")
            else:
                st.info("ℹ️ 没有检测到外部现金流")

if __name__ == "__main__":
    main() 