import re

_LEGACY_PREFIX = re.compile(
    r"^(\s*⚠️[^\n]*\n+|\s*【[^】]*通义千问[^】]*】\s*\n+|——\s*\n提示：[^\n]+\n+)+",
    re.MULTILINE,
)


def strip_legacy_qwen_notice(content: str | None) -> str:
    if not content:
        return content or ""
    s = content.lstrip()
    s = _LEGACY_PREFIX.sub("", s)
    mark = "【根据知识库整理】"
    idx = s.find(mark)
    if idx > 0:
        s = s[idx:]
    return s.strip()
