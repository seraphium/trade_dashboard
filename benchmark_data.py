"""
基准指数数据获取模块 - 使用 Financial Datasets API
"""
import os
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional
import requests
import time
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

class BenchmarkDataFetcher:
    """基准指数数据获取器 - 使用 Financial Datasets API"""
    
    # API基础URL
    BASE_URL = "https://api.financialdatasets.ai/prices/"
    
    # 预定义的基准指数
    BENCHMARKS = {
        'SPY': 'SPDR S&P 500 ETF (SPY)',
        'QQQ': 'Invesco QQQ ETF (QQQ)', 
        'VTI': 'Vanguard Total Stock Market ETF (VTI)',
        'IWM': 'iShares Russell 2000 ETF (IWM)',
        'DIA': 'SPDR Dow Jones Industrial ETF (DIA)',
        'VEA': 'Vanguard FTSE Developed Markets ETF (VEA)',
        'VWO': 'Vanguard FTSE Emerging Markets ETF (VWO)',
        'SPTM': 'S&P Total Market ETF (SPTM)',
        'TQQQ': 'ProShares UltraPro QQQ (TQQQ)',
        'UPRO': 'ProShares UltraPro S&P500 (UPRO)'
    }
    
    def __init__(self):
        """初始化基准数据获取器"""
        self.api_key = self._get_api_key()
        if not self.api_key:
            st.warning("⚠️ 未配置 Financial Datasets API Key，请在环境变量或配置文件中设置 FINANCIAL_DATASETS_API_KEY")
    
    def _get_api_key(self) -> str:
        """获取API密钥"""
        # 从环境变量获取
        api_key = os.getenv('FINANCIAL_DATASETS_API_KEY')
        if api_key:
            return api_key
        
        # 从Streamlit secrets获取（如果部署在云端）
        try:
            return st.secrets.get('FINANCIAL_DATASETS_API_KEY', '')
        except:
            return ''
    
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
        if not _self.api_key:
            logger.error("API密钥未配置")
            return pd.DataFrame()
        
        for attempt in range(max_retries):
            try:
                logger.info(f"正在获取基准指数数据: {symbol} ({start_date} 到 {end_date}) - 尝试 {attempt + 1}/{max_retries}")
                
                # 构建请求头
                headers = {
                    'X-API-KEY': _self.api_key
                }
                
                # 构建请求URL（按照API文档格式）
                url = (
                    f'{_self.BASE_URL}'
                    f'?ticker={symbol}'
                    f'&interval=day'
                    f'&interval_multiplier=1'
                    f'&start_date={start_date}'
                    f'&end_date={end_date}'
                )
                
                # 添加小延时避免请求过于频繁
                if attempt > 0:
                    time.sleep(2 ** attempt)
                
                # 发送API请求
                response = requests.get(url, headers=headers, timeout=30)
                
                if response.status_code == 401:
                    logger.error("API密钥无效或已过期")
                    st.error("❌ API密钥无效或已过期，请检查您的Financial Datasets API密钥")
                    return pd.DataFrame()
                
                if response.status_code == 429:
                    logger.warning(f"API请求频率限制 - 尝试 {attempt + 1}")
                    if attempt < max_retries - 1:
                        time.sleep(5 * (attempt + 1))
                        continue
                    else:
                        st.error("❌ API请求频率限制，请稍后重试")
                        return pd.DataFrame()
                
                response.raise_for_status()
                data = response.json()
                
                # 添加调试信息
                logger.info(f"API响应状态: {response.status_code}")
                logger.info(f"API响应数据结构: {list(data.keys()) if data else 'None'}")
                
                # 检查响应数据
                if not data or 'prices' not in data or not data['prices']:
                    logger.warning(f"未获取到 {symbol} 的数据 - 尝试 {attempt + 1}")
                    if data:
                        logger.warning(f"响应数据: {data}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        return pd.DataFrame()
                
                # 转换为DataFrame
                prices = data['prices']
                logger.info(f"获取到 {len(prices)} 条价格数据")
                if prices:
                    logger.info(f"示例数据字段: {list(prices[0].keys())}")
                
                df = pd.DataFrame(prices)
                
                # 转换时间格式（API返回的是ISO 8601格式，不是Unix时间戳）
                if 'time' in df.columns:
                    df['Date'] = pd.to_datetime(df['time'])
                elif 'timestamp' in df.columns:
                    df['Date'] = pd.to_datetime(df['timestamp'])
                else:
                    logger.error(f"未找到时间字段，可用字段: {list(df.columns)}")
                    return pd.DataFrame()
                
                # 统一处理时区 - 移除时区信息以避免后续合并错误
                if hasattr(df['Date'].dtype, 'tz') and df['Date'].dtype.tz is not None:
                    df['Date'] = df['Date'].dt.tz_localize(None)
                
                # 重命名列以匹配原有格式
                column_mapping = {
                    'open': 'Open',
                    'high': 'High', 
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume'
                }
                df = df.rename(columns=column_mapping)
                
                # 选择需要的列，处理可能缺失的列
                required_columns = ['Date', 'Open', 'High', 'Low', 'Close']
                available_columns = [col for col in required_columns if col in df.columns]
                
                if 'Volume' in df.columns:
                    available_columns.append('Volume')
                else:
                    # 如果没有成交量数据，设置默认值
                    df['Volume'] = 0
                    available_columns.append('Volume')
                
                # 检查是否有足够的数据列
                if len(available_columns) < 5:  # 至少需要Date, Open, High, Low, Close
                    logger.error(f"缺少必要的价格数据列，可用列: {available_columns}")
                    return pd.DataFrame()
                
                df = df[available_columns]
                
                # 按日期排序
                df = df.sort_values('Date').reset_index(drop=True)
                
                # 验证数据完整性
                if len(df) == 0 or 'Close' not in df.columns:
                    logger.warning(f"获取到的 {symbol} 数据不完整 - 尝试 {attempt + 1}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        return pd.DataFrame()
                
                # 计算累计收益率
                df['Cumulative_Return'] = (df['Close'] / df['Close'].iloc[0] - 1) * 100
                
                # 计算每日收益率，处理可能的NaN值
                df['Daily_Return'] = df['Close'].pct_change() * 100
                df['Daily_Return'] = df['Daily_Return'].fillna(0)
                
                logger.info(f"成功获取 {symbol} 的 {len(df)} 条数据")
                return df
                
            except requests.exceptions.RequestException as e:
                logger.error(f"网络请求失败 {symbol} (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    st.error(f"❌ 网络请求失败 {symbol}: {str(e)}")
                    return pd.DataFrame()
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
        计算投资组合表现（改进版本，考虑持仓价值）

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

            # 计算每笔交易的现金流影响
            trades_df = trades_df.copy()
            trades_df['cash_flow'] = trades_df.apply(
                lambda row: -(row['proceeds'] + row['commission']) if row['side'] == 'BUY'
                else row['proceeds'] - row['commission'],
                axis=1
            )

            # 计算每日持仓变化
            daily_positions = self._calculate_daily_positions(trades_df)

            # 计算每日组合价值
            daily_portfolio = self._calculate_daily_portfolio_value(
                trades_df, daily_positions, initial_capital
            )

            return daily_portfolio

        except Exception as e:
            logger.error(f"计算投资组合表现失败: {str(e)}")
            return pd.DataFrame()

    def _calculate_daily_positions(self, trades_df: pd.DataFrame) -> pd.DataFrame:
        """计算每日持仓情况"""
        try:
            # 创建每日持仓记录
            position_records = []

            # 按日期分组处理交易
            for date, day_trades in trades_df.groupby(trades_df['datetime'].dt.date):
                for symbol in day_trades['symbol'].unique():
                    symbol_trades = day_trades[day_trades['symbol'] == symbol]

                    # 计算当日该标的的净持仓变化
                    net_quantity = 0
                    weighted_avg_price = 0
                    total_cost = 0

                    for _, trade in symbol_trades.iterrows():
                        quantity = trade['quantity'] if trade['side'] == 'BUY' else -trade['quantity']
                        cost = trade['proceeds'] + trade['commission']

                        net_quantity += quantity
                        total_cost += cost if trade['side'] == 'BUY' else 0

                    if net_quantity != 0:
                        weighted_avg_price = total_cost / abs(net_quantity) if total_cost > 0 else trade['price']

                    position_records.append({
                        'date': pd.to_datetime(date),
                        'symbol': symbol,
                        'quantity_change': net_quantity,
                        'avg_price': weighted_avg_price
                    })

            if not position_records:
                return pd.DataFrame()

            positions_df = pd.DataFrame(position_records)

            # 计算累计持仓
            cumulative_positions = []
            current_positions = {}

            for date in sorted(positions_df['date'].unique()):
                day_changes = positions_df[positions_df['date'] == date]

                # 更新当前持仓
                for _, change in day_changes.iterrows():
                    symbol = change['symbol']
                    if symbol not in current_positions:
                        current_positions[symbol] = {'quantity': 0, 'avg_price': 0}

                    old_qty = current_positions[symbol]['quantity']
                    new_qty_change = change['quantity_change']
                    new_qty = old_qty + new_qty_change

                    # 更新平均成本价
                    if new_qty != 0 and new_qty_change > 0:  # 买入时更新成本价
                        old_cost = old_qty * current_positions[symbol]['avg_price']
                        new_cost = new_qty_change * change['avg_price']
                        current_positions[symbol]['avg_price'] = (old_cost + new_cost) / new_qty

                    current_positions[symbol]['quantity'] = new_qty

                # 记录当日持仓
                for symbol, pos in current_positions.items():
                    if pos['quantity'] != 0:  # 只记录非零持仓
                        cumulative_positions.append({
                            'date': date,
                            'symbol': symbol,
                            'quantity': pos['quantity'],
                            'avg_price': pos['avg_price']
                        })

            return pd.DataFrame(cumulative_positions)

        except Exception as e:
            logger.error(f"计算每日持仓失败: {str(e)}")
            return pd.DataFrame()

    def _calculate_daily_portfolio_value(self, trades_df: pd.DataFrame,
                                       positions_df: pd.DataFrame,
                                       initial_capital: float) -> pd.DataFrame:
        """计算每日投资组合价值"""
        try:
            # 计算每日现金流
            daily_cash_flow = trades_df.groupby(trades_df['datetime'].dt.date)['cash_flow'].sum().reset_index()
            daily_cash_flow['datetime'] = pd.to_datetime(daily_cash_flow['datetime'])
            daily_cash_flow['cumulative_cash_flow'] = daily_cash_flow['cash_flow'].cumsum()

            # 计算每日现金余额
            daily_cash_flow['cash_balance'] = initial_capital + daily_cash_flow['cumulative_cash_flow']

            # 如果没有持仓数据，只计算现金部分
            if positions_df.empty:
                daily_cash_flow['portfolio_value'] = daily_cash_flow['cash_balance']
                daily_cash_flow['portfolio_return'] = (daily_cash_flow['portfolio_value'] / initial_capital - 1) * 100
                return daily_cash_flow[['datetime', 'portfolio_value', 'portfolio_return']]

            # 合并现金和持仓数据
            all_dates = sorted(set(daily_cash_flow['datetime'].dt.date) | set(positions_df['date'].dt.date))

            portfolio_values = []

            for date in all_dates:
                date_pd = pd.to_datetime(date)

                # 获取当日现金余额
                cash_data = daily_cash_flow[daily_cash_flow['datetime'] <= date_pd]
                cash_balance = cash_data['cash_balance'].iloc[-1] if not cash_data.empty else initial_capital

                # 获取当日持仓价值（使用最新价格作为估值）
                positions_value = 0
                date_positions = positions_df[positions_df['date'] <= date_pd]

                if not date_positions.empty:
                    # 获取每个标的的最新持仓
                    latest_positions = date_positions.groupby('symbol').last().reset_index()

                    for _, pos in latest_positions.iterrows():
                        # 使用最新交易价格作为估值价格
                        symbol_trades = trades_df[
                            (trades_df['symbol'] == pos['symbol']) &
                            (trades_df['datetime'].dt.date <= date)
                        ]

                        if not symbol_trades.empty:
                            latest_price = symbol_trades.iloc[-1]['price']
                            positions_value += pos['quantity'] * latest_price

                total_value = cash_balance + positions_value
                portfolio_return = (total_value / initial_capital - 1) * 100

                portfolio_values.append({
                    'datetime': date_pd,
                    'portfolio_value': total_value,
                    'portfolio_return': portfolio_return,
                    'cash_balance': cash_balance,
                    'positions_value': positions_value
                })

            result_df = pd.DataFrame(portfolio_values)

            # 确保时间列没有时区信息
            if hasattr(result_df['datetime'].dtype, 'tz') and result_df['datetime'].dtype.tz is not None:
                result_df['datetime'] = result_df['datetime'].dt.tz_localize(None)

            return result_df

        except Exception as e:
            logger.error(f"计算每日投资组合价值失败: {str(e)}")
            return pd.DataFrame()
    
    def calculate_performance_metrics(self, returns_series: pd.Series) -> Dict[str, float]:
        """
        计算表现指标

        Args:
            returns_series: 累计收益率序列 (百分比)

        Returns:
            Dict: 表现指标
        """
        try:
            metrics = {}

            if len(returns_series) == 0:
                return self._empty_metrics()

            # 确保数据是数值类型且处理无效值
            returns_series = pd.to_numeric(returns_series, errors='coerce').fillna(0)

            # 基础统计 - 总收益率
            metrics['total_return'] = returns_series.iloc[-1] if len(returns_series) > 0 else 0

            # 计算日收益率用于其他指标计算
            if len(returns_series) > 1:
                # 从累计收益率计算日收益率
                # 累计收益率是百分比，需要转换为小数进行计算
                cumulative_decimal = returns_series / 100  # 转换为小数

                # 计算每日收益率
                daily_returns = []
                for i in range(1, len(cumulative_decimal)):
                    prev_value = 1 + cumulative_decimal.iloc[i-1]
                    curr_value = 1 + cumulative_decimal.iloc[i]
                    daily_return = (curr_value / prev_value) - 1 if prev_value != 0 else 0
                    daily_returns.append(daily_return)

                daily_returns = pd.Series(daily_returns)
                # 过滤掉无穷大和NaN值
                daily_returns = daily_returns.replace([np.inf, -np.inf], np.nan).dropna()

                if len(daily_returns) > 0:
                    # 平均日收益率
                    metrics['avg_daily_return'] = daily_returns.mean()

                    # 年化收益率 (假设252个交易日)
                    if daily_returns.mean() > -1:  # 避免负数开方
                        metrics['annualized_return'] = ((1 + daily_returns.mean()) ** 252 - 1) * 100
                    else:
                        metrics['annualized_return'] = -100

                    # 收益率波动率 (年化，百分比)
                    metrics['volatility'] = daily_returns.std() * (252 ** 0.5) * 100

                    # 夏普比率 (假设无风险利率为2%)
                    risk_free_rate = 0.02
                    annualized_return_decimal = metrics['annualized_return'] / 100
                    volatility_decimal = metrics['volatility'] / 100

                    if volatility_decimal > 0:
                        metrics['sharpe_ratio'] = (annualized_return_decimal - risk_free_rate) / volatility_decimal
                    else:
                        metrics['sharpe_ratio'] = 0

                    # 最大回撤
                    cumulative_values = (1 + daily_returns).cumprod()
                    rolling_max = cumulative_values.expanding().max()
                    drawdown = (cumulative_values - rolling_max) / rolling_max
                    metrics['max_drawdown'] = abs(drawdown.min()) * 100  # 转换为正的百分比
                else:
                    metrics.update(self._empty_metrics())
            else:
                metrics.update(self._empty_metrics())

            return metrics

        except Exception as e:
            logger.error(f"计算表现指标失败: {str(e)}")
            return self._empty_metrics()

    def _empty_metrics(self) -> Dict[str, float]:
        """返回空的指标字典"""
        return {
            'total_return': 0,
            'avg_daily_return': 0,
            'annualized_return': 0,
            'volatility': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0
        }
    
    def get_benchmark_info(self, symbol: str) -> Dict[str, str]:
        """
        获取基准指数信息
        
        Args:
            symbol: 指数符号
            
        Returns:
            Dict: 指数信息
        """
        # 定义每个基准指数的详细信息
        detailed_info = {
            'SPY': {
                'currency': 'USD',
                'exchange': 'NYSE Arca',
                'description': 'SPDR S&P 500 ETF Trust，跟踪标普500指数的表现'
            },
            'QQQ': {
                'currency': 'USD', 
                'exchange': 'NASDAQ',
                'description': 'Invesco QQQ Trust，跟踪纳斯达克100指数的表现'
            },
            'VTI': {
                'currency': 'USD',
                'exchange': 'NYSE Arca',
                'description': 'Vanguard Total Stock Market ETF，跟踪美国整体股市表现'
            },
            'IWM': {
                'currency': 'USD',
                'exchange': 'NYSE Arca', 
                'description': 'iShares Russell 2000 ETF，跟踪罗素2000小盘股指数'
            },
            'DIA': {
                'currency': 'USD',
                'exchange': 'NYSE Arca',
                'description': 'SPDR Dow Jones Industrial Average ETF，跟踪道琼斯工业平均指数'
            },
            'VEA': {
                'currency': 'USD',
                'exchange': 'NYSE Arca',
                'description': 'Vanguard FTSE Developed Markets ETF，跟踪发达市场股票表现'
            },
            'VWO': {
                'currency': 'USD', 
                'exchange': 'NYSE Arca',
                'description': 'Vanguard FTSE Emerging Markets ETF，跟踪新兴市场股票表现'
            },
            'SPTM': {
                'currency': 'USD',
                'exchange': 'NYSE Arca',
                'description': 'SPDR Portfolio S&P 1500 Composite Stock Market ETF'
            },
            'TQQQ': {
                'currency': 'USD',
                'exchange': 'NASDAQ',
                'description': 'ProShares UltraPro QQQ，3倍杠杆追踪纳斯达克100指数'
            },
            'UPRO': {
                'currency': 'USD',
                'exchange': 'NYSE Arca', 
                'description': 'ProShares UltraPro S&P500，3倍杠杆追踪标普500指数'
            }
        }
        
        # 获取详细信息，如果不存在则使用默认值
        info = detailed_info.get(symbol, {
            'currency': 'USD',
            'exchange': 'Unknown',
            'description': f'基准指数: {symbol}'
        })
        
        return {
            'symbol': symbol,
            'name': self.BENCHMARKS.get(symbol, f"未知指数 ({symbol})"),
            'currency': info['currency'],
            'exchange': info['exchange'],
            'description': info['description']
        }
    
    def test_api_connection(self) -> bool:
        """
        测试API连接
        
        Returns:
            bool: 连接是否成功
        """
        if not self.api_key:
            return False
        
        try:
            headers = {
                'X-API-KEY': self.api_key
            }
            
            # 使用简单的请求测试连接
            import datetime
            today = datetime.date.today()
            yesterday = today - datetime.timedelta(days=10)
            
            url = (
                f'{self.BASE_URL}'
                f'?ticker=SPY'
                f'&interval=day'
                f'&interval_multiplier=1'
                f'&start_date={yesterday.strftime("%Y-%m-%d")}'
                f'&end_date={today.strftime("%Y-%m-%d")}'
            )
            
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"API连接测试失败: {str(e)}")
            return False
    
    def generate_mock_benchmark_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        生成模拟基准数据（当API不可用时使用）
        
        Args:
            symbol: 指数符号
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame: 模拟的基准指数数据
        """
        try:
            import numpy as np
            
            # 生成日期范围
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
            
            # 过滤工作日
            business_days = [d for d in date_range if d.weekday() < 5]
            
            if not business_days:
                return pd.DataFrame()
            
            # 生成模拟价格数据
            np.random.seed(42)  # 保证结果可重现
            n_days = len(business_days)
            
            # 模拟股价走势
            initial_price = 100
            daily_returns = np.random.normal(0.0005, 0.02, n_days)  # 平均日收益率0.05%，波动率2%
            prices = [initial_price]
            
            for i in range(1, n_days):
                new_price = prices[-1] * (1 + daily_returns[i])
                prices.append(new_price)
            
            # 创建DataFrame
            df = pd.DataFrame({
                'Date': business_days,
                'Open': prices,
                'High': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
                'Low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
                'Close': prices,
                'Volume': np.random.randint(1000000, 10000000, n_days)
            })
            
            # 确保日期列没有时区信息
            if hasattr(df['Date'].dtype, 'tz') and df['Date'].dtype.tz is not None:
                df['Date'] = df['Date'].dt.tz_localize(None)
            
            # 计算收益率
            df['Cumulative_Return'] = (df['Close'] / df['Close'].iloc[0] - 1) * 100
            df['Daily_Return'] = df['Close'].pct_change() * 100
            df['Daily_Return'] = df['Daily_Return'].fillna(0)
            
            logger.info(f"生成了 {symbol} 的 {len(df)} 条模拟数据")
            return df
            
        except Exception as e:
            logger.error(f"生成模拟数据失败: {str(e)}")
            return pd.DataFrame() 