"""
IBKR Flex API 数据获取模块
"""
import ibflex
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, Any
import yaml

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IBKRDataFetcher:
    """IBKR Flex API 数据获取器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """初始化数据获取器"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            st.error("❌ 配置文件 config.yaml 未找到！")
            self.config = {}
        
        self.flex_token = self.config.get('ibkr', {}).get('flex_token', '')
        self.query_id = self.config.get('ibkr', {}).get('query_id', '')
    
    def validate_config(self) -> bool:
        """验证配置是否完整"""
        if not self.flex_token or not self.query_id:
            return False
        return True
    
    @st.cache_data(ttl=3600)  # 缓存1小时
    def fetch_trades(_self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取交易数据
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            DataFrame: 交易数据
        """
        if not _self.validate_config():
            st.error("❌ 请先在 config.yaml 中配置您的 IBKR Flex Token 和 Query ID")
            return pd.DataFrame()
        
        try:
            logger.info(f"正在获取交易数据: {start_date} 到 {end_date}")
            
            # 使用 ibflex 库获取数据
            response = ibflex.download(_self.flex_token, _self.query_id)
            trades_data = ibflex.parser.parse(response)
            
            # 如果没有交易数据
            if not hasattr(trades_data, 'Trades') or not trades_data.Trades:
                logger.warning("未找到交易数据")
                return pd.DataFrame()
            
            # 转换为 DataFrame
            trades_list = []
            for trade in trades_data.Trades:
                trade_dict = {
                    'trade_id': trade.tradeID,
                    'datetime': pd.to_datetime(f"{trade.tradeDate} {trade.tradeTime}"),
                    'symbol': trade.symbol,
                    'side': 'BUY' if float(trade.quantity) > 0 else 'SELL',
                    'quantity': abs(float(trade.quantity)),
                    'price': float(trade.tradePrice),
                    'proceeds': float(trade.proceeds if hasattr(trade, 'proceeds') else 0),
                    'commission': float(trade.commission if hasattr(trade, 'commission') else 0),
                    'currency': trade.currency if hasattr(trade, 'currency') else 'USD',
                    'exchange': trade.exchange if hasattr(trade, 'exchange') else '',
                    'order_time': pd.to_datetime(f"{trade.orderTime}") if hasattr(trade, 'orderTime') else None,
                    'comment': ''  # 初始化评论列
                }
                trades_list.append(trade_dict)
            
            df = pd.DataFrame(trades_list)
            
            # 按时间过滤
            if start_date:
                df = df[df['datetime'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['datetime'] <= pd.to_datetime(end_date)]
            
            # 排序
            df = df.sort_values('datetime', ascending=False)
            
            logger.info(f"成功获取 {len(df)} 条交易记录")
            return df
            
        except Exception as e:
            logger.error(f"获取交易数据失败: {str(e)}")
            st.error(f"❌ 获取数据失败: {str(e)}")
            return pd.DataFrame()
    
    def get_account_summary(self) -> Dict[str, Any]:
        """获取账户概要信息"""
        try:
            response = ibflex.download(self.flex_token, self.query_id)
            data = ibflex.parser.parse(response)
            
            summary = {}
            if hasattr(data, 'FlexStatements') and data.FlexStatements:
                for statement in data.FlexStatements:
                    if hasattr(statement, 'AccountInformation'):
                        for account in statement.AccountInformation:
                            summary['account_id'] = account.accountId
                            summary['base_currency'] = account.baseCurrency
                            break
            
            return summary
        except Exception as e:
            logger.error(f"获取账户信息失败: {str(e)}")
            return {}

def test_connection(token: str, query_id: str) -> bool:
    """测试 API 连接"""
    try:
        response = ibflex.download(token, query_id)
        return True
    except Exception as e:
        logger.error(f"连接测试失败: {str(e)}")
        return False 