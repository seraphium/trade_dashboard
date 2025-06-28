#!/usr/bin/env python3
"""
IBKR 交易复盘分析平台启动脚本
"""
import subprocess
import sys
import os
from pathlib import Path

def check_dependencies():
    """检查必要的依赖"""
    try:
        import streamlit
        import yfinance
        import pandas
        import plotly
        print("✅ 所有依赖已安装")
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        return False

def main():
    """主函数"""
    print("🚀 启动 IBKR 交易复盘分析平台...")
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查必要文件
    if not Path("app.py").exists():
        print("❌ 找不到 app.py 文件")
        sys.exit(1)
    
    # 启动 Streamlit 应用
    try:
        print("📊 启动 Streamlit 应用...")
        print("🌐 应用将在浏览器中自动打开")
        print("❌ 按 Ctrl+C 停止应用")
        print("-" * 50)
        
        subprocess.run([
            sys.executable, 
            "-m", "streamlit", 
            "run", 
            "app.py",
            "--server.port", "8501",
            "--server.address", "localhost"
        ])
    except KeyboardInterrupt:
        print("\n👋 应用已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 