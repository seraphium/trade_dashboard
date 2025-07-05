"""
图表工具模块
"""
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
import streamlit as st
from typing import List, Dict, Any

class ChartGenerator:
    """图表生成器"""
    
    def __init__(self, theme: str = "plotly_white"):
        """初始化图表生成器"""
        self.theme = theme
    
    def create_trade_timeline(self, trades_df: pd.DataFrame, height: int = 600) -> go.Figure:
        """创建交易时间线图表"""
        if trades_df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="暂无交易数据",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font_size=16
            )
            return fig
        
        # 按符号分组，创建子图
        symbols = trades_df['symbol'].unique()
        colors = px.colors.qualitative.Set3
        
        fig = go.Figure()
        
        for i, symbol in enumerate(symbols):
            symbol_trades = trades_df[trades_df['symbol'] == symbol]
            color = colors[i % len(colors)]
            
            # 买入点
            buys = symbol_trades[symbol_trades['side'] == 'BUY']
            if not buys.empty:
                fig.add_trace(go.Scatter(
                    x=buys['datetime'],
                    y=buys['price'],
                    mode='markers',
                    marker=dict(
                        symbol='triangle-up',
                        size=buys['quantity'] / buys['quantity'].max() * 20 + 8,
                        color='green',
                        line=dict(width=2, color='darkgreen')
                    ),
                    name=f'{symbol} 买入',
                    text=buys.apply(lambda row: f"买入 {row['quantity']} @ ${row['price']:.2f}<br>评论: {row['comment'][:50]}{'...' if len(row['comment']) > 50 else ''}", axis=1),
                    hovertemplate='%{text}<extra></extra>'
                ))
            
            # 卖出点
            sells = symbol_trades[symbol_trades['side'] == 'SELL']
            if not sells.empty:
                fig.add_trace(go.Scatter(
                    x=sells['datetime'],
                    y=sells['price'],
                    mode='markers',
                    marker=dict(
                        symbol='triangle-down',
                        size=sells['quantity'] / sells['quantity'].max() * 20 + 8,
                        color='red',
                        line=dict(width=2, color='darkred')
                    ),
                    name=f'{symbol} 卖出',
                    text=sells.apply(lambda row: f"卖出 {row['quantity']} @ ${row['price']:.2f}<br>评论: {row['comment'][:50]}{'...' if len(row['comment']) > 50 else ''}", axis=1),
                    hovertemplate='%{text}<extra></extra>'
                ))
        
        fig.update_layout(
            title="交易时间线分析",
            xaxis_title="时间",
            yaxis_title="价格 (USD)",
            template=self.theme,
            height=height,
            hovermode='closest',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return fig

    def create_twr_with_trades_timeline(self, twr_result: Dict[str, Any], trades_df: pd.DataFrame, height: int = 600) -> go.Figure:
        """创建基于TWR曲线的交易时间线图表"""
        fig = go.Figure()

        # 首先添加TWR曲线
        if twr_result and 'twr_timeseries' in twr_result and not twr_result['twr_timeseries'].empty:
            twr_data = twr_result['twr_timeseries'].copy()

            # 添加TWR曲线
            fig.add_trace(go.Scatter(
                x=twr_data['date'],
                y=twr_data['twr_return'],
                mode='lines',
                name='TWR收益率曲线',
                line=dict(width=3, color='#2E86AB'),
                hovertemplate='日期: %{x}<br>TWR收益率: %{y:.2f}%<extra></extra>'
            ))

            # 获取TWR数据的时间范围
            twr_start_date = twr_data['date'].min()
            twr_end_date = twr_data['date'].max()

            # 过滤交易数据，只保留在TWR时间范围内的交易
            if not trades_df.empty:
                trades_df = trades_df.copy()
                trades_df['datetime'] = pd.to_datetime(trades_df['datetime'])

                # 过滤交易时间
                filtered_trades = trades_df[
                    (trades_df['datetime'].dt.date >= twr_start_date.date()) &
                    (trades_df['datetime'].dt.date <= twr_end_date.date())
                ]

                if not filtered_trades.empty:
                    # 为每笔交易找到对应的TWR值
                    trade_twr_values = []

                    for _, trade in filtered_trades.iterrows():
                        trade_date = trade['datetime'].date()

                        # 找到最接近的TWR数据点
                        twr_data['date_only'] = twr_data['date'].dt.date
                        closest_twr = twr_data[twr_data['date_only'] <= trade_date]

                        if not closest_twr.empty:
                            twr_value = closest_twr.iloc[-1]['twr_return']
                            trade_twr_values.append(twr_value)
                        else:
                            # 如果找不到对应的TWR值，使用第一个TWR值
                            trade_twr_values.append(twr_data['twr_return'].iloc[0])

                    filtered_trades = filtered_trades.copy()
                    filtered_trades['twr_value'] = trade_twr_values

                    # 按符号分组添加交易标记
                    symbols = filtered_trades['symbol'].unique()

                    for symbol in symbols:
                        symbol_trades = filtered_trades[filtered_trades['symbol'] == symbol]

                        # 买入点
                        buys = symbol_trades[symbol_trades['side'] == 'BUY']
                        if not buys.empty:
                            fig.add_trace(go.Scatter(
                                x=buys['datetime'],
                                y=buys['twr_value'],
                                mode='markers',
                                marker=dict(
                                    symbol='triangle-up',
                                    size=12,
                                    color='green',
                                    line=dict(width=2, color='darkgreen')
                                ),
                                name=f'{symbol} 买入',
                                text=buys.apply(lambda row: f"买入 {row['quantity']} {row['symbol']} @ ${row['price']:.2f}<br>TWR: {row['twr_value']:.2f}%<br>评论: {row['comment'][:50]}{'...' if len(row['comment']) > 50 else ''}", axis=1),
                                hovertemplate='%{text}<extra></extra>',
                                showlegend=True
                            ))

                        # 卖出点
                        sells = symbol_trades[symbol_trades['side'] == 'SELL']
                        if not sells.empty:
                            fig.add_trace(go.Scatter(
                                x=sells['datetime'],
                                y=sells['twr_value'],
                                mode='markers',
                                marker=dict(
                                    symbol='triangle-down',
                                    size=12,
                                    color='red',
                                    line=dict(width=2, color='darkred')
                                ),
                                name=f'{symbol} 卖出',
                                text=sells.apply(lambda row: f"卖出 {row['quantity']} {row['symbol']} @ ${row['price']:.2f}<br>TWR: {row['twr_value']:.2f}%<br>评论: {row['comment'][:50]}{'...' if len(row['comment']) > 50 else ''}", axis=1),
                                hovertemplate='%{text}<extra></extra>',
                                showlegend=True
                            ))

        # 添加零线
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

        fig.update_layout(
            title="TWR曲线 & 交易时间线分析",
            xaxis_title="时间",
            yaxis_title="TWR收益率 (%)",
            template=self.theme,
            height=height,
            hovermode='closest',
            showlegend=False  # 不显示图例，节省空间
        )

        return fig
    
    def create_pnl_chart(self, trades_df: pd.DataFrame) -> go.Figure:
        """创建盈亏分析图表"""
        if trades_df.empty:
            return go.Figure()
        
        # 计算每笔交易的盈亏（简化计算）
        trades_df = trades_df.copy()
        trades_df['pnl'] = trades_df.apply(
            lambda row: row['proceeds'] - row['commission'] if row['side'] == 'SELL' else -(row['proceeds'] + row['commission']),
            axis=1
        )
        
        # 累计盈亏
        trades_df = trades_df.sort_values('datetime')
        trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
        
        fig = go.Figure()
        
        # 累计盈亏线
        fig.add_trace(go.Scatter(
            x=trades_df['datetime'],
            y=trades_df['cumulative_pnl'],
            mode='lines+markers',
            name='累计盈亏',
            line=dict(width=2),
            marker=dict(size=6)
        ))
        
        # 零线
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        
        fig.update_layout(
            title="累计盈亏分析",
            xaxis_title="时间",
            yaxis_title="累计盈亏 (USD)",
            template=self.theme,
            height=400
        )
        
        return fig
    
    def create_trading_volume_chart(self, trades_df: pd.DataFrame) -> go.Figure:
        """创建交易量分析图表"""
        if trades_df.empty:
            return go.Figure()
        
        # 按日期汇总交易量
        daily_volume = trades_df.groupby(trades_df['datetime'].dt.date).agg({
            'quantity': 'sum',
            'proceeds': lambda x: abs(x).sum()
        }).reset_index()
        
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('每日交易数量', '每日交易金额'),
            vertical_spacing=0.1
        )
        
        # 交易数量
        fig.add_trace(
            go.Bar(x=daily_volume['datetime'], y=daily_volume['quantity'], name='交易数量'),
            row=1, col=1
        )
        
        # 交易金额
        fig.add_trace(
            go.Bar(x=daily_volume['datetime'], y=daily_volume['proceeds'], name='交易金额'),
            row=2, col=1
        )
        
        fig.update_layout(
            title="交易量分析",
            template=self.theme,
            height=500,
            showlegend=False
        )
        
        return fig
    
    def create_symbol_distribution(self, trades_df: pd.DataFrame) -> go.Figure:
        """创建标的分布图表"""
        if trades_df.empty:
            return go.Figure()
        
        symbol_stats = trades_df.groupby('symbol').agg({
            'quantity': 'sum',
            'proceeds': lambda x: abs(x).sum(),
            'trade_id': 'count'
        }).rename(columns={'trade_id': 'trade_count'}).reset_index()
        
        fig = go.Figure(data=[
            go.Pie(
                labels=symbol_stats['symbol'],
                values=symbol_stats['proceeds'],
                textinfo='label+percent',
                hole=0.3
            )
        ])
        
        fig.update_layout(
            title="交易标的分布（按金额）",
            template=self.theme,
            height=400
        )
        
        return fig
    
    def create_comment_analysis(self, trades_df: pd.DataFrame) -> go.Figure:
        """创建评论分析图表"""
        if trades_df.empty or 'comment_category' not in trades_df.columns:
            return go.Figure()
        
        # 统计评论分类
        category_stats = trades_df[trades_df['comment'] != ''].groupby('comment_category').size()
        
        if category_stats.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="暂无评论数据",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font_size=16
            )
            return fig
        
        # 定义颜色映射
        color_map = {
            'Good': '#2ECC71',    # 绿色
            'Bad': '#E74C3C',     # 红色
            'Neutral': '#95A5A6'  # 灰色
        }
        
        # 按顺序排列分类
        category_order = ['Good', 'Bad', 'Neutral']
        ordered_categories = [cat for cat in category_order if cat in category_stats.index]
        
        colors = [color_map.get(cat, '#3498DB') for cat in ordered_categories]
        values = [category_stats.get(cat, 0) for cat in ordered_categories]
        
        fig = go.Figure(data=[
            go.Bar(
                x=ordered_categories, 
                y=values,
                marker_color=colors,
                text=values,
                textposition='auto',
                hovertemplate='分类: %{x}<br>数量: %{y}<extra></extra>'
            )
        ])
        
        fig.update_layout(
            title="交易评论分类统计",
            xaxis_title="评论分类",
            yaxis_title="数量",
            template=self.theme,
            height=400,
            showlegend=False
        )
        
        return fig
    
    def create_benchmark_comparison(self, portfolio_data: pd.DataFrame, benchmark_data: Dict[str, pd.DataFrame], 
                                   initial_capital: float = 100000) -> go.Figure:
        """创建投资组合与基准指数对比图表"""
        fig = go.Figure()
        
        # 添加投资组合表现线
        if not portfolio_data.empty:
            fig.add_trace(go.Scatter(
                x=portfolio_data['datetime'],
                y=portfolio_data['portfolio_return'],
                mode='lines',
                name='我的投资组合',
                line=dict(width=3, color='#2E86AB'),
                hovertemplate='日期: %{x}<br>收益率: %{y:.2f}%<extra></extra>'
            ))
        
        # 添加基准指数线
        colors = ['#A23B72', '#F18F01', '#C73E1D', '#592941', '#3F7CAC']
        for i, (symbol, data) in enumerate(benchmark_data.items()):
            if not data.empty:
                fig.add_trace(go.Scatter(
                    x=data['Date'],
                    y=data['Cumulative_Return'],
                    mode='lines',
                    name=f'{symbol}',
                    line=dict(width=2, color=colors[i % len(colors)]),
                    hovertemplate=f'{symbol}<br>日期: %{{x}}<br>收益率: %{{y:.2f}}%<extra></extra>'
                ))
        
        # 添加零线
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        
        fig.update_layout(
            title="投资组合 vs 基准指数表现对比",
            xaxis_title="时间",
            yaxis_title="累计收益率 (%)",
            template=self.theme,
            height=600,
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.15,
                xanchor="center",
                x=0.5
            )
        )
        
        return fig
    
    def create_performance_metrics_comparison(self, portfolio_metrics: Dict[str, float], 
                                            benchmark_metrics: Dict[str, Dict[str, float]]) -> go.Figure:
        """创建表现指标对比图表"""
        
        # 准备数据
        metrics_names = ['总收益率', '波动率', '最大回撤', '夏普比率']
        metric_keys = ['total_return', 'volatility', 'max_drawdown', 'sharpe_ratio']
        
        # 创建子图
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=metrics_names,
            specs=[[{"type": "bar"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "bar"}]]
        )
        
        positions = [(1, 1), (1, 2), (2, 1), (2, 2)]
        
        for i, (metric_name, metric_key) in enumerate(zip(metrics_names, metric_keys)):
            row, col = positions[i]
            
            # 收集数据
            names = ['我的投资组合']
            values = [portfolio_metrics.get(metric_key, 0)]
            
            for symbol, metrics in benchmark_metrics.items():
                names.append(symbol)
                values.append(metrics.get(metric_key, 0))
            
            # 添加柱状图
            fig.add_trace(
                go.Bar(
                    x=names,
                    y=values,
                    name=metric_name,
                    showlegend=False,
                    marker_color=['#2E86AB'] + ['#A23B72', '#F18F01', '#C73E1D', '#592941'][:len(names)-1]
                ),
                row=row, col=col
            )
            
            # 设置y轴标签
            if metric_key in ['total_return', 'volatility', 'max_drawdown']:
                fig.update_yaxes(title_text="%", row=row, col=col)
            else:  # sharpe_ratio
                fig.update_yaxes(title_text="比率", row=row, col=col)
        
        fig.update_layout(
            title="表现指标对比",
            template=self.theme,
            height=600,
            showlegend=False
        )
        
        return fig
    
    def create_rolling_correlation(self, portfolio_data: pd.DataFrame, benchmark_data: pd.DataFrame, 
                                  window: int = 30) -> go.Figure:
        """创建滚动相关性图表"""
        if portfolio_data.empty or benchmark_data.empty:
            return go.Figure()
        
        # 准备数据，统一时区处理
        portfolio_subset = portfolio_data[['datetime', 'portfolio_return']].copy()
        benchmark_subset = benchmark_data[['Date', 'Cumulative_Return']].rename(
            columns={'Date': 'datetime', 'Cumulative_Return': 'benchmark_return'}
        ).copy()
        
        # 统一处理时区信息 - 移除时区信息以避免合并错误
        if pd.api.types.is_datetime64_any_dtype(portfolio_subset['datetime']):
            if hasattr(portfolio_subset['datetime'].dtype, 'tz') and portfolio_subset['datetime'].dtype.tz is not None:
                portfolio_subset['datetime'] = portfolio_subset['datetime'].dt.tz_localize(None)
        
        if pd.api.types.is_datetime64_any_dtype(benchmark_subset['datetime']):
            if hasattr(benchmark_subset['datetime'].dtype, 'tz') and benchmark_subset['datetime'].dtype.tz is not None:
                benchmark_subset['datetime'] = benchmark_subset['datetime'].dt.tz_localize(None)
        
        # 合并数据
        merged_data = pd.merge(
            portfolio_subset,
            benchmark_subset,
            on='datetime',
            how='inner'
        )
        
        if len(merged_data) < window:
            fig = go.Figure()
            fig.add_annotation(
                text="数据不足以计算滚动相关性",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font_size=16
            )
            return fig
        
        # 计算滚动相关性
        merged_data['rolling_corr'] = merged_data['portfolio_return'].rolling(window=window).corr(
            merged_data['benchmark_return']
        )
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=merged_data['datetime'],
            y=merged_data['rolling_corr'],
            mode='lines',
            name=f'{window}日滚动相关性',
            line=dict(width=2, color='#2E86AB'),
            hovertemplate='日期: %{x}<br>相关性: %{y:.3f}<extra></extra>'
        ))
        
        # 添加参考线
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig.add_hline(y=0.5, line_dash="dot", line_color="green", opacity=0.5, annotation_text="中度相关")
        fig.add_hline(y=0.8, line_dash="dot", line_color="red", opacity=0.5, annotation_text="高度相关")
        
        fig.update_layout(
            title=f"与基准指数的{window}日滚动相关性",
            xaxis_title="时间",
            yaxis_title="相关系数",
            template=self.theme,
            height=400,
            yaxis=dict(range=[-1, 1])
        )
        
        return fig
    
    def create_twr_chart(self, twr_result: Dict[str, Any]) -> go.Figure:
        """创建TWR分析图表"""
        if not twr_result or twr_result.get('nav_data').empty:
            fig = go.Figure()
            fig.add_annotation(
                text="暂无TWR数据",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font_size=16
            )
            return fig
        
        nav_data = twr_result['nav_data']
        
        # 计算累计收益率
        nav_data = nav_data.copy()
        initial_nav = nav_data.iloc[0]['nav']
        nav_data['cumulative_return'] = (nav_data['nav'] / initial_nav - 1) * 100
        
        fig = go.Figure()
        
        # NAV曲线
        fig.add_trace(go.Scatter(
            x=nav_data['date'],
            y=nav_data['nav'],
            mode='lines',
            name='净资产价值',
            line=dict(width=2, color='blue'),
            yaxis='y1'
        ))
        
        # 累计收益率曲线
        fig.add_trace(go.Scatter(
            x=nav_data['date'],
            y=nav_data['cumulative_return'],
            mode='lines',
            name='累计收益率(%)',
            line=dict(width=2, color='green'),
            yaxis='y2'
        ))
        
        # 标记现金流事件
        if not twr_result.get('external_cash_flows').empty:
            cash_flows = twr_result['external_cash_flows']
            for _, cf in cash_flows.iterrows():
                color = 'red' if cf['amount'] < 0 else 'orange'
                fig.add_trace(go.Scatter(
                    x=[cf['date']],
                    y=[nav_data[nav_data['date'] == cf['date']]['nav'].iloc[0] if not nav_data[nav_data['date'] == cf['date']].empty else 0],
                    mode='markers',
                    marker=dict(size=10, color=color, symbol='diamond'),
                    name=f"现金流: {cf['amount']:.0f}",
                    showlegend=False,
                    hovertemplate=f"现金流: ${cf['amount']:.2f}<br>类型: {cf['type']}<extra></extra>"
                ))
        
        # 创建双y轴布局
        fig.update_layout(
            title=f"时间加权收益率分析 (TWR: {twr_result['total_twr']:.2%})",
            xaxis_title="日期",
            template=self.theme,
            height=500,
            yaxis=dict(
                title="净资产价值 (USD)",
                side="left",
                title_font=dict(color="blue"),
                tickfont=dict(color="blue")
            ),
            yaxis2=dict(
                title="累计收益率 (%)",
                side="right",
                overlaying="y",
                title_font=dict(color="green"),
                tickfont=dict(color="green")
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return fig
    
    def create_periodic_twr_chart(self, periodic_twr: pd.DataFrame, frequency: str = 'M') -> go.Figure:
        """创建周期性TWR图表"""
        if periodic_twr.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="暂无周期性TWR数据",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font_size=16
            )
            return fig
        
        # 频率标签映射
        freq_labels = {
            'D': '日',
            'W': '周',
            'M': '月',
            'Q': '季度',
            'Y': '年'
        }
        
        freq_label = freq_labels.get(frequency, frequency)
        
        fig = go.Figure()
        
        # 收益率柱状图
        colors = ['green' if r >= 0 else 'red' for r in periodic_twr['return']]
        
        fig.add_trace(go.Bar(
            x=periodic_twr['period'],
            y=periodic_twr['return'] * 100,
            name=f'{freq_label}度收益率',
            marker_color=colors,
            text=[f"{r:.1%}" for r in periodic_twr['return']],
            textposition='outside'
        ))
        
        # 零线
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        
        fig.update_layout(
            title=f"{freq_label}度时间加权收益率",
            xaxis_title="时期",
            yaxis_title="收益率 (%)",
            template=self.theme,
            height=400,
            showlegend=False
        )
        
        return fig
    
    def create_twr_metrics_dashboard(self, twr_result: Dict[str, Any]) -> go.Figure:
        """创建TWR指标仪表板"""
        if not twr_result:
            return go.Figure()
        
        # 创建子图
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('总TWR', '年化收益率', '波动率', '夏普比率'),
            specs=[[{"type": "indicator"}, {"type": "indicator"}],
                   [{"type": "indicator"}, {"type": "indicator"}]]
        )
        
        # 总TWR
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=twr_result['total_twr'] * 100,
            title={'text': "总TWR (%)"},
            gauge={'axis': {'range': [-50, 50]},
                   'bar': {'color': "darkblue"},
                   'steps': [
                       {'range': [-50, 0], 'color': "lightgray"},
                       {'range': [0, 50], 'color': "gray"}],
                   'threshold': {'line': {'color': "red", 'width': 4},
                                'thickness': 0.75, 'value': 0}},
            number={'suffix': '%'}
        ), row=1, col=1)
        
        # 年化收益率
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=twr_result['annualized_return'] * 100,
            title={'text': "年化收益率 (%)"},
            gauge={'axis': {'range': [-30, 30]},
                   'bar': {'color': "darkgreen"},
                   'steps': [
                       {'range': [-30, 0], 'color': "lightgray"},
                       {'range': [0, 30], 'color': "gray"}],
                   'threshold': {'line': {'color': "red", 'width': 4},
                                'thickness': 0.75, 'value': 0}},
            number={'suffix': '%'}
        ), row=1, col=2)
        
        # 波动率
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=twr_result['volatility'] * 100,
            title={'text': "年化波动率 (%)"},
            gauge={'axis': {'range': [0, 50]},
                   'bar': {'color': "orange"},
                   'steps': [
                       {'range': [0, 20], 'color': "lightgreen"},
                       {'range': [20, 35], 'color': "yellow"},
                       {'range': [35, 50], 'color': "lightcoral"}],
                   'threshold': {'line': {'color': "red", 'width': 4},
                                'thickness': 0.75, 'value': 25}},
            number={'suffix': '%'}
        ), row=2, col=1)
        
        # 夏普比率
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=twr_result['sharpe_ratio'],
            title={'text': "夏普比率"},
            gauge={'axis': {'range': [-2, 3]},
                   'bar': {'color': "purple"},
                   'steps': [
                       {'range': [-2, 0], 'color': "lightcoral"},
                       {'range': [0, 1], 'color': "yellow"},
                       {'range': [1, 2], 'color': "lightgreen"},
                       {'range': [2, 3], 'color': "green"}],
                   'threshold': {'line': {'color': "red", 'width': 4},
                                'thickness': 0.75, 'value': 1}},
        ), row=2, col=2)
        
        fig.update_layout(
            title="TWR绩效指标仪表板",
            template=self.theme,
            height=600
        )
        
        return fig
    
    def create_cash_flow_impact_chart(self, twr_result: Dict[str, Any]) -> go.Figure:
        """创建现金流影响分析图表"""
        external_cash_flows = twr_result.get('external_cash_flows') if twr_result else None
        if not twr_result or external_cash_flows is None or external_cash_flows.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="暂无现金流数据",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font_size=16
            )
            return fig
        
        cash_flows = twr_result['external_cash_flows']
        
        # 按类型分组
        cf_summary = cash_flows.groupby('type')['amount'].agg(['sum', 'count']).reset_index()
        
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('现金流类型分布', '现金流时间序列'),
            specs=[[{"type": "pie"}, {"type": "scatter"}]]
        )
        
        # 饼图：现金流类型分布
        fig.add_trace(go.Pie(
            labels=cf_summary['type'],
            values=cf_summary['sum'].abs(),
            name="现金流类型",
            textinfo='label+percent',
            hole=0.3
        ), row=1, col=1)
        
        # 现金流时间序列
        fig.add_trace(go.Scatter(
            x=cash_flows['date'],
            y=cash_flows['amount'],
            mode='markers+lines',
            name='现金流',
            marker=dict(
                size=8,
                color=['red' if amount < 0 else 'green' for amount in cash_flows['amount']],
                line=dict(width=2, color='black')
            ),
            line=dict(width=1, color='gray')
        ), row=1, col=2)
        
        # 零线 - 只添加到散点图子图
        fig.add_shape(
            type="line",
            x0=cash_flows['date'].min(),
            x1=cash_flows['date'].max(),
            y0=0,
            y1=0,
            line=dict(dash="dash", color="gray", width=1),
            opacity=0.5,
            row=1, col=2
        )
        
        fig.update_layout(
            title="现金流影响分析",
            template=self.theme,
            height=400,
            showlegend=False
        )
        
        return fig

    def create_twr_benchmark_comparison(self, twr_result: Dict[str, Any], benchmark_data: Dict[str, pd.DataFrame]) -> go.Figure:
        """创建TWR与基准指数对比图表"""
        fig = go.Figure()

        # 添加TWR表现线
        if twr_result and 'twr_timeseries' in twr_result and not twr_result['twr_timeseries'].empty:
            twr_data = twr_result['twr_timeseries'].copy()

            fig.add_trace(go.Scatter(
                x=twr_data['date'],
                y=twr_data['twr_return'],
                mode='lines',
                name='我的投资组合 (TWR)',
                line=dict(width=3, color='#2E86AB'),
                hovertemplate='日期: %{x}<br>TWR收益率: %{y:.2f}%<extra></extra>'
            ))

        # 添加基准指数线
        colors = ['#A23B72', '#F18F01', '#C73E1D', '#592941', '#3F7CAC']
        for i, (symbol, data) in enumerate(benchmark_data.items()):
            if not data.empty:
                fig.add_trace(go.Scatter(
                    x=data['Date'],
                    y=data['Cumulative_Return'],
                    mode='lines',
                    name=f'{symbol}',
                    line=dict(width=2, color=colors[i % len(colors)]),
                    hovertemplate=f'{symbol}<br>日期: %{{x}}<br>收益率: %{{y:.2f}}%<extra></extra>'
                ))

        # 添加零线
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

        fig.update_layout(
            title="投资组合(TWR) vs 基准指数表现对比",
            xaxis_title="时间",
            yaxis_title="累计收益率 (%)",
            template=self.theme,
            height=600,
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.15,
                xanchor="center",
                x=0.5
            )
        )

        return fig