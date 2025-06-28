"""
基准指数数据获取模块
"""
import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional
import requests
import time

logger = logging.getLogger(__name__)

# 配置请求会话以提高连接稳定性
def setup_yfinance_session():
    """设置 yfinance 会话配置"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    return session

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
    def fetch_benchmark_data(_self, symbol: str, start_date: str, end_date: str, max_retries: int = 3) -> pd.DataFrame:
        """
        获取基准指数数据
        
        Args:
            symbol: 指数符号 (如 'SPY', 'QQQ')
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            max_retries: 最大重试次数
            
        Returns:
            DataFrame: 基准指数价格数据
        """
        import time
        
        for attempt in range(max_retries):
            try:
                logger.info(f"正在获取基准指数数据: {symbol} ({start_date} 到 {end_date}) - 尝试 {attempt + 1}/{max_retries}")
                
                # 使用 yfinance 获取数据，增加更多参数来提高稳定性
                session = setup_yfinance_session()
                ticker = yf.Ticker(symbol, session=session)
                
                # 添加小延时避免请求过于频繁
                if attempt > 0:
                    time.sleep(1)
                
                hist = ticker.history(
                    start=start_date, 
                    end=end_date,
                    interval="1d",
                    auto_adjust=True,
                    prepost=False
                )
                
                if hist.empty:
                    logger.warning(f"未获取到 {symbol} 的数据 - 尝试 {attempt + 1}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # 指数退避
                        continue
                    else:
                        return pd.DataFrame()
                
                # 重置索引，将日期作为列
                hist = hist.reset_index()
                hist['Date'] = pd.to_datetime(hist['Date'])
                
                # 验证数据完整性
                if len(hist) == 0 or 'Close' not in hist.columns:
                    logger.warning(f"获取到的 {symbol} 数据不完整 - 尝试 {attempt + 1}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        return pd.DataFrame()
                
                # 计算累计收益率
                hist['Cumulative_Return'] = (hist['Close'] / hist['Close'].iloc[0] - 1) * 100
                
                # 计算每日收益率
                hist['Daily_Return'] = hist['Close'].pct_change() * 100
                
                logger.info(f"成功获取 {symbol} 的 {len(hist)} 条数据")
                return hist
                
            except Exception as e:
                logger.error(f"获取 {symbol} 数据失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
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
            
            # 如果 info 为空或者是错误信息，使用预定义信息
            if not info or 'symbol' not in info:
                logger.warning(f"无法获取 {symbol} 的详细信息，使用预定义信息")
                return {
                    'name': self.BENCHMARKS.get(symbol, symbol),
                    'currency': 'USD',
                    'exchange': '',
                    'description': ''
                }
            
            return {
                'name': info.get('longName', info.get('shortName', self.BENCHMARKS.get(symbol, symbol))),
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
    
    def test_yfinance_connection(self) -> bool:
        """测试 yfinance 连接"""
        try:
            # 尝试获取一个简单的数据来测试连接
            session = setup_yfinance_session()
            ticker = yf.Ticker("SPY", session=session)  # 使用 SPY 代替 AAPL
            hist = ticker.history(period="5d")
            
            # 如果 SPY 失败，尝试其他符号
            if hist.empty:
                ticker = yf.Ticker("QQQ", session=session)
                hist = ticker.history(period="5d")
            
            return not hist.empty
        except Exception as e:
            logger.error(f"yfinance 连接测试失败: {str(e)}")
            return False
    
    def generate_mock_benchmark_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """生成模拟基准数据用于演示"""
        try:
            import numpy as np
            
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
            dates = pd.date_range(start=start, end=end, freq='B')  # 工作日
            
            # 生成模拟价格数据
            np.random.seed(42)  # 固定种子确保可重复性
            initial_price = 100.0
            
            # 模拟价格走势
            returns = np.random.normal(0.001, 0.02, len(dates))  # 日收益率
            prices = [initial_price]
            
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            # 创建DataFrame
            mock_data = pd.DataFrame({
                'Date': dates,
                'Open': prices,
                'High': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
                'Low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
                'Close': prices,
                'Volume': np.random.randint(1000000, 10000000, len(dates))
            })
            
            # 计算累计收益率
            mock_data['Cumulative_Return'] = (mock_data['Close'] / mock_data['Close'].iloc[0] - 1) * 100
            
            # 计算每日收益率
            mock_data['Daily_Return'] = mock_data['Close'].pct_change() * 100
            
            logger.info(f"生成了 {symbol} 的模拟数据 ({len(mock_data)} 条记录)")
            return mock_data
            
        except Exception as e:
            logger.error(f"生成模拟数据失败: {str(e)}")
            return pd.DataFrame() 