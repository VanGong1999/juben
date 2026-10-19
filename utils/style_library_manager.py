"""
风格库管理器
支持按分类存储剧本对白片段，为 Agent 提供 Few-shot 示例

功能：
1. 支持多种风格分类（悬疑、喜剧、古装、现代、爱情等）
2. 存储 user/assistant 对话示例
3. 根据风格标签检索匹配示例
4. 支持 Redis 持久化
5. 支持动态添加和更新示例

代码作者：宫灵瑞
创建时间：2026年2月7日
"""
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import random


class ScriptStyle(Enum):
    """剧本风格枚举"""
    SUSPENSE = "suspense"           # 悬疑
    COMEDY = "comedy"               # 喜剧
    PERIOD = "period"               # 古装
    MODERN = "modern"               # 现代
    ROMANCE = "romance"             # 爱情
    THRILLER = "thriller"           # 惊悚
    FANTASY = "fantasy"             # 奇幻
    SCIFI = "scifi"                 # 科幻
    HORROR = "horror"               # 恐怖
    DRAMA = "drama"                 # 剧情
    ACTION = "action"               # 动作
    HISTORICAL = "historical"       # 历史
    WUXIA = "wuxia"                 # 武侠
    XIANXIA = "xianxia"             # 仙侠
    URBAN = "urban"                 # 都市
    SLAPSTICK = "slapstick"         # 滑稽
    EMOTIONAL = "emotional"         # 情感
    MYSTERY = "mystery"             # 悬疑推理
    FAMILY = "family"               # 家庭
    YOUTH = "youth"                 # 青春


@dataclass
class StyleExample:
    """风格示例数据类"""
    style: ScriptStyle
    user_input: str
    assistant_output: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    quality_score: float = 1.0
    created_at: str = field(default_factory=str)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "style": self.style.value,
            "user_input": self.user_input,
            "assistant_output": self.assistant_output,
            "metadata": self.metadata,
            "tags": self.tags,
            "quality_score": self.quality_score,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StyleExample":
        """从字典创建"""
        return cls(
            style=ScriptStyle(data.get("style", ScriptStyle.MODERN.value)),
            user_input=data.get("user_input", ""),
            assistant_output=data.get("assistant_output", ""),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
            quality_score=data.get("quality_score", 1.0),
            created_at=data.get("created_at", "")
        )


class StyleLibraryManager:
    """
    风格库管理器

    负责：
    1. 存储和管理风格示例
    2. 根据风格标签检索示例
    3. 支持 Few-shot 学习
    4. 提供 Redis 持久化
    """

    # 内置风格库示例
    BUILT_IN_EXAMPLES = {
        ScriptStyle.SUSPENSE: [
            StyleExample(
                style=ScriptStyle.SUSPENSE,
                user_input="生成一段悬疑对话",
                assistant_output="""【场景：深夜办公室】

李明（盯着电脑屏幕，声音颤抖）："不对...这些数字不对。"

同事小王（凑过来）："什么不对？"

李明（猛地抬头，眼神惊恐）："有人篡改了数据。而且...篡改的时间就在刚才，在我们都在开会的时候。"

小王（脸色苍白）："你是说...我们中间有内鬼？"

李明（压低声音）:"不止如此。我查了访问记录，登录的IP地址...就在这间办公室。"

【窗外一道闪电划过，两人面面相觑】""",
                tags=["悬念", "内鬼", "办公室"],
                metadata={"scene": "office", "mood": "tense"}
            ),
            StyleExample(
                style=ScriptStyle.SUSPENSE,
                user_input="设计一个悬疑开场",
                assistant_output="""【第1集 夜 - 废弃医院】

（镜头从黑暗中缓缓推进）

陈默（手持手电筒，声音沙哑）："传说十年前，这家医院发生过一起离奇的患者失踪案..."

助理小林（紧握记录本）："主编，我们真的要在这里过夜吗？"

陈默（脚步突然停止，手电指向墙角）："小林，你看。"

（手电光束下，墙上有新鲜的抓痕）

小林（声音发抖）："这...这是刚弄出来的？"

陈默（脸色凝重）："而且...血迹还是湿的。"

（镜头突然拉远，黑暗深处传来一声低笑）【片头曲起】""",
                tags=["开场", "废弃场景", "恐怖氛围"],
                metadata={"scene": "hospital", "mood": "scary"}
            ),
        ],
        ScriptStyle.COMEDY: [
            StyleExample(
                style=ScriptStyle.COMEDY,
                user_input="写一段搞笑对话",
                assistant_output="""【场景：相亲餐厅】

男："其实我这个人最大的优点就是...特别会省钱。"

女（眼睛一亮）："真的吗？怎么个省法？"

男（自豪地）:"你看，今天这顿饭...AA吧？"

女（笑容僵住）："啊？"

男（掏出计算器）:"你吃了108块，我吃了96块，你多吃了12块...你看微信还是支付宝？"

女（淡定地叫来服务员）:"服务员，给我打包...把他那份也打包了。"

男："诶？那是我的饭...""
女（微笑）:"AA嘛，我付我那份，你的给我带走。"

【男一脸懵逼】""",
                tags=["相亲", "AA制", "反讽"],
                metadata={"scene": "restaurant", "mood": "humorous"}
            ),
            StyleExample(
                style=ScriptStyle.COMEDY,
                user_input="设计喜剧冲突",
                assistant_output="""【场景：面试现场】

面试官（翻简历）:"你毕业于..."

求职者（自信）:"哈佛大学！"

面试官（惊喜）:"哇！哈佛！哪个专业？"

求职者:"哈佛幼儿园...隔壁小区的。"

面试官（笑容凝固）:"..."

求职者（继续）:"不过我后来去了剑桥！"

面试官（重新燃起希望）:"剑桥大学？"

求职者:"剑桥英语培训班...三个月速成班。"

面试官（深吸一口气）:"你先出去。"

求职者（回头）:"等等，我还有斯坦福的经历！"

面试官:"..."

求职者:"斯坦福健身房办的卡。"

【面试官倒地】""",
                tags=["面试", "误会", "反转"],
                metadata={"scene": "interview", "mood": "funny"}
            ),
        ],
        ScriptStyle.PERIOD: [
            StyleExample(
                style=ScriptStyle.PERIOD,
                user_input="写古装对话",
                assistant_output="""【场景：御书房】

李公公（躬身）:"启禀陛下，江南巡抚王大人求见。"

皇帝（放下奏折）:"王爱卿？让他进来。"

（王大人步入，跪拜）

王大人（叩首）:"臣王有财，叩见皇上！吾皇万岁万岁万万岁！"

皇帝（抬手）:"王爱卿平身。江南水患，赈灾银两可曾发放？"

王大人（犹豫）:"这...臣正要启奏。银两已发，然..."

皇帝（眉头微蹙）:"然何？"

王大人（硬着头皮）:"然运输途中遭遇水匪，银两...遗失大半。"

皇帝（目光凌厉）:"遗失大半？王爱卿，你可知欺君之罪？"

王大人（冷汗直流）:"臣...臣不敢！臣愿戴罪立功，追回银两！"

皇帝（冷笑）:"朕给你三日。若追不回...你就提头来见吧。"

【王大人瘫软在地】""",
                tags=["宫廷", "奏折", "危机"],
                metadata={"scene": "royal_court", "era": "qing"}
            ),
            StyleExample(
                style=ScriptStyle.PERIOD,
                user_input="写武侠江湖场景",
                assistant_output="""【场景：破庙雨夜】

（电闪雷鸣，大雨倾盆）

（一道黑影闪入庙中）

神秘人（抱剑而立，气息微弱）:"呼...好险...差点就追上了..."

（另一道身影飘然而至）

白衣剑客（冷笑）:"欧阳锋，你逃不掉的。"

欧阳锋（强撑站起）:"东方不败！你怎么会在这里？"

东方不败（轻抚绣花针）:"屠龙刀在你手中，我岂能不来？"

欧阳锋（咬牙）:"想要屠龙刀？先问过我手中的蛇杖！"

（两人对峙，气氛剑拔弩张）

（角落里，一个少年默默观察）

少年（心想）:"两大高手决斗...我的机会来了..."

【少年眼中闪过精光】""",
                tags=["武侠", "决斗", "宝物"],
                metadata={"scene": "temple", "mood": "tense"}
            ),
        ],
        ScriptStyle.MODERN: [
            StyleExample(
                style=ScriptStyle.MODERN,
                user_input="现代都市对话",
                assistant_output="""【场景：咖啡厅】

（林晓晓低头刷手机，眉头紧锁）

陈默（放下咖啡）:"还在想工作的事？"

林晓晓（叹气）:"别提了，老板让我明天之前交方案，可是...一点头绪都没有。"

陈默（轻笑）:"你就是太追求完美了。有时候，差不多就行了。"

林晓晓（抬头）:"你说得轻巧！这项目关系到我的晋升..."

陈默:"所以更需要放松。来，我给你讲个笑话。"

林晓晓:"现在？"

陈默:"对，心情好了，灵感自然就来了。"

（林晓晓破涕为笑）

林晓晓:"行，那你讲啊。"

陈默:"从前有个人..."

【镜头拉远，阳光透过窗户洒进来】""",
                tags=["职场", "压力", "温暖"],
                metadata={"scene": "cafe", "mood": "relaxed"}
            ),
        ],
        ScriptStyle.ROMANCE: [
            StyleExample(
                style=ScriptStyle.ROMANCE,
                user_input="写爱情对话",
                assistant_output="""【场景：日落海滩】

（海浪轻拍沙滩，两人并肩而坐）

（夕阳将天空染成橘红色）

江阳（侧头）:"你知道吗？从小到大，我最喜欢看日落。"

林小溪（微笑）:"为什么？"

江阳:"因为日落提醒我，即使是最灿烂的一天，也会结束。但...第二天太阳还会升起。"

林小溪（若有所思）:"你是说...无论遇到什么困难，都会过去？"

江阳:"嗯。而且...日落虽美，但身边有个人陪着看，才是最好的。"

（林小溪脸颊微红）

林小溪:"你...总是这么会说。"

江阳（握住她的手）:"只对你一个人说。"

（两人相视而笑）

【海风吹过，发丝飞舞】""",
                tags=["表白", "浪漫", "海边"],
                metadata={"scene": "beach", "mood": "romantic"}
            ),
        ],
        ScriptStyle.WUXIA: [
            StyleExample(
                style=ScriptStyle.WUXIA,
                user_input="写武侠对话",
                assistant_output="""【场景：华山之巅】

（狂风呼啸，两人立于崖边）

叶孤城（白衣飘飘，剑指苍天）:"西门吹雪，今日一决，不死不休！"

西门吹雪（面无表情，剑已出鞘）:"请。"

（两人同时跃起，剑气纵横）

（乒乒乓乓数百招过后）

叶孤城（喘息）:"好剑法！十年不见，你进步神速！"

西门吹雪（淡淡）:"你也不差。可惜...你的破绽还是太明显。"

叶孤城（大笑）:"破绽？在哪里？"

西门吹雪（剑尖一指）:"你的心里，还有放不下的人。"

叶孤城（愣住）:"..."

西门吹雪:"剑道无情，你做不到无情，所以...你输了。"

叶孤城（苦笑）:"也许吧。但这...正是我所追求的。"

【两人收剑，相互致敬】""",
                tags=["决斗", "剑法", "人生哲理"],
                metadata={"scene": "mountain", "mood": "epic"}
            ),
        ],
        ScriptStyle.EMOTIONAL: [
            StyleExample(
                style=ScriptStyle.EMOTIONAL,
                user_input="写情感对话",
                assistant_output="""【场景：医院病房】

（阳光透过窗帘洒进病房）

（老张躺在病床上，脸色苍白）

小张（握着父亲的手）:"爸，医生说...明天就可以出院了。"

老张（微笑，虚弱）:"嗯...终于可以回家了。"

小张（眼眶泛红）:"爸，对不起...这些年，我一直忙着工作，很少陪您..."

老张（轻轻拍儿子的手）:"傻孩子，说什么呢。你有你的事业，爸理解。"

小张（哽咽）:"可是...您的身体..."

老张:"人生嘛，总有遗憾。但看到你现在过得好，爸就知足了。"

小张:"以后...我会多陪陪您的。我们一起去钓鱼，去旅行..."

老张（欣慰地笑）:"好...爸等着。"

【阳光温暖，父子情深】""",
                tags=["父子", "遗憾", "温暖"],
                metadata={"scene": "hospital", "mood": "touching"}
            ),
        ],
    }

    def __init__(self):
        from utils.logger import JubenLogger
        self.logger = JubenLogger("StyleLibraryManager")
        self._redis_client = None

        # 加载内置示例
        self.examples: Dict[str, List[StyleExample]] = {}
        self._load_builtin_examples()

    def _load_builtin_examples(self):
        """加载内置示例"""
        for style, examples in self.BUILT_IN_EXAMPLES.items():
            self.examples[style.value] = examples.copy()

        self.logger.info(f"📚 加载内置风格示例: {len(self.examples)} 种风格")

    async def _get_redis(self):
        """获取 Redis 客户端"""
        if self._redis_client is None:
            try:
                from utils.redis_client import get_redis_client
                self._redis_client = await get_redis_client()
            except Exception as e:
                self.logger.warning(f"Redis 客户端初始化失败: {e}")
        return self._redis_client

    def _get_style_key(self, style: str) -> str:
        """获取风格存储键"""
        return f"style:library:{style}"

    async def load_from_redis(self) -> bool:
        """
        从 Redis 加载自定义示例

        Returns:
            bool: 是否成功
        """
        try:
            redis_client = await self._get_redis()
            if not redis_client:
                return False

            # 遍历所有风格
            for style in ScriptStyle:
                key = self._get_style_key(style.value)
                data = await redis_client.get(key)

                if data:
                    examples = []
                    if isinstance(data, list):
                        for item in data:
                            examples.append(StyleExample.from_dict(item))
                    else:
                        examples.append(StyleExample.from_dict(data))

                    # 合并到内置示例
                    if style.value not in self.examples:
                        self.examples[style.value] = []
                    self.examples[style.value].extend(examples)

            self.logger.info("✅ 从 Redis 加载风格库成功")
            return True

        except Exception as e:
            self.logger.error(f"从 Redis 加载失败: {e}")
            return False

    async def save_to_redis(self) -> bool:
        """
        保存自定义示例到 Redis

        Returns:
            bool: 是否成功
        """
        try:
            redis_client = await self._get_redis()
            if not redis_client:
                return False

            # 保存每个风格的示例
            for style, examples in self.examples.items():
                key = self._get_style_key(style)
                data = [ex.to_dict() for ex in examples]
                await redis_client.set(key, data, expire=30 * 24 * 3600)  # 30天

            self.logger.info("💾 保存风格库到 Redis 成功")
            return True

        except Exception as e:
            self.logger.error(f"保存到 Redis 失败: {e}")
            return False

    async def add_example(self, example: StyleExample) -> bool:
        """
        添加风格示例

        Args:
            example: 风格示例

        Returns:
            bool: 是否成功
        """
        try:
            style = example.style.value
            if style not in self.examples:
                self.examples[style] = []

            self.examples[style].append(example)

            # 异步保存到 Redis
            asyncio.create_task(self.save_to_redis())

            self.logger.info(f"➕ 添加风格示例: {style}")
            return True

        except Exception as e:
            self.logger.error(f"添加示例失败: {e}")
            return False

    def get_examples_by_style(
        self,
        style: str,
        count: int = 3,
        tags: List[str] = None,
        min_quality: float = 0.0
    ) -> List[StyleExample]:
        """
        根据风格获取示例

        Args:
            style: 风格名称
            count: 返回数量
            tags: 标签筛选
            min_quality: 最低质量分数

        Returns:
            List[StyleExample]: 示例列表
        """
        try:
            # 如果风格不存在，返回空列表
            if style not in self.examples:
                self.logger.warning(f"风格不存在: {style}")
                return []

            examples = self.examples[style]

            # 标签筛选
            if tags:
                examples = [
                    ex for ex in examples
                    if any(tag in ex.tags for tag in tags)
                ]

            # 质量筛选
            if min_quality > 0:
                examples = [ex for ex in examples if ex.quality_score >= min_quality]

            # 随机选择
            if len(examples) > count:
                examples = random.sample(examples, count)

            return examples

        except Exception as e:
            self.logger.error(f"获取示例失败: {e}")
            return []

    def get_examples_by_styles(
        self,
        styles: List[str],
        count_per_style: int = 2
    ) -> List[StyleExample]:
        """
        根据多个风格获取示例

        Args:
            styles: 风格列表
            count_per_style: 每个风格返回数量

        Returns:
            List[StyleExample]: 示例列表
        """
        all_examples = []

        for style in styles:
            examples = self.get_examples_by_style(style, count_per_style)
            all_examples.extend(examples)

        return all_examples

    def parse_style_from_input(self, input_data: Dict[str, Any]) -> List[str]:
        """
        从输入数据中解析风格标签

        Args:
            input_data: 输入数据

        Returns:
            List[str]: 风格列表
        """
        styles = []

        # 直接从 style 字段获取
        if "style" in input_data:
            style_value = input_data["style"]
            if isinstance(style_value, str):
                styles.append(style_value)
            elif isinstance(style_value, list):
                styles.extend(style_value)

        # 从 input 文本中推断
        if "input" in input_data:
            text = input_data["input"]
            text_lower = text.lower()

            # 风格关键词映射
            style_keywords = {
                ScriptStyle.SUSPENSE.value: ["悬疑", "推理", "惊悚", "侦探", "破案"],
                ScriptStyle.COMEDY.value: ["喜剧", "搞笑", "幽默", "轻松", "有趣"],
                ScriptStyle.PERIOD.value: ["古装", "古代", "宫廷", "武侠", "历史"],
                ScriptStyle.MODERN.value: ["现代", "都市", "职场", "城市"],
                ScriptStyle.ROMANCE.value: ["爱情", "浪漫", "表白", "情侣"],
                ScriptStyle.WUXIA.value: ["武侠", "江湖", "功夫", "剑客"],
                ScriptStyle.XIANXIA.value: ["仙侠", "修仙", "宗门", "法术"],
                ScriptStyle.EMOTIONAL.value: ["感人", "情感", "催泪", "温暖"],
                ScriptStyle.HORROR.value: ["恐怖", "惊悚", "鬼", "灵异"],
                ScriptStyle.FANTASY.value: ["奇幻", "魔法", "异世界"],
            }

            for style, keywords in style_keywords.items():
                if any(kw in text_lower for kw in keywords):
                    if style not in styles:
                        styles.append(style)

        # 如果没有找到风格，使用默认
        if not styles:
            styles.append(ScriptStyle.MODERN.value)

        return styles

    def format_examples_as_messages(
        self,
        examples: List[StyleExample]
    ) -> List[Dict[str, str]]:
        """
        将示例格式化为消息对

        Args:
            examples: 示例列表

        Returns:
            List[Dict]: 消息列表
        """
        messages = []

        for example in examples:
            # 添加用户消息
            messages.append({
                "role": "user",
                "content": example.user_input
            })

            # 添加助手消息
            messages.append({
                "role": "assistant",
                "content": example.assistant_output
            })

        return messages

    async def get_fewshot_messages(
        self,
        input_data: Dict[str, Any],
        count: int = 2
    ) -> List[Dict[str, str]]:
        """
        获取 Few-shot 消息（便捷方法）

        Args:
            input_data: 输入数据
            count: 每个风格的示例数量

        Returns:
            List[Dict]: 消息列表
        """
        # 解析风格
        styles = self.parse_style_from_input(input_data)

        # 获取示例
        examples = self.get_examples_by_styles(styles, count_per_style=count)

        # 格式化为消息
        return self.format_examples_as_messages(examples)

    def get_available_styles(self) -> List[str]:
        """获取可用的风格列表"""
        return list(self.examples.keys())

    def get_style_info(self, style: str) -> Dict[str, Any]:
        """
        获取风格信息

        Args:
            style: 风格名称

        Returns:
            Dict: 风格信息
        """
        if style not in self.examples:
            return {"exists": False}

        examples = self.examples[style]
        return {
            "exists": True,
            "example_count": len(examples),
            "tags": list(set([tag for ex in examples for tag in ex.tags])),
            "avg_quality": sum(ex.quality_score for ex in examples) / len(examples)
        }


# ==================== 全局实例 ====================

_style_library_manager: Optional[StyleLibraryManager] = None


async def get_style_library_manager() -> StyleLibraryManager:
    """获取风格库管理器实例（单例模式）"""
    global _style_library_manager
    if _style_library_manager is None:
        _style_library_manager = StyleLibraryManager()
        await _style_library_manager.load_from_redis()
    return _style_library_manager


def get_style_library_manager_sync() -> StyleLibraryManager:
    """获取风格库管理器实例（同步版本，用于非异步上下文）"""
    global _style_library_manager
    if _style_library_manager is None:
        _style_library_manager = StyleLibraryManager()
    return _style_library_manager


# ==================== 便捷函数 ====================

async def get_style_examples(
    input_data: Dict[str, Any],
    count: int = 2
) -> List[Dict[str, str]]:
    """
    获取风格示例（便捷函数）

    Args:
        input_data: 输入数据
        count: 每个风格的示例数量

    Returns:
        List[Dict]: 消息列表
    """
    manager = await get_style_library_manager()
    return await manager.get_fewshot_messages(input_data, count)
