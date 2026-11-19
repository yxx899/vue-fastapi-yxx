"""测试通义千问配置：在 backend 目录执行  python scripts/test_qwen.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.qwen_client import probe_qwen

if __name__ == "__main__":
    result = probe_qwen()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("ok") else 1)
