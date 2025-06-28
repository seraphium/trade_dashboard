"""
IBKR Flex API 数据获取模块
"""
from ibflex import client, parser
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, Any
import yaml
import os
import re
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IBKRDataFetcher:
    """IBKR Flex API 数据获取器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """初始化数据获取器"""
        # 加载 .env 文件（如果存在）
        load_dotenv()
        
        # 尝试从 config.yaml 加载配置
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            self.config = {}
        
        # 优先级：环境变量 > .env 文件 > config.yaml > 默认值
        self.flex_token = (
            os.getenv('IBKR_FLEX_TOKEN') or  # 环境变量
            self.config.get('ibkr', {}).get('flex_token', '')  # config.yaml
        )
        self.query_id = (
            os.getenv('IBKR_QUERY_ID') or  # 环境变量
            self.config.get('ibkr', {}).get('query_id', '')  # config.yaml
        )
    
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
            logger.info(f"使用 Token: {_self.flex_token[:10]}... 和 Query ID: {_self.query_id}")
            
            # 使用 ibflex 库获取数据
            response = client.download(_self.flex_token, _self.query_id)
            
            # 尝试解析数据，如果失败则进行预处理
            try:
                trades_data = parser.parse(response)
            except Exception as parse_error:
                logger.warning(f"初始解析失败: {parse_error}")
                logger.info("尝试预处理 XML 数据...")
                
                # 预处理 XML 数据，移除可能有问题的属性
                xml_str = response.decode('utf-8') if isinstance(response, bytes) else str(response)
                
                # 移除可能导致问题的属性
                problematic_attrs = [
                    'subCategory', 'underlyingConid', 'underlyingSymbol', 
                    'underlyingSecurityID', 'underlyingListingExchange',
                    'issuer', 'issuerCountryCode', 'securityIDType',
                    'cusip', 'isin', 'figi', 'principalAdjustFactor',
                    'relatedTradeID', 'strike', 'expiry', 'putCall',
                    'dateTime', 'settleDateTarget', 'tradeMoney',
                    'netCash', 'closePrice', 'openCloseIndicator',
                    'notes', 'cost', 'fifoPnlRealized', 'mtmPnl',
                    'origTradePrice', 'origTradeDate', 'origTradeID',
                    'origOrderID', 'origTransactionID', 'clearingFirmID',
                    'ibExecID', 'relatedTransactionID', 'rtn',
                    'brokerageOrderID', 'orderReference', 'volatilityOrderLink',
                    'exchOrderId', 'extExecID', 'orderTime', 'openDateTime',
                    'holdingPeriodDateTime', 'whenRealized', 'whenReopened',
                    'levelOfDetail', 'changeInPrice', 'changeInQuantity',
                    'orderType', 'traderID', 'isAPIOrder', 'accruedInt',
                    'initialInvestment', 'serialNumber', 'deliveryType',
                    'commodityType', 'fineness', 'weight'
                ]
                
                for attr in problematic_attrs:
                    # 移除属性，但保留核心交易数据
                    pattern = f' {attr}="[^"]*"'
                    xml_str = re.sub(pattern, '', xml_str)
                
                # 重新尝试解析
                trades_data = parser.parse(xml_str.encode('utf-8'))
                logger.info("预处理后解析成功")
            
            # 检查数据结构
            if not hasattr(trades_data, 'FlexStatements') or not trades_data.FlexStatements:
                logger.warning("未找到 FlexStatements")
                st.warning("⚠️ API 响应中没有找到数据语句")
                return pd.DataFrame()
            
            # 获取第一个语句
            stmt = trades_data.FlexStatements[0]
            
            # 如果没有交易数据
            if not hasattr(stmt, 'Trades') or not stmt.Trades:
                logger.warning("未找到交易数据")
                st.warning("⚠️ 在指定时间范围内未找到交易记录")
                return pd.DataFrame()
            
            # 转换为 DataFrame
            trades_list = []
            for trade in stmt.Trades:
                # 安全地获取属性值
                trade_id = str(getattr(trade, 'tradeID', ''))
                trade_date = getattr(trade, 'tradeDate', None)
                trade_time = getattr(trade, 'tradeTime', None)
                symbol = str(getattr(trade, 'symbol', ''))
                quantity = getattr(trade, 'quantity', 0)
                trade_price = getattr(trade, 'tradePrice', 0)
                currency = str(getattr(trade, 'currency', 'USD'))
                exchange = str(getattr(trade, 'exchange', ''))
                
                # 处理买卖方向
                buy_sell = getattr(trade, 'buySell', None)
                if buy_sell and hasattr(buy_sell, 'name'):
                    side = buy_sell.name  # 'BUY' 或 'SELL'
                else:
                    # 后备方案：根据数量正负判断
                    side = 'BUY' if float(quantity) > 0 else 'SELL'
                
                # 创建日期时间
                datetime_str = None
                if trade_date and trade_time:
                    datetime_str = pd.to_datetime(f"{trade_date} {trade_time}")
                elif trade_date:
                    datetime_str = pd.to_datetime(str(trade_date))
                
                # 处理数值类型（可能是 Decimal）
                quantity_float = abs(float(quantity)) if quantity else 0
                price_float = float(trade_price) if trade_price else 0
                proceeds_float = float(getattr(trade, 'proceeds', 0))
                commission_float = float(getattr(trade, 'ibCommission', 0))
                
                trade_dict = {
                    'trade_id': trade_id,
                    'datetime': datetime_str,
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity_float,
                    'price': price_float,
                    'proceeds': proceeds_float,
                    'commission': commission_float,
                    'currency': currency,
                    'exchange': exchange,
                    'order_time': None,  # 先简化，可以后续添加
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
            error_msg = str(e)
            logger.error(f"获取交易数据失败: {error_msg}")
            
            # 详细错误分析和解决建议
            _self._show_detailed_error(error_msg)
            return pd.DataFrame()
    
    def _show_detailed_error(self, error_msg: str):
        """显示详细的错误信息和解决建议"""
        st.error(f"❌ 获取数据失败: {error_msg}")
        
        # 分析错误类型并提供建议
        if "1020" in error_msg or "Invalid request" in error_msg:
            st.error("🚨 **错误代码 1020: 请求验证失败**")
            st.markdown("""
            **可能的原因和解决方案：**
            
            1. **Flex Token 无效或过期**
               - 检查 Token 是否正确复制（不要包含空格）
               - 在 IBKR 账户管理中重新生成 Token
            
            2. **Query ID 错误**
               - 确认 Query ID 是否正确
               - 检查 Flex Query 是否为 "Active" 状态
            
            3. **Token 和 Query ID 不匹配**
               - 确保 Token 和 Query 来自同一个账户
               - 检查是否使用了正确的账户配置
            
            4. **Flex Query 配置问题**
               - 确认 Query 类型为 "Activity Flex Query"
               - 确认已勾选 "Trades" 数据部分
               - 检查 Query 的日期范围设置
            """)
            
            # 提供诊断按钮
            if st.button("🔍 运行诊断测试"):
                self._run_diagnostics()
                
        elif "network" in error_msg.lower() or "connection" in error_msg.lower():
            st.error("🌐 **网络连接问题**")
            st.info("请检查网络连接，确保能够访问 IBKR 服务器")
            
        else:
            st.error("❓ **未知错误**")
            st.info("请检查日志获取更多详细信息")
    
    def _run_diagnostics(self):
        """运行诊断测试"""
        st.subheader("🔍 诊断测试结果")
        
        # 1. 配置检查
        with st.expander("1. 配置检查", expanded=True):
            if self.flex_token:
                st.success(f"✅ Flex Token: {self.flex_token[:10]}...{self.flex_token[-4:]}")
            else:
                st.error("❌ Flex Token 未配置")
            
            if self.query_id:
                st.success(f"✅ Query ID: {self.query_id}")
            else:
                st.error("❌ Query ID 未配置")
        
        # 2. 连接测试
        with st.expander("2. API 连接测试", expanded=True):
            if self.validate_config():
                with st.spinner("正在测试连接..."):
                    try:
                        response = client.download(self.flex_token, self.query_id)
                        st.success("✅ API 连接成功")
                        
                        try:
                            data = parser.parse(response)
                            st.success("✅ 数据解析成功")
                        except Exception as parse_error:
                            st.warning(f"⚠️ 初始解析失败: {parse_error}")
                            st.info("正在尝试预处理数据...")
                            
                            # 预处理 XML 数据
                            xml_str = response.decode('utf-8') if isinstance(response, bytes) else str(response)
                            
                            # 移除可能导致问题的属性（简化版）
                            problematic_attrs = ['subCategory', 'underlyingConid', 'underlyingSymbol']
                            for attr in problematic_attrs:
                                pattern = f' {attr}="[^"]*"'
                                xml_str = re.sub(pattern, '', xml_str)
                            
                            data = parser.parse(xml_str.encode('utf-8'))
                            st.success("✅ 预处理后解析成功")
                        
                        # 检查数据内容
                        if hasattr(data, 'FlexStatements') and data.FlexStatements:
                            stmt = data.FlexStatements[0]
                            if hasattr(stmt, 'Trades') and stmt.Trades:
                                st.success(f"✅ 找到 {len(stmt.Trades)} 条交易记录")
                            else:
                                st.warning("⚠️ 未找到交易记录（可能是日期范围问题）")
                        else:
                            st.warning("⚠️ 响应中没有找到 FlexStatements")
                            
                    except Exception as conn_error:
                        st.error(f"❌ 连接失败: {conn_error}")
                        
                        # 提供具体的错误解决建议
                        error_str = str(conn_error)
                        if "1020" in error_str:
                            st.markdown("""
                            **错误 1020 解决步骤：**
                            1. 登录 IBKR 账户管理
                            2. 检查 Flex Query 状态是否为 "Active"
                            3. 重新生成 Flex Token
                            4. 确认 Query 包含 "Trades" 数据
                            """)
            else:
                st.error("❌ 配置不完整，无法进行连接测试")
    
    def get_account_summary(self) -> Dict[str, Any]:
        """获取账户概要信息"""
        try:
            response = client.download(self.flex_token, self.query_id)
            
            try:
                data = parser.parse(response)
            except Exception as parse_error:
                logger.warning(f"账户信息解析失败，尝试预处理: {parse_error}")
                
                # 预处理 XML 数据
                xml_str = response.decode('utf-8') if isinstance(response, bytes) else str(response)
                
                # 移除可能导致问题的属性
                problematic_attrs = ['subCategory', 'underlyingConid', 'underlyingSymbol']
                for attr in problematic_attrs:
                    pattern = f' {attr}="[^"]*"'
                    xml_str = re.sub(pattern, '', xml_str)
                
                data = parser.parse(xml_str.encode('utf-8'))
            
            summary = {}
            if hasattr(data, 'FlexStatements') and data.FlexStatements:
                stmt = data.FlexStatements[0]
                if hasattr(stmt, 'AccountInformation') and stmt.AccountInformation:
                    account = stmt.AccountInformation[0]  # 获取第一个账户信息
                    summary['account_id'] = getattr(account, 'accountId', 'Unknown')
                    summary['base_currency'] = getattr(account, 'currency', 'USD')
                    summary['account_type'] = getattr(account, 'accountType', 'Unknown')
                    summary['last_traded_date'] = getattr(account, 'lastTradedDate', None)
                    summary['name'] = getattr(account, 'name', 'Unknown')
            
            return summary
        except Exception as e:
            logger.error(f"获取账户信息失败: {str(e)}")
            return {}

def test_connection(token: str, query_id: str) -> tuple[bool, str]:
    """
    测试 API 连接
    
    Returns:
        tuple: (是否成功, 详细信息)
    """
    try:
        if not token or not query_id:
            return False, "Token 或 Query ID 未配置"
            
        logger.info(f"测试连接: Token={token[:10]}... Query ID={query_id}")
        response = client.download(token, query_id)
        
        try:
            data = parser.parse(response)
        except Exception as parse_error:
            logger.warning(f"初始解析失败，尝试预处理: {parse_error}")
            
            # 预处理 XML 数据
            xml_str = response.decode('utf-8') if isinstance(response, bytes) else str(response)
            
            # 移除可能导致问题的属性
            problematic_attrs = ['subCategory', 'underlyingConid', 'underlyingSymbol']
            for attr in problematic_attrs:
                pattern = f' {attr}="[^"]*"'
                xml_str = re.sub(pattern, '', xml_str)
            
            data = parser.parse(xml_str.encode('utf-8'))
        
        # 检查是否包含交易数据
        if hasattr(data, 'FlexStatements') and data.FlexStatements:
            stmt = data.FlexStatements[0]
            if hasattr(stmt, 'Trades'):
                trade_count = len(stmt.Trades) if stmt.Trades else 0
                return True, f"连接成功，找到 {trade_count} 条交易记录"
            else:
                return True, "连接成功，但未找到交易数据部分（请检查 Flex Query 配置）"
        else:
            return True, "连接成功，但响应中没有找到 FlexStatements"
            
    except Exception as e:
        error_msg = str(e)
        
        # 分析具体错误类型
        if "1020" in error_msg:
            return False, "错误 1020: Token 或 Query ID 无效，请检查配置"
        elif "1003" in error_msg:
            return False, "错误 1003: Query 未激活或不存在"
        elif "1019" in error_msg:
            return False, "错误 1019: Token 已过期，请重新生成"
        elif "network" in error_msg.lower() or "timeout" in error_msg.lower():
            return False, f"网络连接问题: {error_msg}"
        else:
            return False, f"连接失败: {error_msg}" 
