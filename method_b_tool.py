# Method B 工具定义：动态查询高校角色设定
import os, json
base_dir = os.path.dirname(os.path.abspath(__file__))

# 传给 SparkApi2.main() 的 functions 参数
SCHOOL_PERSONA_TOOL = {
    "plugins": [
        {
            "name": "get_school_persona",
            "description": "根据用户提到的学校简称、全称、人物姓名或昵称，查询对应高校意识体的角色设定。用于在对话中准确引用家庭成员（弟弟妹妹/兄弟姐妹）的身份、性格和关系。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "查询关键词：如'东南大学'、'瑾韵'、'二哥'、'南师'、'灿灿'、'河海'、'老四'、'工科那个'等"
                    }
                },
                "required": ["query"]
            }
        }
    ]
}

# 主角色数据文件路径
MASTER_ROLES_FILE = os.path.join(base_dir, "高校拟人角色.json")

# 类级缓存：角色索引（三重索引：学校名/人名/别名）
_ROLES_CACHE = None

def _load_roles_index():
    """从主 JSON 构建索引，缓存到模块级。"""
    global _ROLES_CACHE
    if _ROLES_CACHE is not None:
        return _ROLES_CACHE
    if not os.path.exists(MASTER_ROLES_FILE):
        _ROLES_CACHE = {}
        return _ROLES_CACHE
    try:
        with open(MASTER_ROLES_FILE, 'r', encoding='gbk', errors='ignore') as f:
            raw = f.read()
            # 修复：文件在第一个完整 JSON 数组后可能有多余内容，只取到第一个 ] 结尾
            close_idx = raw.find(']')
            if close_idx != -1:
                raw = raw[:close_idx+1]
            data = json.loads(raw)
        index = {"by_school": {}, "by_name": {}, "by_alias": {}, "items": []}
        for item in data:
            school = item.get("代表高校", "")
            name = item.get("姓名", "")
            alias = item.get("别名", "")
            index["items"].append(item)
            if school:
                index["by_school"][school] = item
            if name:
                index["by_name"][name] = item
            if alias:
                for a in alias.replace("，", ",").split(","):
                    a = a.strip()
                    if a:
                        index["by_alias"][a] = item
        _ROLES_CACHE = index
        return index
    except Exception as e:
        print(f"Load roles error: {e}")
        _ROLES_CACHE = {}
        return _ROLES_CACHE


def lookup_persona(query_text):
    """根据查询关键词，查主数据文件，返回匹配角色的摘要文本。"""
    idx = _load_roles_index()
    hits = []
    seen_ids = set()

    # 1) 精确匹配人名
    for name, item in idx["by_name"].items():
        if name == query_text or name in query_text:
            if id(item) not in seen_ids:
                seen_ids.add(id(item))
                hits.append(item)

    # 2) 别名/昵称匹配
    for alias, item in idx["by_alias"].items():
        if alias == query_text or alias in query_text or query_text in alias:
            if id(item) not in seen_ids:
                seen_ids.add(id(item))
                hits.append(item)

    # 3) 学校名匹配（包括简称）
    for school, item in idx["by_school"].items():
        if school in query_text:
            if id(item) not in seen_ids:
                seen_ids.add(id(item))
                hits.append(item)
        # 简称：取"南京XX大学"的"XX"
        short = school.replace("南京", "").replace("大学", "").replace("学院", "")
        if short and len(short) >= 2 and (short == query_text or short in query_text):
            if id(item) not in seen_ids:
                seen_ids.add(id(item))
                hits.append(item)

    if not hits:
        # 最后兜底：模糊关键匹配（查所有角色，看设定里是否包含关键词）
        for item in idx["items"]:
            setting = item.get("设定", "")
            if query_text in setting or query_text[:3] in setting:
                if id(item) not in seen_ids:
                    seen_ids.add(id(item))
                    hits.append(item)

    # 格式化结果
    lines = [f"查询 '{query_text}' 结果："]
    for item in hits[:3]:  # 最多返回3个，防止 token 爆炸
        school = item.get("代表高校", "?")
        name = item.get("姓名", "?")
        gender = item.get("性别", "?")
        setting = item.get("设定", "")
        snippet = setting[:350] + ("..." if len(setting) > 350 else "")
        lines.append(f"\n◆ {school} | {name}（{gender}）")
        lines.append(f"   设定摘要：{snippet}")

    if not hits:
        lines.append("未匹配到明确角色，请尝试更具体的学校名或人名（如'瑾韵'、'东南大学'、'南师大'）。")

    return "\n".join(lines)
