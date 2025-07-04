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


def safe_get_attr(obj, attr_name, default=None):
    """安全获取对象属性，支持多种访问方式"""
    try:
        # 方式1: 直接getattr
        return getattr(obj, attr_name, default)
    except:
        try:
            # 方式2: 如果对象有__dict__
            if hasattr(obj, '__dict__'):
                return obj.__dict__.get(attr_name, default)
        except:
            try:
                # 方式3: 如果对象是字典形式
                if hasattr(obj, '__getitem__'):
                    return obj[attr_name] if attr_name in obj else default
            except:
                pass
    return default


def safe_float(value, default=0.0):
    """安全转换为浮点数，处理None和无效值"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# IBKR XML 中可能导致解析问题的属性列表
# 这些属性在某些情况下会导致 ibflex 解析器失败，需要在预处理时移除
PROBLEMATIC_ATTRS = [
    # 基础标识符属性
    'subCategory', 'underlyingConid', 'underlyingSymbol', 
    'underlyingSecurityID', 'underlyingListingExchange',
    'issuer', 'issuerCountryCode', 'securityIDType',
    'cusip', 'isin', 'figi', 'principalAdjustFactor',
    
    # 交易相关属性
    'relatedTradeID', 'strike', 'expiry', 'putCall',
    'settleDateTarget', 'tradeMoney',
    'netCash', 'closePrice', 'openCloseIndicator',
    'notes', 'cost', 'fifoPnlRealized', 'mtmPnl',
    
    # 订单和交易ID属性
    'origTradePrice', 'origTradeDate', 'origTradeID',
    'origOrderID', 'origTransactionID', 'clearingFirmID',
    'ibExecID', 'relatedTransactionID', 'rtn',
    'brokerageOrderID', 'orderReference', 'volatilityOrderLink',
    'exchOrderId', 'extExecID', 'orderTime', 'openDateTime',
    
    # 时间和状态属性
    'holdingPeriodDateTime', 'whenRealized', 'whenReopened',
    'levelOfDetail', 'changeInPrice', 'changeInQuantity',
    'orderType', 'traderID', 'isAPIOrder', 'accruedInt',
    
    # 交易数据属性（在某些查询类型中可能有问题）
    'tradeID', 'tradePrice',
    'proceeds', 'commission', 'buySell',
    
    # 商品和投资属性
    'initialInvestment', 'serialNumber', 'deliveryType',
    'commodityType', 'fineness', 'weight'
]

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
        
        # 支持两个不同的Query ID
        self.trades_query_id = (
            os.getenv('IBKR_TRADES_QUERY_ID') or  # 环境变量
            self.config.get('ibkr', {}).get('trades_query_id', '') or  # config.yaml新格式
            self.config.get('ibkr', {}).get('query_id', '')  # config.yaml旧格式（向后兼容）
        )
        
        self.performance_query_id = (
            os.getenv('IBKR_PERFORMANCE_QUERY_ID') or  # 环境变量
            self.config.get('ibkr', {}).get('performance_query_id', '')  # config.yaml新格式
        )
    
    def validate_config(self, query_type: str = 'trades') -> bool:
        """
        验证配置是否完整
        
        Args:
            query_type: 查询类型，'trades' 或 'performance' 或 'all'
        """
        if not self.flex_token:
            return False
            
        if query_type == 'trades':
            return bool(self.trades_query_id)
        elif query_type == 'performance':
            return bool(self.performance_query_id)
        elif query_type == 'all':
            return bool(self.trades_query_id and self.performance_query_id)
        else:
            # 默认检查trades query
            return bool(self.trades_query_id)
    
    def _download_with_retry(self, token: str, query_id: str, max_retries: int = 3, delay: float = 2.0):
        """
        带重试机制的数据下载
        
        Args:
            token: Flex Token
            query_id: Query ID  
            max_retries: 最大重试次数
            delay: 重试间隔(秒)
            
        Returns:
            API响应数据
        """
        import time
        import ssl
        import urllib3
        from urllib3.exceptions import SSLError as Urllib3SSLError
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"重试获取数据，第 {attempt}/{max_retries} 次")
                    time.sleep(delay * attempt)  # 递增延时
                
                # 使用 ibflex 库获取数据
                response = client.download(token, query_id)
                logger.info("数据获取成功")
                return response
                
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                # 判断是否为网络相关错误，值得重试
                is_retryable = any([
                    "ssl" in error_str,
                    "eof occurred" in error_str,
                    "connection" in error_str,
                    "timeout" in error_str,
                    "network" in error_str,
                    "max retries exceeded" in error_str
                ])
                
                if not is_retryable or attempt >= max_retries:
                    # 不可重试的错误或达到最大重试次数
                    logger.error(f"获取数据失败 (尝试 {attempt + 1}/{max_retries + 1}): {str(e)}")
                    raise e
                else:
                    logger.warning(f"网络错误，将重试 (尝试 {attempt + 1}/{max_retries + 1}): {str(e)}")
                    
        # 如果所有重试都失败了
        raise last_error if last_error else Exception("未知错误")
    
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
        if not _self.validate_config('trades'):
            st.error("❌ 请先在 config.yaml 中配置您的 IBKR Flex Token 和 Trades Query ID")
            return pd.DataFrame()
        
        try:
            logger.info(f"正在获取交易数据: {start_date} 到 {end_date}")
            logger.info(f"使用 Token: {_self.flex_token[:10]}... 和 Trades Query ID: {_self.trades_query_id}")
            
            # 使用重试机制获取数据
            response = _self._download_with_retry(_self.flex_token, _self.trades_query_id)
            
            # 尝试解析数据，如果失败则进行预处理
            try:
                trades_data = parser.parse(response)
            except Exception as parse_error:
                logger.warning(f"初始解析失败: {parse_error}")
                logger.info("尝试预处理 XML 数据...")
                
                # 预处理 XML 数据，移除可能有问题的属性
                xml_str = response.decode('utf-8') if isinstance(response, bytes) else str(response)
                
                # 移除可能导致问题的属性
                for attr in PROBLEMATIC_ATTRS:
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
                quantity_float = abs(safe_float(quantity))
                price_float = safe_float(trade_price)
                proceeds_float = safe_float(getattr(trade, 'proceeds', 0))
                commission_float = safe_float(getattr(trade, 'ibCommission', 0))
                
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
                
        elif "network" in error_msg.lower() or "connection" in error_msg.lower() or "SSL" in error_msg or "EOF occurred" in error_msg:
            st.error("🌐 **网络连接问题**")
            st.markdown("""
            **SSL连接问题解决方案：**
            
            1. **检查网络连接**
               - 确保网络连接稳定
               - 尝试刷新页面重新获取数据
            
            2. **SSL协议问题**
               - 这是IBKR服务器SSL连接中断的常见问题
               - 通常是暂时性的，请稍等几分钟后重试
            
            3. **代理或防火墙**
               - 如果使用公司网络，可能被防火墙阻挡
               - 尝试使用不同的网络环境
            
            4. **请求频率限制**
               - IBKR可能限制了请求频率
               - 等待1-2分钟后重新尝试
            """)
            
            # 提供重试按钮
            if st.button("🔄 重新尝试获取数据", key="retry_ssl"):
                st.rerun()
            
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
                        response = self._download_with_retry(self.flex_token, self.query_id)
                        st.success("✅ API 连接成功")
                        
                        try:
                            data = parser.parse(response)
                            st.success("✅ 数据解析成功")
                        except Exception as parse_error:
                            st.warning(f"⚠️ 初始解析失败: {parse_error}")
                            st.info("正在尝试预处理数据...")
                            
                            # 预处理 XML 数据
                            xml_str = response.decode('utf-8') if isinstance(response, bytes) else str(response)
                            
                            # 使用完整的属性清理列表
                            for attr in PROBLEMATIC_ATTRS:
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
            # 优先使用performance query，如果没有则使用trades query
            query_id = self.performance_query_id or self.trades_query_id
            if not query_id:
                logger.error("未配置任何Query ID")
                return {}
            
            response = self._download_with_retry(self.flex_token, query_id)
            
            try:
                data = parser.parse(response)
            except Exception as parse_error:
                logger.warning(f"账户信息解析失败，尝试预处理: {parse_error}")
                
                # 预处理 XML 数据
                xml_str = response.decode('utf-8') if isinstance(response, bytes) else str(response)
                
                # 使用完整的属性清理列表
                for attr in PROBLEMATIC_ATTRS:
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

    @st.cache_data(ttl=3600)  # 缓存1小时
    def fetch_nav_data(_self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取每日净资产价值(NAV)数据
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            DataFrame: NAV数据，包含日期和净资产价值
        """
        if not _self.validate_config('performance'):
            st.error("❌ 请先配置 IBKR Performance Query ID")
            return pd.DataFrame()
        
        try:
            logger.info(f"正在获取NAV数据: {start_date} 到 {end_date}")
            logger.info(f"使用 Performance Query ID: {_self.performance_query_id}")
            
            # 使用重试机制获取数据
            response = _self._download_with_retry(_self.flex_token, _self.performance_query_id)
            
            # 解析数据
            try:
                nav_data = parser.parse(response)
            except Exception as parse_error:
                logger.warning(f"NAV数据解析失败，尝试预处理: {parse_error}")
                
                # 预处理 XML 数据
                xml_str = response.decode('utf-8') if isinstance(response, bytes) else str(response)
                
                # 移除可能导致问题的属性 - 但保留重要的性能数据属性
                # 注意：PROBLEMATIC_ATTRS 包含了 dateTime，但我们可能需要保留它用于某些性能数据
                # 不移除: currency, reportDate, stock, options 等重要属性
                for attr in PROBLEMATIC_ATTRS:
                    pattern = f' {attr}="[^"]*"'
                    xml_str = re.sub(pattern, '', xml_str)
                
                try:
                    nav_data = parser.parse(xml_str.encode('utf-8'))
                    logger.info("XML预处理后解析成功")
                except Exception as final_error:
                    logger.error(f"预处理后仍然解析失败: {final_error}")
                    # 如果还是失败，直接返回空数据
                    return pd.DataFrame()
            
            # 检查数据结构
            if not hasattr(nav_data, 'FlexStatements') or not nav_data.FlexStatements:
                logger.warning("未找到 FlexStatements")
                return pd.DataFrame()
            
            stmt = nav_data.FlexStatements[0]
            
            # 查找NAV数据（可能在不同节点中）
            nav_list = []
            
            # 检查 NetAssetValue 节点
            if hasattr(stmt, 'NetAssetValue') and stmt.NetAssetValue:
                for nav_item in stmt.NetAssetValue:
                    nav_dict = {
                        'reportDate': safe_get_attr(nav_item, 'reportDate', None),
                        'total': safe_get_attr(nav_item, 'total', 0),
                        'currency': safe_get_attr(nav_item, 'currency', 'USD')
                    }
                    nav_list.append(nav_dict)
            
            # 检查 EquitySummaryInBase 节点（用户数据格式）
            elif hasattr(stmt, 'EquitySummaryInBase') and stmt.EquitySummaryInBase:
                logger.info("从 EquitySummaryInBase 节点获取NAV数据")
                for equity_item in stmt.EquitySummaryInBase:
                    try:
                        # 安全获取各属性
                        stock_value = safe_float(safe_get_attr(equity_item, 'stock', 0))
                        options_value = safe_float(safe_get_attr(equity_item, 'options', 0))
                        total_nav = stock_value + options_value
                        
                        nav_dict = {
                            'reportDate': safe_get_attr(equity_item, 'reportDate', None),
                            'total': total_nav,
                            'currency': safe_get_attr(equity_item, 'currency', 'USD'),
                            'stock': stock_value,
                            'options': options_value
                        }
                        
                        logger.debug(f"处理NAV记录: {nav_dict}")
                        nav_list.append(nav_dict)
                        
                    except Exception as item_error:
                        logger.warning(f"处理单个NAV记录失败: {item_error}")
                        # 记录可用的属性以便调试
                        available_attrs = [attr for attr in dir(equity_item) if not attr.startswith('_')]
                        logger.debug(f"对象可用属性: {available_attrs}")
                        continue
            
            # 检查 EquitySummaryByReportDateInBase 节点（performance query格式）
            elif hasattr(stmt, 'EquitySummaryByReportDateInBase') and stmt.EquitySummaryByReportDateInBase:
                logger.info("从 EquitySummaryByReportDateInBase 节点获取NAV数据")
                for equity_item in stmt.EquitySummaryByReportDateInBase:
                    try:
                        # 安全获取各属性
                        stock_value = safe_float(safe_get_attr(equity_item, 'stock', 0))
                        options_value = safe_float(safe_get_attr(equity_item, 'options', 0))
                        total_nav = stock_value + options_value
                        
                        nav_dict = {
                            'reportDate': safe_get_attr(equity_item, 'reportDate', None),
                            'total': total_nav,
                            'currency': safe_get_attr(equity_item, 'currency', 'USD'),
                            'stock': stock_value,
                            'options': options_value
                        }
                        
                        logger.debug(f"处理NAV记录: {nav_dict}")
                        nav_list.append(nav_dict)
                        
                    except Exception as item_error:
                        logger.warning(f"处理单个NAV记录失败: {item_error}")
                        # 记录可用的属性以便调试
                        available_attrs = [attr for attr in dir(equity_item) if not attr.startswith('_')]
                        logger.debug(f"对象可用属性: {available_attrs}")
                        continue
            
            # 检查 MTMPerformanceSummaryInBase 节点（性能总结数据）
            elif hasattr(stmt, 'MTMPerformanceSummaryInBase') and stmt.MTMPerformanceSummaryInBase:
                logger.info("从 MTMPerformanceSummaryInBase 节点获取NAV数据")
                for mtm_item in stmt.MTMPerformanceSummaryInBase:
                    try:
                        # 从MTM数据推导NAV
                        ending_value = safe_float(safe_get_attr(mtm_item, 'endingValue', 0))
                        
                        nav_dict = {
                            'reportDate': safe_get_attr(mtm_item, 'reportDate', None),
                            'total': ending_value,
                            'currency': safe_get_attr(mtm_item, 'currency', 'USD'),
                            'stock': ending_value,  # 简化处理
                            'options': 0
                        }
                        
                        logger.debug(f"处理MTM NAV记录: {nav_dict}")
                        nav_list.append(nav_dict)
                        
                    except Exception as item_error:
                        logger.warning(f"处理单个MTM记录失败: {item_error}")
                        # 记录可用的属性以便调试
                        available_attrs = [attr for attr in dir(mtm_item) if not attr.startswith('_')]
                        logger.debug(f"MTM对象可用属性: {available_attrs}")
                        continue
            
            # 如果没有专门的NAV数据，尝试从其他节点推导
            elif hasattr(stmt, 'Trades') or hasattr(stmt, 'CashTransactions'):
                # 可以从持仓和现金数据计算NAV，这里先返回空数据
                logger.warning("未找到专门的NAV数据，需要通过其他方式计算")
                return pd.DataFrame(columns=['reportDate', 'total', 'currency', 'stock', 'options'])
            
            if not nav_list:
                logger.warning("未找到NAV数据")
                return pd.DataFrame(columns=['reportDate', 'total', 'currency', 'stock', 'options'])
            
            df = pd.DataFrame(nav_list)
            
            # 数据清理
            df['reportDate'] = pd.to_datetime(df['reportDate'])
            df['total'] = pd.to_numeric(df['total'], errors='coerce')
            
            # 按时间过滤
            if start_date:
                df = df[df['reportDate'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['reportDate'] <= pd.to_datetime(end_date)]
            
            # 排序
            df = df.sort_values('reportDate', ascending=True)
            
            logger.info(f"成功获取 {len(df)} 条NAV记录")
            return df
            
        except Exception as e:
            logger.error(f"获取NAV数据失败: {e}")
            st.error(f"❌ 获取NAV数据失败: {e}")
            return pd.DataFrame()
    
    @st.cache_data(ttl=3600)  # 缓存1小时
    def fetch_cash_transactions(_self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取现金流数据
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            DataFrame: 现金流数据
        """
        if not _self.validate_config('performance'):
            st.error("❌ 请先配置 IBKR Performance Query ID")
            return pd.DataFrame()
        
        try:
            logger.info(f"正在获取现金流数据: {start_date} 到 {end_date}")
            logger.info(f"使用 Performance Query ID: {_self.performance_query_id}")
            
            response = _self._download_with_retry(_self.flex_token, _self.performance_query_id)
            
            try:
                cash_data = parser.parse(response)
            except Exception as parse_error:
                logger.warning(f"现金流数据解析失败，尝试预处理: {parse_error}")
                
                xml_str = response.decode('utf-8') if isinstance(response, bytes) else str(response)
                
                # 移除可能导致问题的属性 - 但保留现金流相关的重要属性
                # 保留: currency, reportDate, amount, type, dateTime, activityDescription等重要属性
                # 移除XML中的换行符
                xml_str = xml_str.replace('\n', '').replace('\r', '')
                for attr in PROBLEMATIC_ATTRS:
                    pattern = f' {attr}="[^"]*"'
                    xml_str = re.sub(pattern, '', xml_str)
                
                try:
                    cash_data = parser.parse(xml_str.encode('utf-8'))
                    logger.info("现金流XML预处理后解析成功")
                except Exception as final_error:
                    logger.error(f"现金流预处理后仍然解析失败: {final_error}")
                    return pd.DataFrame()
            
            if not hasattr(cash_data, 'FlexStatements') or not cash_data.FlexStatements:
                logger.warning("未找到 FlexStatements")
                return pd.DataFrame()
            
            stmt = cash_data.FlexStatements[0]
            
            cash_list = []
            
            # 检查 CashTransactions 节点
            if hasattr(stmt, 'CashTransactions') and stmt.CashTransactions:
                logger.info(f"找到 {len(stmt.CashTransactions)} 条现金流记录")
                for cash_item in stmt.CashTransactions:
                    try:
                        report_date = safe_get_attr(cash_item, 'reportDate', None)
                        amount = safe_get_attr(cash_item, 'amount', 0)
                        cash_type = safe_get_attr(cash_item, 'type', '')
                        
                        # 如果没有dateTime，使用reportDate
                        date_time = safe_get_attr(cash_item, 'dateTime', None)
                        if not date_time and report_date:
                            date_time = report_date
                        
                        cash_dict = {
                            'reportDate': report_date,
                            'dateTime': date_time,
                            'amount': safe_float(amount),
                            'currency': safe_get_attr(cash_item, 'currency', 'USD'),
                            'type': cash_type,
                            'activityDescription': safe_get_attr(cash_item, 'activityDescription', cash_type),
                            'symbol': safe_get_attr(cash_item, 'symbol', ''),
                            'accountId': safe_get_attr(cash_item, 'accountId', ''),
                            'tradeID': safe_get_attr(cash_item, 'tradeID', '')
                        }
                        
                        logger.debug(f"处理现金流记录: {cash_dict}")
                        cash_list.append(cash_dict)
                        
                    except Exception as item_error:
                        logger.warning(f"处理单个现金流记录失败: {item_error}")
                        # 记录可用的属性以便调试
                        available_attrs = [attr for attr in dir(cash_item) if not attr.startswith('_')]
                        logger.debug(f"现金流对象可用属性: {available_attrs}")
                        continue
            
            if not cash_list:
                logger.warning("未找到现金流数据")
                return pd.DataFrame(columns=['reportDate', 'dateTime', 'amount', 'currency', 'type', 'activityDescription', 'symbol', 'accountId', 'tradeID'])
            
            df = pd.DataFrame(cash_list)
            
            # 数据清理
            df['reportDate'] = pd.to_datetime(df['reportDate'], errors='coerce')
            df['dateTime'] = pd.to_datetime(df['dateTime'], errors='coerce')
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
            
            # 按时间过滤
            if start_date:
                df = df[df['reportDate'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['reportDate'] <= pd.to_datetime(end_date)]
            
            # 排序
            df = df.sort_values('reportDate', ascending=True)
            
            logger.info(f"成功获取 {len(df)} 条现金流记录")
            return df
            
        except Exception as e:
            logger.error(f"获取现金流数据失败: {e}")
            st.error(f"❌ 获取现金流数据失败: {e}")
            return pd.DataFrame()
    
    @st.cache_data(ttl=3600)  # 缓存1小时  
    def fetch_positions(_self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取持仓数据
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            DataFrame: 持仓数据
        """
        if not _self.validate_config('performance'):
            st.error("❌ 请先配置 IBKR Performance Query ID")
            return pd.DataFrame()
        
        try:
            logger.info(f"正在获取持仓数据: {start_date} 到 {end_date}")
            logger.info(f"使用 Performance Query ID: {_self.performance_query_id}")
            
            response = _self._download_with_retry(_self.flex_token, _self.performance_query_id)
            
            try:
                pos_data = parser.parse(response)
            except Exception as parse_error:
                logger.warning(f"持仓数据解析失败，尝试预处理: {parse_error}")
                
                xml_str = response.decode('utf-8') if isinstance(response, bytes) else str(response)
                
                # 使用与NAV相同的完整属性清理列表
                for attr in PROBLEMATIC_ATTRS:
                    pattern = f' {attr}="[^"]*"'
                    xml_str = re.sub(pattern, '', xml_str)
                
                pos_data = parser.parse(xml_str.encode('utf-8'))
            
            if not hasattr(pos_data, 'FlexStatements') or not pos_data.FlexStatements:
                logger.warning("未找到 FlexStatements")
                return pd.DataFrame()
            
            stmt = pos_data.FlexStatements[0]
            
            pos_list = []
            
            # 检查 Positions 节点
            if hasattr(stmt, 'Positions') and stmt.Positions:
                for pos_item in stmt.Positions:
                    pos_dict = {
                        'reportDate': safe_get_attr(pos_item, 'reportDate', None),
                        'symbol': safe_get_attr(pos_item, 'symbol', ''),
                        'position': safe_get_attr(pos_item, 'position', 0),
                        'markPrice': safe_get_attr(pos_item, 'markPrice', 0),
                        'positionValue': safe_get_attr(pos_item, 'positionValue', 0),
                        'currency': safe_get_attr(pos_item, 'currency', 'USD'),
                        'accountId': safe_get_attr(pos_item, 'accountId', ''),
                        'assetCategory': safe_get_attr(pos_item, 'assetCategory', '')
                    }
                    pos_list.append(pos_dict)
            
            if not pos_list:
                logger.warning("未找到持仓数据")
                return pd.DataFrame(columns=['reportDate', 'symbol', 'position', 'markPrice', 'positionValue', 'currency'])
            
            df = pd.DataFrame(pos_list)
            
            # 数据清理
            df['reportDate'] = pd.to_datetime(df['reportDate'], errors='coerce')
            df['position'] = pd.to_numeric(df['position'], errors='coerce')
            df['markPrice'] = pd.to_numeric(df['markPrice'], errors='coerce')
            df['positionValue'] = pd.to_numeric(df['positionValue'], errors='coerce')
            
            # 按时间过滤
            if start_date:
                df = df[df['reportDate'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['reportDate'] <= pd.to_datetime(end_date)]
            
            # 排序
            df = df.sort_values(['reportDate', 'symbol'], ascending=True)
            
            logger.info(f"成功获取 {len(df)} 条持仓记录")
            return df
            
        except Exception as e:
            logger.error(f"获取持仓数据失败: {e}")
            st.error(f"❌ 获取持仓数据失败: {e}")
            return pd.DataFrame()

def _download_with_global_retry(token: str, query_id: str, max_retries: int = 3, delay: float = 2.0):
    """
    全局重试下载函数
    
    Args:
        token: Flex Token
        query_id: Query ID  
        max_retries: 最大重试次数
        delay: 重试间隔(秒)
        
    Returns:
        API响应数据
    """
    import time
    
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                logger.info(f"重试获取数据，第 {attempt}/{max_retries} 次")
                time.sleep(delay * attempt)  # 递增延时
            
            # 使用 ibflex 库获取数据
            response = client.download(token, query_id)
            logger.info("数据获取成功")
            return response
            
        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            
            # 判断是否为网络相关错误，值得重试
            is_retryable = any([
                "ssl" in error_str,
                "eof occurred" in error_str,
                "connection" in error_str,
                "timeout" in error_str,
                "network" in error_str,
                "max retries exceeded" in error_str
            ])
            
            if not is_retryable or attempt >= max_retries:
                # 不可重试的错误或达到最大重试次数
                logger.error(f"获取数据失败 (尝试 {attempt + 1}/{max_retries + 1}): {str(e)}")
                raise e
            else:
                logger.warning(f"网络错误，将重试 (尝试 {attempt + 1}/{max_retries + 1}): {str(e)}")
                
    # 如果所有重试都失败了
    raise last_error if last_error else Exception("未知错误")

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
        response = _download_with_global_retry(token, query_id)
        
        try:
            data = parser.parse(response)
        except Exception as parse_error:
            logger.warning(f"初始解析失败，尝试预处理: {parse_error}")
            
            # 预处理 XML 数据
            xml_str = response.decode('utf-8') if isinstance(response, bytes) else str(response)
                      
            for attr in PROBLEMATIC_ATTRS:
                pattern = f' {attr}="[^"]*"'
                xml_str = re.sub(pattern, '', xml_str)
            
            data = parser.parse(xml_str.encode('utf-8'))
        
        # 检查响应数据内容
        if hasattr(data, 'FlexStatements') and data.FlexStatements:
            stmt = data.FlexStatements[0]
            data_found = []
            
            # 检查各种数据类型
            if hasattr(stmt, 'Trades') and stmt.Trades:
                trade_count = len(stmt.Trades)
                data_found.append(f"{trade_count} 条交易记录")
            
            if hasattr(stmt, 'EquitySummaryInBase') and stmt.EquitySummaryInBase:
                nav_count = len(stmt.EquitySummaryInBase)
                data_found.append(f"{nav_count} 条NAV记录")
            
            if hasattr(stmt, 'CashTransactions') and stmt.CashTransactions:
                cash_count = len(stmt.CashTransactions)
                data_found.append(f"{cash_count} 条现金流记录")
            
            if hasattr(stmt, 'OpenPositions') and stmt.OpenPositions:
                pos_count = len(stmt.OpenPositions)
                data_found.append(f"{pos_count} 条持仓记录")
            
            if hasattr(stmt, 'MTMPerformanceSummaryInBase') and stmt.MTMPerformanceSummaryInBase:
                mtm_count = len(stmt.MTMPerformanceSummaryInBase)
                data_found.append(f"{mtm_count} 条MTM记录")
            
            if data_found:
                return True, f"连接成功，找到: {', '.join(data_found)}"
            else:
                return True, "连接成功，但未找到预期的数据部分（请检查 Flex Query 配置）"
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
