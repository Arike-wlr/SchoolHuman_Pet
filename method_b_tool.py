""" 工具声明 + 角色索引查询。"""
import os, json

# 主数据文件
MASTER_ROLES_FILE = os.path.join(os.path.dirname(__file__), '..', '高校拟人角色.json')

SCHOOL_PERSONA_TOOL = {
    "name": "lookup_school_persona",
    "description": "查询高校拟人角色设定：根据学校名/人名/别名查找角色数据，用于用户提到其他高校时提供准确回应。",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "查询关键词（学校名、角色名、别名或简称）"
            }
        },
        "required": ["query"]
    }
}

_roles_index_cache = None

def _load_roles_index():
    global _roles_index_cache
    if _roles_index_cache is not None:
        return _roles_index_cache
    idx = {"by_school": {}, "by_name": {}, "by_alias": {}}
    if not os.path.exists(MASTER_ROLES_FILE):
        _roles_index_cache = idx
        return idx
    try:
        with open(MASTER_ROLES_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            data = json.load(f)
        for item in data:
            school = item.get("代表高校", "")
            name = item.get("姓名", "")
            alias = item.get("别名", "")
            if school: idx["by_school"][school] = item
            if name: idx["by_name"][name] = item
            if alias:
                for a in alias.replace("，", ",").split(","):
                    a = a.strip()
                    if a: idx["by_alias"][a] = item
    except Exception:
        pass
    _roles_index_cache = idx
    return idx

def lookup_persona(query):
    """模糊匹配：返回匹配角色的摘要。"""
    idx = _load_roles_index()
    hits = []
    q = str(query).strip()
    # 直接匹配
    for k, item in idx["by_school"].items():
        if q in k or k in q:
            hits.append(item)
    for k, item in idx["by_name"].items():
        if q in k or k in q:
            hits.append(item)
    for k, item in idx["by_alias"].items():
        if q in k or k in q:
            hits.append(item)
    # 去重
    seen = set()
    unique = []
    for item in hits:
        sid = id(item)
        if sid not in seen:
            seen.add(sid)
            unique.append(item)
    if not unique:
        return f"未找到与「{q}」相关的角色信息。"
    # 提取摘要
    parts = []
    for item in unique[:2]:
        s = item.get("代表高校", "")
        n = item.get("姓名", "")
        a = item.get("别名", "")
        st = item.get("设定", "")
        snippet = st[:200] + ("..." if len(st) > 200 else "")
        parts.append(f"【{s} · {n}】别名：{a}\n设定摘要：{snippet}")
    return "\n\n".join(parts)
