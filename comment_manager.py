"""
交易评论管理模块
"""
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import streamlit as st
import logging
import os

logger = logging.getLogger(__name__)

class CommentManager:
    """交易评论管理器"""
    
    def __init__(self, comments_file: str = "trade_comments.json"):
        """初始化评论管理器"""
        self.comments_file = comments_file
        self.comments = self.load_comments()
    
    def load_comments(self) -> Dict[str, Dict]:
        """加载已保存的评论"""
        try:
            if os.path.exists(self.comments_file):
                with open(self.comments_file, 'r', encoding='utf-8') as f:
                    comments_data = json.load(f)
                    # 转换为以 trade_id 为键的字典
                    return {item['trade_id']: item for item in comments_data}
            return {}
        except Exception as e:
            logger.error(f"加载评论失败: {str(e)}")
            return {}
    
    def save_comments(self) -> bool:
        """保存评论到文件"""
        try:
            # 转换为列表格式保存
            comments_list = list(self.comments.values())
            with open(self.comments_file, 'w', encoding='utf-8') as f:
                json.dump(comments_list, f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"成功保存 {len(comments_list)} 条评论")
            return True
        except Exception as e:
            logger.error(f"保存评论失败: {str(e)}")
            st.error(f"❌ 保存评论失败: {str(e)}")
            return False
    
    def add_comment(self, trade_id: str, comment: str, category: str = "Neutral") -> bool:
        """添加或更新评论"""
        try:
            self.comments[trade_id] = {
                'trade_id': trade_id,
                'comment': comment,
                'category': category,
                'timestamp': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            return self.save_comments()
        except Exception as e:
            logger.error(f"添加评论失败: {str(e)}")
            return False
    
    def get_comment(self, trade_id: str) -> str:
        """获取指定交易的评论"""
        return self.comments.get(trade_id, {}).get('comment', '')
    
    def get_comment_category(self, trade_id: str) -> str:
        """获取指定交易的评论分类"""
        return self.comments.get(trade_id, {}).get('category', 'Neutral')
    
    def delete_comment(self, trade_id: str) -> bool:
        """删除评论"""
        try:
            if trade_id in self.comments:
                del self.comments[trade_id]
                return self.save_comments()
            return True
        except Exception as e:
            logger.error(f"删除评论失败: {str(e)}")
            return False
    
    def merge_comments_with_trades(self, trades_df: pd.DataFrame) -> pd.DataFrame:
        """将评论合并到交易数据中"""
        if trades_df.empty:
            return trades_df
        
        # 添加评论和分类列
        trades_df['comment'] = trades_df['trade_id'].apply(self.get_comment)
        trades_df['comment_category'] = trades_df['trade_id'].apply(self.get_comment_category)
        
        return trades_df
    
    def get_comment_statistics(self) -> Dict:
        """获取评论统计信息"""
        total_comments = len(self.comments)
        categories = {}
        
        for comment_data in self.comments.values():
            category = comment_data.get('category', '一般')
            categories[category] = categories.get(category, 0) + 1
        
        return {
            'total_comments': total_comments,
            'categories': categories,
            'latest_update': max([c.get('updated_at', '') for c in self.comments.values()]) if self.comments else None
        }
    
    def export_comments_csv(self) -> str:
        """导出评论为 CSV 格式"""
        try:
            if not self.comments:
                return ""
            
            df = pd.DataFrame(list(self.comments.values()))
            return df.to_csv(index=False)
        except Exception as e:
            logger.error(f"导出评论失败: {str(e)}")
            return ""
    
    def update_category(self, trade_id: str, category: str) -> bool:
        """更新指定交易的评论分类"""
        try:
            if trade_id in self.comments:
                self.comments[trade_id]['category'] = category
                self.comments[trade_id]['updated_at'] = datetime.now().isoformat()
            else:
                # 如果评论不存在，创建一个只有分类的空评论
                self.comments[trade_id] = {
                    'trade_id': trade_id,
                    'comment': '',
                    'category': category,
                    'timestamp': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
            return self.save_comments()
        except Exception as e:
            logger.error(f"更新分类失败: {str(e)}")
            return False

    def bulk_update_comments(self, updates: Dict[str, str]) -> bool:
        """批量更新评论"""
        try:
            for trade_id, comment in updates.items():
                if comment.strip():  # 只更新非空评论
                    # 保持原有的category
                    current_category = self.get_comment_category(trade_id)
                    self.add_comment(trade_id, comment.strip(), current_category)
            return True
        except Exception as e:
            logger.error(f"批量更新评论失败: {str(e)}")
            return False

    def bulk_update_categories(self, updates: Dict[str, str]) -> bool:
        """批量更新评论分类"""
        try:
            for trade_id, category in updates.items():
                self.update_category(trade_id, category)
            return True
        except Exception as e:
            logger.error(f"批量更新分类失败: {str(e)}")
            return False 