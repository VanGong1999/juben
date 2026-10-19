"""
mind_map_system 系统提示词
自动从txt文件转换生成
"""

MIND_MAP_SYSTEM_SYSTEM_PROMPT = """You are a Mind Map Expert.
Your task is to generate a mind map JSON based on the user's input.
Output format:
{
  "title": "Topic",
  "nodes": [...]
}"""

# 结构化提示词配置
MIND_MAP_SYSTEM_PROMPT_CONFIG = {
    "agent_name": "mind_map_system",
    "role": "",
    "profile": {},
    "background": "",
    "goals": [],
    "constraints": [],
    "skills": [],
    "workflows": [],
    "output_format": "",
    "definitions": {},
    "version": "2.0",
    "created_by": "prompt_converter",
    "source_file": "mind_map_system_system.txt"
}

def get_mind_map_system_system_prompt() -> str:
    """获取mind_map_system系统提示词"""
    return MIND_MAP_SYSTEM_SYSTEM_PROMPT

def get_mind_map_system_prompt_config() -> dict:
    """获取mind_map_system提示词配置"""
    return MIND_MAP_SYSTEM_PROMPT_CONFIG

# 导出主要变量
__all__ = [
    "MIND_MAP_SYSTEM_SYSTEM_PROMPT",
    "MIND_MAP_SYSTEM_PROMPT_CONFIG",
    "get_mind_map_system_system_prompt",
    "get_mind_map_system_prompt_config"
]
