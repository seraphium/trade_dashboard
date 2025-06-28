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

def main():
    """主函数"""
    init_session_state()
    
    # 主标题
    st.title("📈 IBKR 交易复盘分析平台")
    st.markdown("---")
    
    # 侧边栏配置
    with st.sidebar:
        st.header("⚙️ 配置")
        
        # API 配置检查
        if not st.session_state.data_fetcher.validate_config():
            st.error("❌ 请先配置 IBKR API")
            st.info("请在 config.yaml 中设置您的 flex_token 和 query_id")
            
            # 允许在界面中输入配置
            st.subheader("临时配置")
            flex_token = st.text_input("Flex Token", type="password", help="从 IBKR 账户管理中获取")
            query_id = st.text_input("Query ID", help="您创建的 Flex Query ID")
            
            if st.button("测试连接"):
                if flex_token and query_id:
                    with st.spinner("正在测试连接..."):
                        success, message = test_connection(flex_token, query_id)
                        if success:
                            st.success(f"✅ {message}")
                            # 临时更新配置
                            st.session_state.data_fetcher.flex_token = flex_token
                            st.session_state.data_fetcher.query_id = query_id
                        else:
                            st.error(f"❌ {message}")
                            
                            # 如果是1020错误，显示详细解决方案
                            if "1020" in message:
                                st.markdown("""
                                **🔧 错误 1020 解决步骤：**
                                1. 登录 [IBKR 账户管理](https://www.interactivebrokers.com)
                                2. 导航到 Reports → Flex Queries
                                3. 检查您的 Flex Query 状态是否为 "Active"
                                4. 确认 Query 包含 "Trades" 数据部分
                                5. 重新生成 Flex Token
                                6. 确保复制的 Token 和 Query ID 没有多余的空格
                                """)
                else:
                    st.warning("请输入完整的配置信息")
        else:
            st.success("✅ API 配置已就绪")
        
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
        
        # 获取数据按钮
        if st.button("🔄 获取交易数据", use_container_width=True):
            if st.session_state.data_fetcher.validate_config():
                with st.spinner("正在获取交易数据..."):
                    trades_df = st.session_state.data_fetcher.fetch_trades(
                        start_date=start_date.strftime("%Y-%m-%d"),
                        end_date=end_date.strftime("%Y-%m-%d")
                    )
                    if not trades_df.empty:
                        # 合并评论
                        trades_df = st.session_state.comment_manager.merge_comments_with_trades(trades_df)
                        st.session_state.trades_df = trades_df
                        
                        # 计算投资组合表现
                        portfolio_data = st.session_state.benchmark_fetcher.calculate_portfolio_performance(
                            trades_df, initial_capital
                        )
                        st.session_state.portfolio_data = portfolio_data
                        
                        st.success(f"✅ 成功获取 {len(trades_df)} 条交易记录")
                    else:
                        st.warning("未获取到交易数据")
            else:
                st.error("请先配置 API 信息")
        
        # Financial Datasets API 连接测试
        if st.button("🔗 测试 Financial Datasets API 连接", use_container_width=True):
            with st.spinner("正在测试连接..."):
                if st.session_state.benchmark_fetcher.test_api_connection():
                    st.success("✅ Financial Datasets API 连接正常")
                else:
                    st.error("❌ Financial Datasets API 连接失败，请检查API密钥配置")
        
        # 数据源选择
        use_mock_data = st.checkbox(
            "🧪 使用模拟数据（演示模式）",
            help="如果网络连接有问题，可以使用模拟数据进行功能演示"
        )
        
        # 获取基准数据按钮
        if selected_benchmarks and st.button("📈 获取基准数据", use_container_width=True):
            with st.spinner("正在获取基准指数数据..."):
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
                        st.success(f"✅ 生成了 {len(benchmark_data)} 个基准指数的模拟数据: {', '.join(benchmark_data.keys())}")
                    else:
                        st.error("❌ 生成模拟数据失败")
                        
                else:
                    # 使用真实数据
                    if not st.session_state.benchmark_fetcher.test_api_connection():
                        st.error("❌ Financial Datasets API 连接失败，无法获取基准数据")
                        st.info("💡 提示：请检查您的API密钥配置。您也可以使用模拟数据进行演示。")
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
                            st.success(f"✅ 成功获取 {len(successful_symbols)} 个基准指数数据: {', '.join(successful_symbols)}")
                        
                        if failed_symbols:
                            st.warning(f"⚠️ 以下基准指数获取失败: {', '.join(failed_symbols)}")
                            st.info("💡 提示：可以尝试重新获取或选择其他基准指数，或者使用模拟数据进行演示")
                        
                        if not benchmark_data:
                            st.error("❌ 未能获取任何基准数据")
        
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
            
            # 基准数据统计
            if st.session_state.benchmark_data:
                st.markdown("**基准指数数据:**")
                for symbol, data in st.session_state.benchmark_data.items():
                    if not data.empty:
                        latest_return = data['Cumulative_Return'].iloc[-1]
                        st.metric(f"{symbol}", f"{latest_return:+.2f}%")
    
    # 主内容区域
    if st.session_state.trades_df.empty:
        st.info("👈 请在侧边栏配置 API 并获取交易数据")
        
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
            - 💾 **数据持久化**: 评论自动保存为本地文件
            - 🔍 **数据筛选**: 支持多维度数据过滤和搜索
            """)
        
        return
    
    # 创建标签页
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 交易记录", "📈 图表分析", "🆚 基准对比", "💬 评论管理", "📊 统计报告"])
    
    with tab1:
        show_trades_table()
    
    with tab2:
        show_charts()
    
    with tab3:
        show_benchmark_comparison()
    
    with tab4:
        show_comment_management()
    
    with tab5:
        show_statistics()

def show_trades_table():
    """显示交易记录表格"""
    st.subheader("📋 交易记录")
    
    df = st.session_state.trades_df.copy()
    
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
            if st.button("💾 保存更改", use_container_width=True):
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
        ["交易时间线", "盈亏分析", "交易量分析", "标的分布", "评论分析", "与基准对比"]
    )
    
    if chart_type == "交易时间线":
        fig = chart_gen.create_trade_timeline(df)
        st.plotly_chart(fig, use_container_width=True)
        
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
    
    elif chart_type == "与基准对比":
        if st.session_state.benchmark_data and not st.session_state.portfolio_data.empty:
            fig = chart_gen.create_benchmark_comparison(
                st.session_state.portfolio_data, 
                st.session_state.benchmark_data
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.info("💡 提示：鼠标悬停查看详细收益率，可在图例中点击隐藏/显示特定指数")
        else:
            st.warning("⚠️ 请先获取交易数据和基准指数数据")

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
        if st.button("导出评论为 CSV"):
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
        if st.button("备份评论数据"):
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

def show_benchmark_comparison():
    """显示基准对比分析"""
    st.subheader("🆚 基准对比分析")
    
    if st.session_state.benchmark_data and not st.session_state.portfolio_data.empty:
        chart_gen = st.session_state.chart_generator
        benchmark_fetcher = st.session_state.benchmark_fetcher
        
        # 投资组合 vs 基准对比图
        st.subheader("📈 收益率对比")
        fig_comparison = chart_gen.create_benchmark_comparison(
            st.session_state.portfolio_data,
            st.session_state.benchmark_data
        )
        st.plotly_chart(fig_comparison, use_container_width=True)
        
        # 计算表现指标
        st.subheader("📊 表现指标对比")
        
        # 计算投资组合指标
        portfolio_returns = st.session_state.portfolio_data['portfolio_return']
        portfolio_metrics = benchmark_fetcher.calculate_performance_metrics(portfolio_returns)
        
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
            st.markdown("**投资组合表现:**")
            metrics_df = pd.DataFrame([{
                '指标': '总收益率 (%)',
                '值': f"{portfolio_metrics.get('total_return', 0):.2f}"
            }, {
                '指标': '波动率 (%)', 
                '值': f"{portfolio_metrics.get('volatility', 0):.2f}"
            }, {
                '指标': '最大回撤 (%)',
                '值': f"{portfolio_metrics.get('max_drawdown', 0):.2f}"
            }, {
                '指标': '夏普比率',
                '值': f"{portfolio_metrics.get('sharpe_ratio', 0):.3f}"
            }])
            st.dataframe(metrics_df, hide_index=True, use_container_width=True)
        
        with col2:
            st.markdown("**基准指数表现:**")
            benchmark_summary = []
            for symbol, metrics in benchmark_metrics.items():
                benchmark_summary.append({
                    '指数': symbol,
                    '总收益率 (%)': f"{metrics.get('total_return', 0):.2f}",
                    '波动率 (%)': f"{metrics.get('volatility', 0):.2f}",
                    '最大回撤 (%)': f"{metrics.get('max_drawdown', 0):.2f}",
                    '夏普比率': f"{metrics.get('sharpe_ratio', 0):.3f}"
                })
            
            if benchmark_summary:
                benchmark_df = pd.DataFrame(benchmark_summary)
                st.dataframe(benchmark_df, hide_index=True, use_container_width=True)
        
        # 表现指标对比图
        if benchmark_metrics:
            fig_metrics = chart_gen.create_performance_metrics_comparison(
                portfolio_metrics, benchmark_metrics
            )
            st.plotly_chart(fig_metrics, use_container_width=True)
        
        # 相关性分析
        if len(st.session_state.benchmark_data) == 1:
            st.subheader("📊 相关性分析")
            benchmark_symbol = list(st.session_state.benchmark_data.keys())[0]
            benchmark_data = st.session_state.benchmark_data[benchmark_symbol]
            
            fig_corr = chart_gen.create_rolling_correlation(
                st.session_state.portfolio_data,
                benchmark_data
            )
            st.plotly_chart(fig_corr, use_container_width=True)
            
            st.info("💡 相关性说明：\n- 接近 1：高度正相关\n- 接近 0：无相关性\n- 接近 -1：高度负相关")
        
        # 基准指数信息
        st.subheader("ℹ️ 基准指数信息")
        for symbol in st.session_state.benchmark_data.keys():
            info = benchmark_fetcher.get_benchmark_info(symbol)
            with st.expander(f"{symbol} - {info['name']}"):
                st.write(f"**货币:** {info['currency']}")
                st.write(f"**交易所:** {info['exchange']}")
                if info['description']:
                    st.write(f"**描述:** {info['description']}")
    
    else:
        st.info("请先获取交易数据和基准指数数据以进行对比分析")
        
        st.subheader("📖 使用指南")
        with st.expander("如何进行基准对比分析", expanded=True):
            st.markdown("""
            1. **获取交易数据**: 在侧边栏点击"🔄 获取交易数据"
            2. **选择基准指数**: 选择如 SPY、QQQ 等基准指数
            3. **获取基准数据**: 点击"📈 获取基准数据"
            4. **查看对比**: 返回此页面查看详细对比分析
            
            **支持的基准指数:**
            - **SPY**: S&P 500 ETF
            - **QQQ**: 纳斯达克 100 ETF  
            - **VTI**: 全市场 ETF
            - **IWM**: 小盘股 ETF
            - **^GSPC**: S&P 500 指数
            - **^IXIC**: 纳斯达克指数
            """)

if __name__ == "__main__":
    main() 