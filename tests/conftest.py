"""Cấu hình pytest: thêm thư mục gốc repo vào sys.path để import được generation.*"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
