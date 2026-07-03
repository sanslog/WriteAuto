def build_generation_prompt(
    base_prompt: str,
    style_of_writing: str,
    world_outlook: str,
    outline: str,
    detailed_outline: str,
    next_node_title: str,
    main_character_design: str,
    foreshadow: str,
    context: str,
    user_input_text: str = "",
    enter_loop: bool = False,
    previous_generated_text: str = "",
) -> tuple[str, str]:
    system = f"""你是一位专业的小说作家。请根据以下设定创作小说内容。

【世界设定】
{world_outlook or "无"}

【写作风格】
{style_of_writing or "无"}

【核心要求】
- 生成小说正文时要求每一段开头以4个空格开始，作为本段段首缩进
{("- "+base_prompt) if base_prompt else ""}

你必须严格遵守以上设定进行创作。"""

    user_parts = []

    if outline:
        user_parts.append(f"【大纲】\n{outline}")

    if detailed_outline:
        user_parts.append(f"【当前节点与节点细纲】\n{detailed_outline}")

    if next_node_title:
        user_parts.append(f"【下一节点】{next_node_title}")

    if main_character_design:
        user_parts.append(f"【角色设定】\n{main_character_design}")

    if foreshadow:
        user_parts.append(f"【需要在本次生成中回收的伏笔】\n{foreshadow}")

    if context:
        user_parts.append(f"【已写内容】\n{context}")

    if enter_loop and user_input_text:
        user_parts.append(f"【修改意见】\n请根据以下意见重新修改内容：\n{user_input_text}")
        if previous_generated_text:
            user_parts.append(f"【上次生成的内容（供参考，需按要求修改）】\n{previous_generated_text[:3000]}")

    user_parts.append(
        "请根据以上所有信息，续写当前节点的章节内容。可以分多个章节，要求每章字数为2100-2300字，单次生成超过2300字数限制时进行章节拆分，并分别为每个章节取标题且每章字数不少于2000字。" \
        "每章文本内容以'第X章'为开头，X为汉字数字"
        "输出格式为纯文本，章节标题用「第X章 章节名」格式，生成章节序号请延续已写内容最后一章，如果已写内容为空则从第一章开始。"
    )

    return system, "\n\n".join(user_parts)

def build_legality_check_prompt(content: str) -> str:
    system = "你是一位内容审核专家。请判断给定的小说内容是否包含违规内容。"
    user = f"""请检查以下内容是否包含：
- 极端政治敏感内容
- 色情描写
- 暴力恐怖宣扬
- 其他违法违规内容

内容：
{content}

请返回 JSON：{{"unlawful": true/false, "reason": "违规原因（如果违规）"}}
"""
    return system, user


def build_character_state_prompt(content: str, characters: str) -> str:
    system = "你是一位文学角色分析专家。请从给定的小说内容中提取每个角色的最新状态。"
    user = f"""角色列表：
{characters}

最新章节内容：
{content}

请分析以上内容，提取每个角色在当前章节结束时的状态。
返回 JSON：{{"states": [{{"name": "角色名", "state": "状态描述", "location": "当前位置", "status_condition": "身体状况"}}]}}
"""
    return system, user
