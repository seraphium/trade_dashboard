"""
基准指数数据获取模块
"""
import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class BenchmarkDataFetcher:
    """基准指数数据获取器"""
    
    # 预定义的基准指数
    BENCHMARKS = {
        'SPY': 'SPDR S&P 500 ETF (SPY)',
        'QQQ': 'Invesco QQQ ETF (QQQ)', 
        'VTI': 'Vanguard Total Stock Market ETF (VTI)',
        'IWM': 'iShares Russell 2000 ETF (IWM)',
        'DIA': 'SPDR Dow Jones Industrial ETF (DIA)',
        'VEA': 'Vanguard FTSE Developed Markets ETF (VEA)',
        'VWO': 'Vanguard FTSE Emerging Markets ETF (VWO)',
        '^GSPC': 'S&P 500 指数',
        '^IXIC': '纳斯达克综合指数',
        '^DJI': '道琼斯工业平均指数'
    }
    
    def __init__(self):
        """初始化基准数据获取器"""
        pass
    
    @st.cache_data(ttl=3600)  # 缓存1小时
    def fetch_benchmark_data(_self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取基准指数数据
        
        Args:
            symbol: 指数符号 (如 'SPY', 'QQQ')
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            DataFrame: 基准指数价格数据
        """
        try:
            logger.info(f"正在获取基准指数数据: {symbol} ({start_date} 到 {end_date})")
            
            # 使用 yfinance 获取数据
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date)
            
            if hist.empty:
                logger.warning(f"未获取到 {symbol} 的数据")
                return pd.DataFrame()
            
            # 重置索引，将日期作为列
            hist = hist.reset_index()
            hist['Date'] = pd.to_datetime(hist['Date'])
            
            # 计算累计收益率
            hist['Cumulative_Return'] = (hist['Close'] / hist['Close'].iloc[0] - 1) * 100
            
            # 计算每日收益率
            hist['Daily_Return'] = hist['Close'].pct_change() * 100
            
            logger.info(f"成功获取 {symbol} 的 {len(hist)} 条数据")
            return hist
            
        except Exception as e:
            logger.error(f"获取基准数据失败: {str(e)}")
            st.error(f"❌ 获取 {symbol} 数据失败: {str(e)}")
            return pd.DataFrame()
    
    def get_multiple_benchmarks(self, symbols: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """
        获取多个基准指数数据
        
        Args:
            symbols: 指数符号列表
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Dict: 符号到数据DataFrame的映射
        """
        benchmarks_data = {}
        
        for symbol in symbols:
            data = self.fetch_benchmark_data(symbol, start_date, end_date)
            if not data.empty:
                benchmarks_data[symbol] = data
        
        return benchmarks_data
    
    def calculate_portfolio_performance(self, trades_df: pd.DataFrame, initial_capital: float = 100000) -> pd.DataFrame:
        """
        计算投资组合表现
        
        Args:
            trades_df: 交易数据
            initial_capital: 初始资金
            
        Returns:
            DataFrame: 投资组合每日表现数据
        """
        if trades_df.empty:
            return pd.DataFrame()
        
        try:
            # 按日期排序
            trades_df = trades_df.sort_values('datetime')
            
            # 计算每笔交易的盈亏
            trades_df = trades_df.copy()
            trades_df['pnl'] = trades_df.apply(
                lambda row: row['proceeds'] - row['commission'] if row['side'] == 'SELL' 
                else -(row['proceeds'] + row['commission']),
                axis=1
            )
            
            # 计算累计盈亏
            trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
            
            # 创建每日组合价值数据
            daily_portfolio = trades_df.groupby(trades_df['datetime'].dt.date).agg({
                'cumulative_pnl': 'last'
            }).reset_index()
            
            daily_portfolio['datetime'] = pd.to_datetime(daily_portfolio['datetime'])
            daily_portfolio['portfolio_value'] = initial_capital + daily_portfolio['cumulative_pnl']
            daily_portfolio['portfolio_return'] = (daily_portfolio['portfolio_value'] / initial_capital - 1) * 100
            
            return daily_portfolio
            
        except Exception as e:
            logger.error(f"计算投资组合表现失败: {str(e)}")
            return pd.DataFrame()
    
    def calculate_performance_metrics(self, returns_series: pd.Series) -> Dict[str, float]:
        """
        计算表现指标
        
        Args:
            returns_series: 收益率序列 (百分比)
            
        Returns:
            Dict: 表现指标
        """
        try:
            metrics = {}
            
            # 基础统计
            metrics['total_return'] = returns_series.iloc[-1] if len(returns_series) > 0 else 0
            metrics['volatility'] = returns_series.std() if len(returns_series) > 1 else 0
            metrics['max_return'] = returns_series.max() if len(returns_series) > 0 else 0
            metrics['min_return'] = returns_series.min() if len(returns_series) > 0 else 0
            
            # 最大回撤
            cumulative = (1 + returns_series / 100).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max * 100
            metrics['max_drawdown'] = drawdown.min()
            
            # 夏普比率 (假设无风险利率为2%)
            excess_returns = returns_series - 2/252  # 日化无风险利率
            metrics['sharpe_ratio'] = excess_returns.mean() / excess_returns.std() * (252**0.5) if excess_returns.std() > 0 else 0
            
            return metrics
            
        except Exception as e:
            logger.error(f"计算表现指标失败: {str(e)}")
            return {}
    
    def get_benchmark_info(self, symbol: str) -> Dict[str, str]:
        """获取基准指数信息"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                'name': info.get('longName', info.get('shortName', symbol)),
                'currency': info.get('currency', 'USD'),
                'exchange': info.get('exchange', ''),
                'description': info.get('longBusinessSummary', '')[:200] + '...' if info.get('longBusinessSummary') else ''
            }
        except Exception as e:
            logger.error(f"获取 {symbol} 信息失败: {str(e)}")
            return {
                'name': self.BENCHMARKS.get(symbol, symbol),
                'currency': 'USD',
                'exchange': '',
                'description': ''
            } 