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
                fig.update_yaxis(title_text="%", row=row, col=col)
            else:  # sharpe_ratio
                fig.update_yaxis(title_text="比率", row=row, col=col)
        
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
        
        # 合并数据
        merged_data = pd.merge(
            portfolio_data[['datetime', 'portfolio_return']],
            benchmark_data[['Date', 'Cumulative_Return']].rename(columns={'Date': 'datetime', 'Cumulative_Return': 'benchmark_return'}),
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