"""
时间加权收益率(TWR)计算器模块
用于计算投资组合的时间加权收益率，剔除现金流影响
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging
import streamlit as st

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NAVProcessor:
    """NAV数据处理器"""
    
    @staticmethod
    def clean_nav_data(nav_df: pd.DataFrame) -> pd.DataFrame:
        """清理和预处理NAV数据"""
        if nav_df.empty:
            return nav_df
        
        nav_df = nav_df.copy()
        
        # 确保日期列为datetime类型
        if 'reportDate' in nav_df.columns:
            nav_df['date'] = pd.to_datetime(nav_df['reportDate'])
        elif 'date' in nav_df.columns:
            nav_df['date'] = pd.to_datetime(nav_df['date'])
        else:
            raise ValueError("NAV数据中缺少日期列")
        
        # 排序
        nav_df = nav_df.sort_values('date')
        
        # 处理缺失值
        if 'total' in nav_df.columns:
            nav_df['nav'] = pd.to_numeric(nav_df['total'], errors='coerce')
        elif 'nav' in nav_df.columns:
            nav_df['nav'] = pd.to_numeric(nav_df['nav'], errors='coerce')
        else:
            raise ValueError("NAV数据中缺少净资产价值列")
        
        # 前向填充缺失值
        nav_df['nav'] = nav_df['nav'].ffill()
        
        # 移除仍然为空的行
        nav_df = nav_df.dropna(subset=['nav'])
        
        return nav_df[['date', 'nav']].reset_index(drop=True)
    
    @staticmethod
    def fill_missing_dates(nav_df: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
        """填充缺失的交易日NAV数据"""
        if nav_df.empty:
            return nav_df
        
        # 创建完整的日期范围（仅工作日）
        date_range = pd.bdate_range(start=start_date, end=end_date)
        full_df = pd.DataFrame({'date': date_range})
        
        # 合并并前向填充
        result_df = full_df.merge(nav_df, on='date', how='left')
        result_df['nav'] = result_df['nav'].ffill()
        
        return result_df.dropna(subset=['nav'])

class CashFlowProcessor:
    """现金流处理器"""
    
    @staticmethod
    def clean_cash_flow_data(cf_df: pd.DataFrame) -> pd.DataFrame:
        """清理和预处理现金流数据"""
        if cf_df.empty:
            return pd.DataFrame(columns=['date', 'amount', 'type', 'description'])
        
        cf_df = cf_df.copy()
        
        # 确保日期列为datetime类型
        if 'reportDate' in cf_df.columns:
            cf_df['date'] = pd.to_datetime(cf_df['reportDate'])
        elif 'dateTime' in cf_df.columns:
            cf_df['date'] = pd.to_datetime(cf_df['dateTime']).dt.date
            cf_df['date'] = pd.to_datetime(cf_df['date'])
        elif 'date' in cf_df.columns:
            cf_df['date'] = pd.to_datetime(cf_df['date'])
        else:
            raise ValueError("现金流数据中缺少日期列")
        
        # 处理金额
        if 'amount' in cf_df.columns:
            cf_df['amount'] = pd.to_numeric(cf_df['amount'], errors='coerce')
        else:
            raise ValueError("现金流数据中缺少金额列")
        
        # 确定现金流类型
        if 'type' not in cf_df.columns:
            cf_df['type'] = cf_df.apply(CashFlowProcessor._infer_cash_flow_type, axis=1)
        else:
            # 标准化现金流类型
            cf_df['type'] = cf_df['type'].apply(CashFlowProcessor._standardize_cash_flow_type)
        
        # 添加描述并确保为字符串类型
        if 'description' not in cf_df.columns:
            cf_df['description'] = cf_df.get('activityDescription', '')

        # 确保所有字符串字段都是字符串类型，避免枚举类型导致的序列化问题
        cf_df['description'] = cf_df['description'].astype(str)
        cf_df['type'] = cf_df['type'].astype(str)

        # 处理货币转换
        if 'currency' in cf_df.columns:
            cf_df = CashFlowProcessor._convert_currency_to_usd(cf_df)

        # 去重处理：基于日期、金额、类型去重
        original_count = len(cf_df)
        cf_df = cf_df.drop_duplicates(subset=['date', 'amount', 'type'], keep='first')
        if len(cf_df) < original_count:
            logger.info(f"去重处理: 从 {original_count} 条记录减少到 {len(cf_df)} 条记录")

        # 选择需要的列，如果有currency列也保留用于调试
        columns_to_keep = ['date', 'amount', 'type', 'description']
        if 'currency' in cf_df.columns:
            columns_to_keep.append('currency')

        return cf_df[columns_to_keep].dropna(subset=['amount'])
    
    @staticmethod
    def _standardize_cash_flow_type(type_str: str) -> str:
        """标准化现金流类型"""
        type_str = str(type_str).lower()
        
        if 'dividend' in type_str:
            return 'DIVIDEND'
        elif 'interest' in type_str:
            return 'INTEREST'
        elif 'deposit' in type_str or 'wire in' in type_str:
            return 'DEPOSIT'
        elif 'withdrawal' in type_str or 'wire out' in type_str:
            return 'WITHDRAWAL'
        elif 'fee' in type_str or 'commission' in type_str:
            return 'FEE'
        else:
            return type_str.upper()
    
    @staticmethod
    def _infer_cash_flow_type(row) -> str:
        """推断现金流类型"""
        amount = row.get('amount', 0)
        description = str(row.get('activityDescription', '')).lower()
        
        if 'deposit' in description or 'wire in' in description:
            return 'DEPOSIT'
        elif 'withdrawal' in description or 'wire out' in description:
            return 'WITHDRAWAL'
        elif 'dividend' in description:
            return 'DIVIDEND'
        elif 'interest' in description:
            return 'INTEREST'
        elif 'fee' in description or 'commission' in description:
            return 'FEE'
        elif amount > 0:
            return 'CASH_IN'
        else:
            return 'CASH_OUT'
    
    @staticmethod
    def _convert_currency_to_usd(cf_df: pd.DataFrame) -> pd.DataFrame:
        """将非美元现金流转换为美元"""
        if cf_df.empty or 'currency' not in cf_df.columns:
            return cf_df

        # 简化的汇率转换（实际应用中应该使用实时汇率）
        # 这里使用近似汇率，实际应该从API获取历史汇率
        exchange_rates = {
            'USD': 1.0,
            'HKD': 0.128,  # 1 HKD ≈ 0.128 USD (近似汇率)
            'CNY': 0.14,   # 1 CNY ≈ 0.14 USD
            'EUR': 1.1,    # 1 EUR ≈ 1.1 USD
            'GBP': 1.25,   # 1 GBP ≈ 1.25 USD
            'JPY': 0.007,  # 1 JPY ≈ 0.007 USD
        }

        cf_df = cf_df.copy()

        for idx, row in cf_df.iterrows():
            currency = row.get('currency', 'USD')
            if currency != 'USD' and currency in exchange_rates:
                original_amount = row['amount']
                converted_amount = original_amount * exchange_rates[currency]
                cf_df.at[idx, 'amount'] = converted_amount

                logger.info(f"货币转换: {original_amount:.2f} {currency} -> {converted_amount:.2f} USD")
            elif currency != 'USD':
                logger.warning(f"未知货币类型: {currency}, 使用原始金额")

        return cf_df

    @staticmethod
    def filter_external_cash_flows(cf_df: pd.DataFrame) -> pd.DataFrame:
        """过滤出外部现金流（排除股息、利息等投资收益）"""
        if cf_df.empty:
            return cf_df
        
        external_types = ['DEPOSIT', 'WITHDRAWAL', 'CASH_IN', 'CASH_OUT']
        return cf_df[cf_df['type'].isin(external_types)]

class TimeSeriesProcessor:
    """时间序列处理器"""
    
    @staticmethod
    def split_periods_by_cash_flows(nav_df: pd.DataFrame, cf_df: pd.DataFrame) -> List[Dict]:
        """根据现金流将时间序列分割为子区间"""
        if nav_df.empty:
            return []
        
        # 获取现金流日期
        cf_dates = set(cf_df['date'].dt.date) if not cf_df.empty else set()
        
        # 获取所有日期并排序
        all_dates = sorted(nav_df['date'].dt.date.unique())
        
        periods = []
        start_idx = 0
        
        for i, date in enumerate(all_dates):
            if date in cf_dates or i == len(all_dates) - 1:
                # 找到现金流日期或最后一天
                end_idx = i
                if start_idx <= end_idx:
                    period_data = nav_df.iloc[start_idx:end_idx+1].copy()
                    period_cf = cf_df[cf_df['date'].dt.date == date] if date in cf_dates else pd.DataFrame()
                    
                    periods.append({
                        'start_date': all_dates[start_idx],
                        'end_date': date,
                        'nav_data': period_data,
                        'cash_flows': period_cf,
                        'has_cash_flow': date in cf_dates
                    })
                
                start_idx = i + 1 if i < len(all_dates) - 1 else i
        
        return periods

class PerformanceMetrics:
    """绩效指标计算器"""
    
    @staticmethod
    def calculate_annualized_return(total_return: float, days: int) -> float:
        """计算年化收益率"""
        if days <= 0:
            return 0

        # 处理极端情况：如果总收益率小于-100%，年化收益率无意义
        if total_return <= -1:
            return float('nan')

        try:
            base = 1 + total_return
            if base <= 0:
                return float('nan')

            annualized = (base ** (365.25 / days)) - 1

            # 检查结果是否合理
            if np.isnan(annualized) or np.isinf(annualized):
                return float('nan')

            return annualized
        except (ValueError, OverflowError, ZeroDivisionError):
            return float('nan')
    
    @staticmethod
    def calculate_volatility(returns: pd.Series, annualized: bool = True) -> float:
        """计算波动率"""
        if returns.empty:
            return 0
        
        vol = returns.std()
        if annualized:
            vol *= np.sqrt(252)  # 假设252个交易日
        return vol
    
    @staticmethod
    def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """计算夏普比率"""
        if returns.empty:
            return 0
        
        excess_returns = returns.mean() * 252 - risk_free_rate
        volatility = PerformanceMetrics.calculate_volatility(returns, annualized=True)
        
        if volatility == 0:
            return 0
        
        return excess_returns / volatility
    
    @staticmethod
    def calculate_max_drawdown(nav_series: pd.Series) -> Tuple[float, pd.Timestamp, pd.Timestamp]:
        """计算最大回撤"""
        if nav_series.empty:
            return 0, None, None
        
        # 计算累计最高点
        cummax = nav_series.expanding().max()
        
        # 计算回撤
        drawdown = (nav_series - cummax) / cummax
        
        # 找到最大回撤
        max_dd = drawdown.min()
        max_dd_end = drawdown.idxmin()
        
        # 找到最大回撤开始点
        max_dd_start = nav_series.loc[:max_dd_end].idxmax()
        
        return abs(max_dd), max_dd_start, max_dd_end

class TWRCalculator:
    """时间加权收益率计算器"""
    
    def __init__(self):
        self.nav_processor = NAVProcessor()
        self.cf_processor = CashFlowProcessor()
        self.ts_processor = TimeSeriesProcessor()
        self.metrics = PerformanceMetrics()
    
    def calculate_twr(self, nav_df: pd.DataFrame, cf_df: pd.DataFrame) -> Dict:
        """
        计算时间加权收益率
        
        Args:
            nav_df: NAV数据，包含'date'和'nav'列
            cf_df: 现金流数据，包含'date', 'amount', 'type'列
            
        Returns:
            包含TWR结果的字典
        """
        try:
            # 数据预处理
            clean_nav = self.nav_processor.clean_nav_data(nav_df)
            clean_cf = self.cf_processor.clean_cash_flow_data(cf_df)
            
            if clean_nav.empty:
                logger.warning("NAV数据为空")
                return self._empty_result()
            
            # 过滤外部现金流
            external_cf = self.cf_processor.filter_external_cash_flows(clean_cf)
            
            # 按现金流分割时间序列
            periods = self.ts_processor.split_periods_by_cash_flows(clean_nav, external_cf)

            # 调试信息：显示NAV数据范围
            logger.info(f"NAV数据范围: {clean_nav['nav'].min():.2f} 到 {clean_nav['nav'].max():.2f}")
            logger.info(f"外部现金流总数: {len(external_cf)}")
            if not external_cf.empty:
                logger.info(f"现金流金额范围: {external_cf['amount'].min():.2f} 到 {external_cf['amount'].max():.2f}")
            logger.info(f"分割后的期间数: {len(periods)}")
            
            if not periods:
                logger.warning("没有有效的时间区间")
                return self._empty_result()
            
            # 计算每个子区间的收益率
            period_returns = []
            detailed_periods = []
            
            for period in periods:
                period_result = self._calculate_period_return(period)
                period_returns.append(period_result['return'])
                detailed_periods.append(period_result)
            
            # 计算总TWR
            logger.info(f"期间收益率列表: {[f'{r:.4f}' for r in period_returns]}")
            total_twr = self._calculate_compound_return(period_returns)
            logger.info(f"计算得到的总TWR: {total_twr:.4f}")
            
            # 计算其他指标
            start_date = periods[0]['start_date']
            end_date = periods[-1]['end_date']
            days = (end_date - start_date).days
            
            annualized_return = self.metrics.calculate_annualized_return(total_twr, days)
            logger.info(f"年化收益率计算: total_twr={total_twr:.4f}, days={days}, annualized={annualized_return:.4f}")
            
            # 计算日收益率序列用于波动率计算
            daily_returns = clean_nav['nav'].pct_change().dropna()
            # 过滤掉无穷大和NaN值
            daily_returns = daily_returns.replace([np.inf, -np.inf], np.nan).dropna()
            volatility = self.metrics.calculate_volatility(daily_returns)
            sharpe_ratio = self.metrics.calculate_sharpe_ratio(daily_returns)
            max_drawdown, dd_start, dd_end = self.metrics.calculate_max_drawdown(clean_nav.set_index('date')['nav'])
            
            # 生成每日TWR时间序列
            twr_timeseries = self._generate_twr_timeseries(clean_nav, periods, detailed_periods)

            return {
                'total_twr': total_twr,
                'annualized_return': annualized_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'max_drawdown_start': dd_start,
                'max_drawdown_end': dd_end,
                'start_date': start_date,
                'end_date': end_date,
                'total_days': days,
                'period_count': len(periods),
                'period_returns': period_returns,
                'detailed_periods': detailed_periods,
                'nav_data': clean_nav,
                'twr_timeseries': twr_timeseries,  # 新增：每日TWR时间序列
                'cash_flows': clean_cf,
                'external_cash_flows': external_cf
            }
            
        except Exception as e:
            logger.error(f"TWR计算失败: {e}")
            return self._empty_result()

    def _generate_twr_timeseries(self, nav_df: pd.DataFrame, periods: List[Dict], detailed_periods: List[Dict]) -> pd.DataFrame:
        """生成每日TWR时间序列 - 基于真实NAV变化"""
        try:
            if nav_df.empty:
                return pd.DataFrame()

            # 按日期排序NAV数据
            nav_df = nav_df.sort_values('date').reset_index(drop=True)

            # 获取现金流数据
            cash_flows = {}
            for period in periods:
                if period['has_cash_flow'] and not period['cash_flows'].empty:
                    for _, cf in period['cash_flows'].iterrows():
                        cf_date = cf['date'].date()
                        if cf_date not in cash_flows:
                            cash_flows[cf_date] = 0
                        cash_flows[cf_date] += cf['amount']

            # 计算每日TWR
            twr_data = []
            cumulative_twr = 1.0  # 累计TWR倍数

            for i, (_, nav_row) in enumerate(nav_df.iterrows()):
                current_date = nav_row['date']
                current_nav = nav_row['nav']

                if i == 0:
                    # 第一天，TWR为0%
                    daily_twr_return = 0.0
                    prev_nav = current_nav
                else:
                    # 计算当日收益率
                    prev_nav = nav_df.iloc[i-1]['nav']

                    # 检查是否有现金流
                    cf_amount = cash_flows.get(current_date.date(), 0)

                    if cf_amount != 0:
                        # 有现金流的日子，需要调整计算
                        # 假设现金流发生在日末，计算调整后的收益率
                        adjusted_nav = current_nav - cf_amount
                        daily_return = (adjusted_nav - prev_nav) / prev_nav if prev_nav != 0 else 0

                        logger.debug(f"现金流调整 {current_date.date()}: "
                                   f"原NAV={current_nav:.2f}, 现金流={cf_amount:.2f}, "
                                   f"调整后NAV={adjusted_nav:.2f}, 日收益率={daily_return:.4f}")
                    else:
                        # 无现金流，正常计算日收益率
                        daily_return = (current_nav - prev_nav) / prev_nav if prev_nav != 0 else 0

                    # 更新累计TWR
                    cumulative_twr *= (1 + daily_return)
                    daily_twr_return = (cumulative_twr - 1) * 100

                twr_data.append({
                    'date': current_date,
                    'twr_return': daily_twr_return,
                    'nav': current_nav,
                    'daily_return': daily_return if i > 0 else 0,
                    'cash_flow': cash_flows.get(current_date.date(), 0)
                })

            if not twr_data:
                return pd.DataFrame()

            twr_df = pd.DataFrame(twr_data)

            logger.info(f"生成真实TWR时间序列: {len(twr_df)} 个数据点")
            logger.info(f"TWR范围: {twr_df['twr_return'].min():.2f}% 到 {twr_df['twr_return'].max():.2f}%")

            return twr_df

        except Exception as e:
            logger.error(f"生成TWR时间序列失败: {e}")
            return pd.DataFrame()
    
    def _calculate_period_return(self, period: Dict) -> Dict:
        """计算单个时间区间的收益率"""
        nav_data = period['nav_data']
        
        if len(nav_data) < 2:
            return {
                'start_date': period['start_date'],
                'end_date': period['end_date'],
                'return': 0.0,
                'start_nav': nav_data.iloc[0]['nav'] if not nav_data.empty else 0,
                'end_nav': nav_data.iloc[-1]['nav'] if not nav_data.empty else 0,
                'cash_flows': period['cash_flows'],
                'days': 0
            }
        
        start_nav = nav_data.iloc[0]['nav']
        end_nav = nav_data.iloc[-1]['nav']
        
        # 如果期间有现金流，需要调整计算
        if period['has_cash_flow'] and not period['cash_flows'].empty:
            total_cf = period['cash_flows']['amount'].sum()

            # TWR的正确计算方法：
            # 假设现金流发生在期末，我们需要计算原有资金的收益率
            #
            # 如果是入金(正现金流)：
            #   期末总NAV = 原有资金增长后的价值 + 入金金额
            #   所以：原有资金增长后的价值 = 期末总NAV - 入金金额
            #   收益率 = (原有资金增长后的价值 - 起始NAV) / 起始NAV
            #
            # 如果是出金(负现金流)：
            #   期末总NAV = 原有资金增长后的价值 - 出金金额
            #   所以：原有资金增长后的价值 = 期末总NAV + 出金金额
            #   收益率 = (原有资金增长后的价值 - 起始NAV) / 起始NAV
            #
            # 统一公式：原有资金增长后的价值 = 期末NAV - 现金流净额

            original_funds_end_value = end_nav - total_cf

            # 计算收益率，即使原有资金期末价值为负也要正确计算
            period_return = (original_funds_end_value - start_nav) / start_nav if start_nav != 0 else 0

            # 详细的现金流信息
            cf_details = []
            for _, cf_row in period['cash_flows'].iterrows():
                cf_details.append(f"{cf_row['date'].strftime('%Y-%m-%d')}: {cf_row['amount']:.2f} ({cf_row['type']})")

            logger.info(f"期间 {period['start_date']} 到 {period['end_date']}: "
                        f"起始NAV={start_nav:.2f}, 期末NAV={end_nav:.2f}, "
                        f"现金流总额={total_cf:.2f}, 原有资金期末价值={original_funds_end_value:.2f}, "
                        f"收益率={period_return:.4f}")
            logger.info(f"现金流详情: {'; '.join(cf_details)}")

            # 合理性检查
            if abs(period_return) > 5:  # 收益率超过500%，可能有问题
                logger.warning(f"期间收益率异常: {period_return:.4f}, 请检查数据")

            # 如果原有资金期末价值为负，说明投资亏损严重
            if original_funds_end_value < 0:
                logger.warning(f"原有资金期末价值为负: {original_funds_end_value:.2f}, 说明投资亏损超过本金")

        else:
            period_return = (end_nav - start_nav) / start_nav if start_nav != 0 else 0
            logger.info(f"期间 {period['start_date']} 到 {period['end_date']}: "
                        f"起始NAV={start_nav:.2f}, 期末NAV={end_nav:.2f}, "
                        f"收益率={period_return:.4f} (无现金流)")
        
        return {
            'start_date': period['start_date'],
            'end_date': period['end_date'],
            'return': period_return,
            'start_nav': start_nav,
            'end_nav': end_nav,
            'cash_flows': period['cash_flows'],
            'days': (period['end_date'] - period['start_date']).days
        }
    
    def _calculate_compound_return(self, returns: List[float]) -> float:
        """计算复合收益率"""
        if not returns:
            return 0.0
        
        compound = 1.0
        for r in returns:
            compound *= (1 + r)
        
        return compound - 1.0
    
    def calculate_periodic_twr(self, nav_df: pd.DataFrame, cf_df: pd.DataFrame, 
                              frequency: str = 'M') -> pd.DataFrame:
        """
        计算周期性TWR（月度、季度等）
        
        Args:
            nav_df: NAV数据
            cf_df: 现金流数据
            frequency: 频率 ('D', 'W', 'M', 'Q', 'Y')
            
        Returns:
            包含周期TWR的DataFrame
        """
        try:
            clean_nav = self.nav_processor.clean_nav_data(nav_df)
            clean_cf = self.cf_processor.clean_cash_flow_data(cf_df)
            
            if clean_nav.empty:
                return pd.DataFrame()
            
            # 设置日期为索引
            nav_series = clean_nav.set_index('date')['nav']
            
            # 按频率重采样
            period_starts = nav_series.resample(frequency).first()
            period_ends = nav_series.resample(frequency).last()
            
            results = []
            for period in period_starts.index:
                period_start_nav = period_starts[period]
                period_end_nav = period_ends[period]
                
                if pd.notna(period_start_nav) and pd.notna(period_end_nav) and period_start_nav != 0:
                    # 获取该期间的现金流
                    if frequency == 'M':
                        period_end_date = period + pd.offsets.MonthEnd()
                    elif frequency == 'Q':
                        period_end_date = period + pd.offsets.QuarterEnd()
                    elif frequency == 'Y':
                        period_end_date = period + pd.offsets.YearEnd()
                    else:
                        period_end_date = period + pd.DateOffset(days=1)
                    
                    period_cf = clean_cf[
                        (clean_cf['date'] >= period) & 
                        (clean_cf['date'] < period_end_date)
                    ]
                    
                    # 计算期间收益率
                    if not period_cf.empty:
                        total_cf = period_cf['amount'].sum()
                        adjusted_end_nav = period_end_nav - total_cf
                        period_return = (adjusted_end_nav - period_start_nav) / period_start_nav if period_start_nav != 0 else 0
                    else:
                        period_return = (period_end_nav - period_start_nav) / period_start_nav if period_start_nav != 0 else 0
                    
                    results.append({
                        'period': period,
                        'start_nav': period_start_nav,
                        'end_nav': period_end_nav,
                        'cash_flows': period_cf['amount'].sum() if not period_cf.empty else 0,
                        'return': period_return
                    })
            
            return pd.DataFrame(results)
            
        except Exception as e:
            logger.error(f"周期TWR计算失败: {e}")
            return pd.DataFrame()
    
    def _empty_result(self) -> Dict:
        """返回空结果"""
        return {
            'total_twr': 0.0,
            'annualized_return': 0.0,
            'volatility': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'max_drawdown_start': None,
            'max_drawdown_end': None,
            'start_date': None,
            'end_date': None,
            'total_days': 0,
            'period_count': 0,
            'period_returns': [],
            'detailed_periods': [],
            'nav_data': pd.DataFrame(),
            'cash_flows': pd.DataFrame(),
            'external_cash_flows': pd.DataFrame()
        }

# 便利函数
def calculate_simple_twr(nav_data: List[Tuple], cash_flows: List[Tuple] = None) -> Dict:
    """
    简化的TWR计算接口
    
    Args:
        nav_data: [(date, nav_value), ...] 
        cash_flows: [(date, amount, type), ...]
        
    Returns:
        TWR计算结果
    """
    nav_df = pd.DataFrame(nav_data, columns=['date', 'nav'])
    
    if cash_flows:
        cf_df = pd.DataFrame(cash_flows, columns=['date', 'amount', 'type'])
    else:
        cf_df = pd.DataFrame()
    
    calculator = TWRCalculator()
    return calculator.calculate_twr(nav_df, cf_df) 