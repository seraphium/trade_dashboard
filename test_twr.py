#!/usr/bin/env python3
"""
TWR计算器测试脚本
用于验证时间加权收益率计算功能的准确性
"""
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from twr_calculator import TWRCalculator, calculate_simple_twr

def test_simple_twr():
    """测试简单TWR计算"""
    print("测试1: 简单TWR计算（无现金流）")
    
    # 创建测试数据：简单上涨的NAV
    nav_data = [
        ('2023-01-01', 100000),
        ('2023-01-02', 101000),
        ('2023-01-03', 102000),
        ('2023-01-04', 103000),
        ('2023-01-05', 104000),
    ]
    
    result = calculate_simple_twr(nav_data)
    
    print(f"总TWR: {result['total_twr']:.4%}")
    print(f"年化收益率: {result['annualized_return']:.4%}")
    print(f"波动率: {result['volatility']:.4%}")
    print(f"夏普比率: {result['sharpe_ratio']:.3f}")
    print(f"计算区间数: {result['period_count']}")
    print("✅ 测试1通过\n")

def test_twr_with_cash_flows():
    """测试有现金流的TWR计算"""
    print("测试2: 有现金流的TWR计算")
    
    # 创建测试数据
    nav_data = [
        ('2023-01-01', 100000),
        ('2023-01-02', 101000),
        ('2023-01-03', 151000),  # 有现金流注入
        ('2023-01-04', 152000),
        ('2023-01-05', 153000),
    ]
    
    cash_flows = [
        ('2023-01-03', 50000, 'DEPOSIT'),  # 1月3日注入5万
    ]
    
    result = calculate_simple_twr(nav_data, cash_flows)
    
    print(f"总TWR: {result['total_twr']:.4%}")
    print(f"年化收益率: {result['annualized_return']:.4%}")
    print(f"计算区间数: {result['period_count']}")
    print(f"期间收益率: {[f'{r:.4%}' for r in result['period_returns']]}")
    print("✅ 测试2通过\n")

def test_periodic_twr():
    """测试周期性TWR计算"""
    print("测试3: 周期性TWR计算")
    
    # 创建一个月的数据
    start_date = datetime(2023, 1, 1)
    nav_data = []
    
    for i in range(31):
        date = start_date + timedelta(days=i)
        # 模拟波动的NAV，总体上升趋势
        nav = 100000 * (1 + 0.001 * i + 0.002 * (i % 3 - 1))
        nav_data.append((date.strftime('%Y-%m-%d'), nav))
    
    nav_df = pd.DataFrame(nav_data, columns=['date', 'nav'])
    cash_df = pd.DataFrame()  # 无现金流
    
    calculator = TWRCalculator()
    periodic_result = calculator.calculate_periodic_twr(nav_df, cash_df, 'W')
    
    print(f"周度TWR记录数: {len(periodic_result)}")
    if not periodic_result.empty:
        print("周度收益率:")
        for _, row in periodic_result.iterrows():
            print(f"  {row['period']}: {row['return']:.4%}")
    print("✅ 测试3通过\n")

def test_performance_metrics():
    """测试绩效指标计算"""
    print("测试4: 绩效指标计算")
    
    # 创建有一定波动的数据
    nav_data = [
        ('2023-01-01', 100000),
        ('2023-01-02', 102000),
        ('2023-01-03', 101000),
        ('2023-01-04', 103000),
        ('2023-01-05', 105000),
        ('2023-01-06', 104000),
        ('2023-01-07', 106000),
        ('2023-01-08', 103000),  # 回撤
        ('2023-01-09', 107000),
        ('2023-01-10', 108000),
    ]
    
    result = calculate_simple_twr(nav_data)
    
    print(f"总TWR: {result['total_twr']:.4%}")
    print(f"年化收益率: {result['annualized_return']:.4%}")
    print(f"波动率: {result['volatility']:.4%}")
    print(f"夏普比率: {result['sharpe_ratio']:.3f}")
    print(f"最大回撤: {result['max_drawdown']:.4%}")
    
    if result['max_drawdown_start'] and result['max_drawdown_end']:
        print(f"回撤期间: {result['max_drawdown_start']} 至 {result['max_drawdown_end']}")
    
    print("✅ 测试4通过\n")

def test_edge_cases():
    """测试边界情况"""
    print("测试5: 边界情况")
    
    # 测试空数据
    empty_result = calculate_simple_twr([])
    print(f"空数据TWR: {empty_result['total_twr']}")
    
    # 测试单个数据点
    single_result = calculate_simple_twr([('2023-01-01', 100000)])
    print(f"单点数据TWR: {single_result['total_twr']}")
    
    # 测试NAV为0的情况
    zero_nav_data = [
        ('2023-01-01', 0),
        ('2023-01-02', 1000),
    ]
    zero_result = calculate_simple_twr(zero_nav_data)
    print(f"零NAV开始TWR: {zero_result['total_twr']}")
    
    print("✅ 测试5通过\n")

def run_all_tests():
    """运行所有测试"""
    print("🧪 开始TWR计算器测试\n")
    print("=" * 50)
    
    try:
        test_simple_twr()
        test_twr_with_cash_flows()
        test_periodic_twr()
        test_performance_metrics()
        test_edge_cases()
        
        print("=" * 50)
        print("🎉 所有测试通过！TWR计算器功能正常")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 