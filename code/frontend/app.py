"""
Simple LangGraph Client - A Streamlit interface for LangGraph assistants.

This application provides a clean web interface for interacting with LangGraph
assistants, featuring streaming responses, reasoning tags, and debug information.

IMPORTANT: Before running this client, you MUST start the LangGraph API server:
    1. Open a new terminal
    2. cd code/2-agentic-rag
    3. Run: langgraph dev
    4. Wait for "Ready accept requests at http://127.0.0.1:2024"
    5. Then run this client in another terminal: streamlit run simple_client.py

See .devx/2-agentic-rag/running.md for more details.
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import httpx
import streamlit as st
import streamlit.components.v1 as components
from langgraph_sdk import get_sync_client

# 获取项目根目录（更稳健的方式）
APP_PATH = Path(__file__).resolve()  # 获取绝对路径
PROJECT_ROOT = APP_PATH.parent.parent.parent  # 往上 3 层到项目根目录

# 配置 logging
LOG_DIR = PROJECT_ROOT / "storage" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 配置根 logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            LOG_DIR / f"frontend_{datetime.now().strftime('%Y%m%d')}.log",
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)

_LOGGER = logging.getLogger(__name__)

# 打印路径信息帮助调试
_LOGGER.info(f"APP_PATH: {APP_PATH}")
_LOGGER.info(f"PROJECT_ROOT: {PROJECT_ROOT}")
_LOGGER.info(f"LOG_DIR: {LOG_DIR}")

# 定义历史记录存储目录
HISTORY_DIR = PROJECT_ROOT / "storage" / "chat_history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)
_LOGGER.info(f"HISTORY_DIR: {HISTORY_DIR}")

# ==============================================================================
# 配置和初始化
# ==============================================================================

# LangGraph API 服务器地址，默认本地地址
BASE_URL = os.getenv("LANGGRAPH_API_URL", "http://127.0.0.1:2024")

# 创建同步客户端，用于与 LangGraph API 通信
CLIENT = get_sync_client(url=BASE_URL)


# ==============================================================================
# 历史记录持久化函数
# ==============================================================================
# Sample history. File name: ff3a3c700-082d-430e-a045-335f8011b3cc.json
# [
#   {
#     "role": "user",
#     "content": "what time is it?"
#   },
#   {
#     "role": "ai",
#     "content": "",
#     "name": null,
#     "think": "The user is asking what time it is. This is a simple question about the current time. I don't have access to a real-time clock tool, but I can use web search to get the current time. However, I should consider if this is something I can answer without tools. Since I don't have a built-in clock, I need to use web search to get the current time. Let me use web search for \"current time\".\n"
#   },
#   {
#     "role": "tool",
#     "content": "{\"query\":\"current time\",\"follow_up_questions\":null,\"answer\":null,\"images\":[],\"results\":[{\"url\":\"https://www.checktimes.com/world/north_america/us/indiana/flat_rock\",\"title\":\"Current Time in , Indiana | Timezone and Date in IN. USA\",\"content\":\"Current Time in , IN. 02:45:28. AM. EDT. Thursday, May 7, 2026. Date and Time Info. Current Timezone. \\\"EDT\\\" Eastern Daylight Time (North America).\",\"score\":0.5191075,\"raw_content\":null},{\"url\":\"https://24timezones.com\",\"title\":\"World Clock \u2014 current time around the world\",\"content\":\"Our Global Timezone Map displays the current time now around the world. The map also reflects the daylight, night and midnight in real-time.\",\"score\":0.40613216,\"raw_content\":null},{\"url\":\"https://www.time.gov\",\"title\":\"Time.gov\",\"content\":\"07:24:40 P.M.. Mountain DAYLIGHT Time. MDT (UTC-6).\",\"score\":0.34813574,\"raw_content\":null},{\"url\":\"https://time.is\",\"title\":\"Time.is - exact time, any time zone\",\"content\":\"Your clock is 22 hours, 15 minutes and 33.3 seconds behind. \u00b7 Tokyo 07:15am \u00b7 Beijing 06:15am \u00b7 Paris 12:15am \u00b7 London 11:15pm \u00b7 New York 06:15pm.\",\"score\":0.33463344,\"raw_content\":null},{\"url\":\"https://www.worldometers.info/time/indiana-united-states\",\"title\":\"Time in Indiana, USA (LIVE) - Worldometer\",\"content\":\"Exact local time now in Indiana, United States. Time Zone, UTC offset ... Current Local Time in Indiana, United States. 12h24h. AnalogDigital. 08:26:48.\",\"score\":0.32008815,\"raw_content\":null}],\"response_time\":0.56,\"request_id\":\"6cde2892-f5b5-4e30-9011-40cc7b586d39\"}",
#     "name": "web_search"
#   },
#   {
#     "role": "ai",
#     "content": "",
#     "name": null,
#     "think": "The web search results show various times. The first result shows \"Current Time in , Indiana | Timezone and Date in IN. USA\" with content \"Current Time in , IN. 02:45:28. AM. EDT. Thursday, May 7, 2026.\" That seems like a future date (May 7, 2026) which is odd. Another result from time.gov shows \"07:24:40 P.M.. Mountain DAYLIGHT Time. MDT (UTC-6).\" That might be more current. However, the search results may not be perfectly accurate. I should provide an answer based on the most reliable source. Time.gov is the official U.S. time. The result says \"07:24:40 P.M.. Mountain DAYLIGHT Time. MDT (UTC-6).\" That suggests it's 7:24:40 PM MDT. But I need to consider the user's location? The user didn't specify location. I could give the current UTC time or mention that I don't have real-time clock but can provide approximate time from web search. However, as an IT help desk agent, I should be helpful. I can say that based on web search, the current time is approximately [time] in [timezone]. But I should cite the source.\n\nLet me check another source: time.is shows \"Your clock is 22 hours, 15 minutes and 33.3 seconds behind.\" That indicates the user's clock is off. Not helpful.\n\nI could also search for \"current time now\" to get a more direct answer. Let me try a different query.\n"
#   },
#   {
#     "role": "tool",
#     "content": "{\"query\":\"current time now\",\"follow_up_questions\":null,\"answer\":null,\"images\":[],\"results\":[{\"url\":\"https://www.thetimenow.com\",\"title\":\"The Time Now: What Time Is It\",\"content\":\"Current local time in United States \u00b7 12 hour 24 hour. 1:52:30 AM.\",\"score\":0.82425016,\"raw_content\":null},{\"url\":\"https://time.now\",\"title\":\"Time.now: Current Time Now\",\"content\":\"Time now in Major Time Zones \u00b7 EST. Sat 01:03 \u00b7 PST. Fri 22:03 \u00b7 GMT. Sat 05:03 \u00b7 CET. Sat 07:03 \u00b7 JST. Sat 14:03 \u00b7 AEST. Sat 15:03 \u00b7 IST. Sat 10:33 \u00b7 CST. Sat\",\"score\":0.8124067,\"raw_content\":null},{\"url\":\"https://24timezones.com\",\"title\":\"World Clock \u2014 current time around the world\",\"content\":\"Our Global Timezone Map displays the current time now around the world. The map also reflects the daylight, night and midnight in real-time.\",\"score\":0.5090084,\"raw_content\":null},{\"url\":\"https://multimedia.phoenix.edu/tools/time/index.php\",\"title\":\"Arizona Time - Clock - University of Phoenix\",\"content\":\"Current Phoenix Time. 5:00:05 pm. Thursday, May 21, 2026. Current local time is the same as Phoenix. Pacific. 5:00:05 pm. May 21, 2026. Mountain. 6:00:05 pm.\",\"score\":0.49245724,\"raw_content\":null},{\"url\":\"https://www.timeanddate.com/worldclock\",\"title\":\"The World Clock \u2014 Worldwide - Time and Date\",\"content\":\"World time and date for cities in all time zones. International time right now. Takes into account all DST clock changes.\",\"score\":0.4017588,\"raw_content\":null}],\"response_time\":0.87,\"request_id\":\"dbbd70b6-9a41-424f-b0ee-d2fdc78ddf04\"}",
#     "name": "web_search"
#   },
#   {
#     "role": "ai",
#     "content": "",
#     "name": null,
#     "think": "The results show \"Current local time in United States \u00b7 12 hour 24 hour. 1:52:30 AM.\" from thetimenow.com. Another shows \"Time now in Major Time Zones \u00b7 EST. Sat 01:03 \u00b7 PST. Fri 22:03 \u00b7 GMT. Sat 05:03 \u00b7 CET. Sat 07:03 \u00b7 JST. Sat 14:03 \u00b7 AEST. Sat 15:03 \u00b7 IST. Sat 10:33 \u00b7 CST. Sat\" from time.now. This suggests it's around 1:52 AM or 01:03 EST, etc. The dates in some results show May 2026, which is clearly wrong (maybe the search results are cached or have errors). I need to be cautious. Perhaps I should rely on time.gov as the most authoritative. Let me open time.gov directly.\n\n"
#   },
#   {
#     "role": "tool",
#     "content": "{\"query\":\"time.gov current time\",\"follow_up_questions\":null,\"answer\":null,\"images\":[],\"results\":[{\"url\":\"https://www.nist.gov/pml/time-and-frequency-division/what-time-it-faqs\",\"title\":\"What Time is It? FAQs | NIST\",\"content\":\"The current time is shown on the Internet at https://www.time.gov/ - it synchronizes with NIST every ten minutes. There is an accuracy\",\"score\":0.99366105,\"raw_content\":null},{\"url\":\"https://timegov.nist.gov\",\"title\":\"NIST - National Institute of Standards and Technology\",\"content\":\"Hawaii Standard Time. HST (UTC-10). 12:04:34 P.M. ; Samoa Standard Time. SST (UTC-11). 11:04:34 A.M. ; Chamorro Standard Time. CHST (UTC+10). 08:04:34 A.M..\",\"score\":0.98571813,\"raw_content\":null},{\"url\":\"http://cs.indstate.edu/~jkinne/cs473-s2015/current_time2.html\",\"title\":\"current time - Google Search\",\"content\":\"14:28 PM \u00b7 The Official NIST US Time: \u00b7 Current local time in New York, New York, U.S.A. \u00b7 The World Clock \u2014 Worldwide - Time and Date \u00b7 Current local time in San\",\"score\":0.9026096,\"raw_content\":null},{\"url\":\"https://space.umd.edu/pm/currenttime.html\",\"title\":\"What time is it?\",\"content\":\"Current time in GMT from the U.S. Naval Observatory: Clock may require Netscape.\",\"score\":0.677474,\"raw_content\":null},{\"url\":\"https://24timezones.com/United-States/time\",\"title\":\"Current local time in United States - World Clock\",\"content\":\"Current local time in United States \u00b7 Chicago \u00b7 Houston \u00b7 San Antonio \u00b7 Dallas. 3:07 AM. Monday, May 18, 2026. GMT -06:00. MDT \u00b7 Denver \u00b7 El Paso\",\"score\":0.67405045,\"raw_content\":null}],\"response_time\":0.58,\"request_id\":\"5790a1e9-a095-4716-ab9f-ca8a4b1ba211\"}",
#     "name": "web_search"
#   },
#   {
#     "role": "ai",
#     "content": "",
#     "name": null,
#     "think": "The NIST result shows various times: Hawaii Standard Time 12:04:34 P.M., Samoa Standard Time 11:04:34 A.M., Chamorro Standard Time 08:04:34 A.M.. This seems like a snapshot. The time appears to be around 12:04 PM HST, which is UTC-10. That would be 22:04 UTC? Let's calculate: HST is UTC-10, so 12:04 PM HST = 22:04 UTC. Samoa Standard Time (UTC-11) 11:04 AM = 22:04 UTC. Chamorro Standard Time (UTC+10) 08:04 AM = 22:04 UTC. So the time is consistent: 22:04 UTC. That would be 6:04 PM EDT (UTC-4), 3:04 PM PDT (UTC-7), etc. However, the result also shows \"Current local time in United States \u00b7 Chicago \u00b7 Houston \u00b7 San Antonio \u00b7 Dallas. 3:07 AM. Monday, May 18, 2026. GMT -06:00. MDT\" which again shows a date in May 2026. This is confusing; maybe the search results are returning outdated or test data. I should not rely on dates from these results.\n\nGiven the inconsistency, I should perhaps tell the user that I don't have access to a real-time clock, but I can suggest they check their device clock or visit time.gov. However, as an IT help desk agent, I might be expected to provide the current time if possible. I could use the web search to get a rough estimate, but I need to cite sources.\n\nLet me try a query for \"current UTC time\".\n\n"
#   },
#   {
#     "role": "tool",
#     "content": "{\"query\":\"current UTC time\",\"follow_up_questions\":null,\"answer\":null,\"images\":[],\"results\":[{\"url\":\"https://www.utctime.net\",\"title\":\"UTC Time Now\",\"content\":\"Current time: 22:10:29 UTC. UTC is replaced with Z that is the zero UTC offset. UTC time in ISO-8601 is 22:10:29Z. Note\",\"score\":0.99957937,\"raw_content\":null},{\"url\":\"https://www.tickcounter.com/timezone/utc\",\"title\":\"Current Time In UTC - TickCounter\",\"content\":\"Online clock showing current local date and time in timezone UTC (UTC ... Current time in UTC. 17:04:38. Thursday, May 21st 2026, UTC+00:00. Share New\",\"score\":0.9991239,\"raw_content\":null},{\"url\":\"https://24timezones.com/time-zone/utc\",\"title\":\"UTC time zone \u2014 Coordinated Universal Time - World Clock\",\"content\":\"Current UTC time. UTC. 20334PM. Saturday, May 23, 2026. What is Coordinated Universal Time. UTC timing. UTC (Coordinated Universal Time) is one of the well-\",\"score\":0.9990527,\"raw_content\":null},{\"url\":\"https://time.now/timezones/utc\",\"title\":\"Current Time in UTC (Coordinated Universal Time) - Time.now\",\"content\":\"Time now at UTC time zones: \u00b7 UTC-12 Fri 12:00 \u00b7 UTC-11 Fri 13:00 \u00b7 UTC-10 Fri 14:00 \u00b7 UTC-9:30 Fri 14:30 \u00b7 UTC-9 Fri 15:00 \u00b7 UTC-8 Fri 16:00 \u00b7 UTC-7 Fri 17:00\",\"score\":0.9979493,\"raw_content\":null},{\"url\":\"https://currenttimeutc.com\",\"title\":\"Current Time UTC - Lightning fast times\",\"content\":\"Current Time UTC - Lightning fast times. Effortlessly and accurately convert time zones with our user-friendly tool. Find local times for any location!\",\"score\":0.99771273,\"raw_content\":null}],\"response_time\":0.69,\"request_id\":\"25916f74-8fe1-44ed-bd44-46d87058775e\"}",
#     "name": "web_search"
#   },
#   {
#     "role": "ai",
#     "content": "",
#     "name": null,
#     "think": "The first result from utctime.net says \"Current time: 22:10:29 UTC\". The second from tickcounter says \"Current time in UTC. 17:04:38. Thursday, May 21st 2026, UTC+00:00.\" Again date May 2026. The third says \"Current UTC time. UTC. 20334PM. Saturday, May 23, 2026.\" That seems like a garbled time. The fourth from time.now shows offsets. The inconsistency suggests that many of these sites might be returning cached or incorrect data. However, the utctime.net result seems plausible: 22:10:29 UTC. That would be 6:10 PM EDT (if EDT is UTC-4). But I don't know the current date.\n\nGiven the user's simple question \"what time is it?\", I think the best answer is to provide the current UTC time from a reliable source, citing utctime.net. I'll also mention that time zones vary. I'll answer: According to utctime.net, the current UTC time is 22:10:29 UTC. For local time, please check your device settings or visit time.gov.\n\nBut I should also check if there's a more recent search. The utctime.net result might be from the search at that moment. I'll use that.\n\nLet me also check time.gov directly via web search for the exact time.\n\n\n"
#   },
#   {
#     "role": "tool",
#     "content": "{\"query\":\"current time\",\"follow_up_questions\":null,\"answer\":null,\"images\":[],\"results\":[{\"url\":\"https://www.time.gov\",\"title\":\"Time.gov\",\"content\":\"05:24:03 P.M.. Mountain DAYLIGHT Time. MDT (UTC-6).\",\"score\":0.6698534,\"raw_content\":null},{\"url\":\"https://time.gov/web\",\"title\":\"NIST TIME - Time.gov\",\"content\":\"Official UTC(NIST) Time. 09:58:03 P.M.. Pacific Daylight Time (UTC-7)\",\"score\":0.6102915,\"raw_content\":null},{\"url\":\"https://time.gov/widget\",\"title\":\"NIST Time Widget - Time.gov\",\"content\":\"It is a web clock showing the official time of day from NIST, displayed as a 12 or 24-hour clock, in a user-selectable time zone. The time reference for the\",\"score\":0.54346967,\"raw_content\":null},{\"url\":\"https://www.time.gov?t=24\",\"title\":\"NIST - National Institute of Standards and Technology\",\"content\":\"03:04:34 P.M.. United States Time Zone Map. 24\",\"score\":0.51325434,\"raw_content\":null},{\"url\":\"https://nist.time.gov\",\"title\":\"NIST Time.gov\",\"content\":\"National Institute of Standards and Technology/ OFFICIAL U.S. TIME ... Hashed image for Daylight Saving Time not observed = DAYLIGHT SAVING TIME NOT OBSERVED.\",\"score\":0.41094592,\"raw_content\":null}],\"response_time\":1.11,\"request_id\":\"b0e5d8e6-5678-4cb0-84b8-dc0f853c4ec2\"}",
#     "name": "web_search"
#   },
#   {
#     "role": "ai",
#     "content": "Based on a web search, the current Coordinated Universal Time (UTC) is approximately **22:10:29 UTC** [Web].  \n\nPlease note that time zones vary by location. For official U.S. time, you can visit [time.gov](https://www.time.gov), and for your local time, check the clock on your device or operating system.  \n\nIf you need assistance with time\u2011related IT issues (e.g., clock synchronization, time zone settings, or VPN/email timestamp problems), let me know and I can search our internal knowledge base for specific guidance.",
#     "name": null,
#     "think": "Now I have time.gov results: \"05:24:03 P.M.. Mountain DAYLIGHT Time. MDT (UTC-6).\" and \"Official UTC(NIST) Time. 09:58:03 P.M.. Pacific Daylight Time (UTC-7)\". Let's interpret: Mountain Daylight Time (MDT) is UTC-6. If it's 05:24:03 PM MDT, that is 17:24:03 MDT. Adding 6 hours gives UTC 23:24:03. Pacific Daylight Time (PDT) is UTC-7. 09:58:03 PM PDT is 21:58:03 PDT, adding 7 hours gives UTC 04:58:03 next day? Wait, 21:58:03 PDT + 7 = 04:58:03 UTC next day. That doesn't match. Actually, PDT is UTC-7, so 21:58:03 PDT = 04:58:03 UTC (next day). MDT is UTC-6, so 17:24:03 MDT = 23:24:03 UTC. These are inconsistent by about 5 hours. Something is off. Perhaps the times are from different moments due to search latency. Or maybe the search results are showing different times because of caching.\n\nLet's look at the content: \"05:24:03 P.M.. Mountain DAYLIGHT Time. MDT (UTC-6).\" That seems like a time in the afternoon. \"Official UTC(NIST) Time. 09:58:03 P.M.. Pacific Daylight Time (UTC-7)\" That is evening. If it's 5:24 PM MDT, then PDT (which is one hour behind MDT) would be 4:24 PM PDT, not 9:58 PM. So these results are not consistent; they might be from different days or erroneous.\n\nGiven the confusion, I think the safest answer is to state that I don't have access to a real-time clock, but I can direct the user to reliable sources like time.gov or suggest they check their device clock. However, the user asked \"what time is it?\" expecting an answer. As an IT help desk agent, I might be expected to provide the current time if possible. I could use the web search to get a rough estimate and mention the uncertainty.\n\nAlternatively, I could use the company's IT knowledge base? But that's for IT policies, not time. Not relevant.\n\nI'll answer with the UTC time from utctime.net, citing it, and note that time zones vary. I'll also mention that for official U.S. time, they can visit time.gov.\n\nLet's formulate the answer.\n\n"
#   }
# ]
def load_history(assistant_id: str, thread_id: str) -> List[Dict]:
    """
    从文件加载历史记录

    参数:
        assistant_id: 助手ID，用于构建文件名前缀
        thread_id: 线程ID

    返回:
        历史消息列表
    """
    # 文件名格式: {assistant_id[:8]}_{thread_id}.json
    history_file = HISTORY_DIR / f"{assistant_id[:8]}_{thread_id}.json"
    _LOGGER.debug(f"Loading history from: {history_file}")
    if history_file.exists():
        try:
            with open(history_file, "r") as f:
                history = json.load(f)
                _LOGGER.debug(f"Loaded {len(history)} messages")
                return history
        except Exception as e:
            _LOGGER.error(f"Failed to load history: {e}")
            return []
    return []


def save_history(assistant_id: str, thread_id: str, history: List[Dict]):
    """
    将历史记录保存到文件

    参数:
        assistant_id: 助手ID，用于构建文件名前缀
        thread_id: 线程ID
        history: 历史消息列表
    """
    # 文件名格式: {assistant_id[:8]}_{thread_id}.json
    history_file = HISTORY_DIR / f"{assistant_id[:8]}_{thread_id}.json"
    _LOGGER.debug(f"Saving {len(history)} messages to: {history_file}")
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)


def get_all_conversations(assistant_id: str) -> List[Dict]:
    """
    获取指定助手的所有历史对话

    参数:
        assistant_id: 助手ID，用于过滤历史记录文件

    返回格式:
    [
        {
            "thread_id": "xxx",
            "preview": "第一条消息内容预览...",
            "created_at": "文件创建时间",
            "message_count": 消息数量
        },
        ...
    ]
    """
    conversations = []
    if not os.path.exists(HISTORY_DIR):
        return conversations

    # 文件名前缀: {assistant_id[:8]}_
    prefix = f"{assistant_id[:8]}_"

    for filename in os.listdir(HISTORY_DIR):
        # 只处理属于当前助手的历史记录文件
        if filename.startswith(prefix) and filename.endswith(".json"):
            # 从文件名中提取 thread_id
            # 文件名格式: {assistant_id[:8]}_{thread_id}.json
            # 移除前缀和 .json 后缀
            thread_id = filename[len(prefix) : -5]
            history_file = os.path.join(HISTORY_DIR, filename)

            try:
                with open(history_file, "r") as f:
                    history = json.load(f)

                if not history:
                    continue

                # 获取第一条用户消息作为预览
                preview = "Empty conversation"
                for msg in history:
                    if msg.get("role") == "user":
                        preview = msg.get("content", "")[:50]
                        if len(msg.get("content", "")) > 50:
                            preview += "..."
                        break

                # 获取文件修改时间
                created_at = os.path.getmtime(history_file)

                conversations.append(
                    {
                        "thread_id": thread_id,
                        "preview": preview,
                        "created_at": created_at,
                        "message_count": len(history),
                    }
                )
            except:
                continue

    # 按修改时间倒序排列（最新的在前）
    conversations.sort(key=lambda x: x["created_at"], reverse=True)
    return conversations


# 头像映射表：决定不同角色在聊天界面中显示的头像
# - "ai": 使用 Streamlit 内置的 "assistant" 头像 (🤖)
# - "user": 使用 Streamlit 内置的 "user" 头像 (👤)
# - "tool": 使用 emoji 图标 (🛠️)
AVATARS = {"ai": "assistant", "user": "user", "tool": "🛠️"}

# 流式响应开关：部分模型可能不支持流式响应与工具调用同时使用
# STREAMING=True: ["updates", "messages"] - 实时显示流式消息
# STREAMING=False: ["updates", "values"] - 等待完整响应后处理（可能有问题）
STREAMING = False  # 非流式模式，避免重复显示问题


# ==============================================================================
# Streamlit 页面初始化
# ==============================================================================

# 配置页面标题、布局和图标
st.set_page_config(page_title="AI TechOps", layout="wide", page_icon="🤖")

# 添加自定义样式确保侧边栏按钮左对齐
st.markdown(
    """
    <style>
    /* 确保侧边栏按钮左对齐 */
    section[data-testid="stSidebar"] button[kind="secondary"] {
        justify-content: flex-start !important;
        text-align: left !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# 初始化会话状态（Session State）
# ==============================================================================
# Session State 会在整个用户会话期间持久保存，刷新页面后仍然保留
# st.session_state 是 Streamlit 提供的 SessionStateProxy 对象
# 支持两种访问方式：
#   - 点操作符：st.session_state.threads（推荐，更简洁）
#   - 字典访问：st.session_state["threads"]
#       # key 是变量时，必须用 []
#           key = "threads"
#           st.session_state[key]  # ✅ 可以
#           st.session_state.key    # ❌ 不行，Python 会把 key 当作属性名
# threads: 存储每个助手对应的会话线程ID
#   - 这里的thread_id 就是 LangGraph API 服务器返回的会话线程标识符，
#   - 详见：new_thread_id = CLIENT.threads.create()["thread_id"]）
# 结构: {ASSISTANT_ID: THREAD_ID}
if "threads" not in st.session_state:
    st.session_state.threads: Dict[str, str] = {}

# history: 存储每个助手对应的聊天历史消息
# 结构: {ASSISTANT_ID: [{"role": "user/ai/tool", "content": "...", ...}, ...]}
if "history" not in st.session_state:
    st.session_state.history: Dict[str, List[Dict[str, str]]] = {}


# ==============================================================================
# 辅助函数：获取助手列表
# ==============================================================================
# 缓存装饰器：将函数结果缓存到内存中，避免频繁调用 API
# - 存储位置：内存（RAM），重启服务器会清空
# - 作用域：全局（所有用户共享）
# - 过期时间：90 秒（TTL）
@st.cache_data(show_spinner=False, ttl=90)
def list_assistants() -> List[Dict[str, Any]]:
    """
    从 LangGraph API 服务器获取可用的助手列表

    助手注册和发现流程：
    1. 服务器启动时读取 langgraph.json 配置文件
    2. 配置文件中定义了助手名称和对应的模块路径
       例如：{"rag_agent": "rag_agent:AGENT"}
    3. 服务器加载指定模块（如 rag_agent.py）
    4. 提取模块中的 AGENT 变量（由 create_react_agent 创建）
    5. 将助手注册到 API 服务中
    6. 客户端通过 CLIENT.assistants.search() 查询可用助手

    返回:
        助手列表，每个助手包含 assistant_id、name 等信息
    """
    try:
        # 调用 API 搜索最多50个助手
        return CLIENT.assistants.search(limit=50)
    except httpx.ConnectError:
        # 连接失败时显示错误信息并停止应用
        st.markdown(
            """
            # Uh oh! 😱

            It looks like the LangGraph API server is not reachable. Please check if the server is running.
            """
        )
        st.stop()


# ==============================================================================
# 加载助手列表并检查连接
# ==============================================================================

# 从服务器获取助手列表
ALL_ASSISTANTS = list_assistants()

# Sample assistant list
# ALL_ASSISTANTS = [
#     {
#         "assistant_id": "3aa5e058-25ba-5c4e-9cd4-b994c9cf54f1",
#         "graph_id": "rag_agent",
#         "config": {},
#         "context": {},
#         "metadata": {"created_by": "system"},
#         "name": "rag_agent",
#         "created_at": "2026-05-24T02:44:59.881616+00:00",
#         "updated_at": "2026-05-24T02:44:59.881616+00:00",
#         "version": 1,
#         "description": None
#     }
# ]

# 如果没有找到助手，显示错误信息并停止
if not ALL_ASSISTANTS:
    st.error("❌ No assistants found on the server.")
    st.markdown(
        """
    **The LangGraph API server is not running!**

    Please start the server first:
    ```bash
    cd code/2-agentic-rag
    langgraph dev
    ```

    Then wait for the message: *"Ready accept requests at http://127.0.0.1:2024"*

    See `.devx/2-agentic-rag/running.md` for more details.
    """
    )
    st.stop()


# ==============================================================================
# 侧边栏：助手选择和会话管理
# ==============================================================================

with st.sidebar:
    # 助手选择下拉框
    # - ALL_ASSISTANTS: 选项列表，每个元素是一个助手字典
    # - format_func: 格式化函数，决定下拉框显示什么文字
    #   - 有 name 字段则显示 name（如 "rag_agent"）
    #   - 没有 name 则显示 assistant_id
    # - 显示的文字由 Streamlit 组件内部管理，不保存到变量
    # - 返回值: 用户选中的完整助手字典（不是显示的文字）
    ASSISTANT = st.selectbox(
        "Select Assistant",
        ALL_ASSISTANTS,
        format_func=lambda a: a.get("name") or a["assistant_id"],
    )
    # 从选中的助手字典中提取 assistant_id
    ASSISTANT_ID = ASSISTANT["assistant_id"]

    # 新建对话按钮
    if st.sidebar.button("➕ New conversation", use_container_width=True):
        _LOGGER.info(f"Creating new conversation for assistant: {ASSISTANT_ID}")
        # 直接创建新线程（不删除旧的历史记录文件）
        # 这行代码的作用是： 创建一个新的对话线程（thread）并获取其 ID 。
        #   - CLIENT 是 LangGraph SDK 的同步客户端（第61行初始化）
        #   - CLIENT.threads.create() 调用 LangGraph API 服务器的 /threads 端点
        #   - 服务器返回一个字典，其中包含 thread_id 字段
        #   - 这是一个 UUID 格式 的唯一标识符，例如："3aa5e058-25ba-5c4e-9cd4-b994c9cf54f1"
        # thread_id 的作用。在 LangGraph 架构中
        #   - LangGraph使用thread来管理多轮对话的上下文
        #   - 每个thread维护独立的对话状态和历史
        #   - 相当于 ChatGPT 中的"对话"概念
        # 赋值给 new_thread_id
        #   - 将线程 ID 保存到变量中，供后续使用
        new_thread_id = CLIENT.threads.create()["thread_id"]
        st.session_state.threads[ASSISTANT_ID] = new_thread_id
        st.session_state.history[ASSISTANT_ID] = []
        # 将新创建的线程ID同步到URL查询参数，实现对话链接分享和书签功能
        # - st.query_params: Streamlit的URL参数管理器，用于读写URL中的?key=value参数
        # - f"thread_{ASSISTANT_ID[:8]}": 生成唯一的参数名，使用助手ID前8字符作为前缀
        #   这样可以支持多个助手同时使用不同的线程（避免key冲突）
        # - new_thread_id: LangGraph服务器返回的线程唯一标识符（UUID格式）
        # - 效果: URL会变成类似 http://localhost:8501/?thread_3aa5e058=dc75f828-xxx
        # - 用途: 用户可以复制URL分享给他人，或添加书签，打开时自动恢复到该对话
        # 触发场景 ：用户点击"新建对话"按钮
        # 目的 ：同步 新创建的线程 到 URL 参数
        st.query_params[f"thread_{ASSISTANT_ID[:8]}"] = new_thread_id
        # 强制重新运行整个应用脚本，将状态变化同步到界面
        # - Streamlit 的特性：修改 session_state 后界面不会自动更新
        # - st.rerun() 触发整个脚本重新执行，类似用户手动刷新页面（F5）
        # - 注：Streamlit 的特性 ：脚本只在特定事件下执行：
        #       - 用户输入内容
        #       - 用户点击按钮
        #       - 手动刷新页面
        # - 执行流程：重新读取 session_state → 重新渲染侧边栏 → 重新渲染聊天区域
        # - 副作用：整个脚本从第一行重新执行，包括可能的 API 调用
        #       - 注意：有 @st.cache_data 装饰器的函数会使用缓存，避免频繁请求
        st.rerun()

    # -------------------------------------------------------------------------
    # 1. 先确定当前线程 ID（优先级：Session State > URL 参数 > 新建对话）
    # -------------------------------------------------------------------------
    # 这行代码 就是从浏览器地址栏的 URL 查询参数中获取线程 ID 。
    # 1）. st.query_params 是什么？
    # st.query_params 是 Streamlit 提供的 URL 查询参数管理器 ，专门用于读取和写入 URL 中的 ?key=value 部分。
    # 2）. 工作原理
    # 假设用户在地址栏输入的 URL 是：
    # ```
    # http://localhost:8501/?
    # thread_3aa5e058=dc75f828-2cfa-437b-82f5-39
    # 7791c44f2e
    # ```
    # 查询参数部分 ：
    # - key = thread_3aa5e058
    # - value = dc75f828-2cfa-437b-82f5-397791c44f2e
    # 3）. get() 方法的作用
    # ```
    # st.query_params.get("key", default_value)
    # ```
    # - 如果 URL 中存在该参数，返回对应的值
    # - 如果不存在，返回 None （默认值）
    thread_id_from_url = st.query_params.get(f"thread_{ASSISTANT_ID[:8]}")
    thread_value = st.session_state.threads.get(ASSISTANT_ID)

    if thread_value is not None:
        # 使用 Session State 中的线程 ID
        THREAD_ID = thread_value
    elif thread_id_from_url:
        # 回退到 URL 中的线程 ID
        THREAD_ID = thread_id_from_url
        st.session_state.threads[ASSISTANT_ID] = THREAD_ID
    else:
        # 创建新线程（像 ChatGPT 一样，默认是新对话）
        THREAD_ID = CLIENT.threads.create()["thread_id"]
        st.session_state.threads[ASSISTANT_ID] = THREAD_ID

    # 确保历史记录已加载
    if (
        ASSISTANT_ID
        not in st.session_state.history  # 检查当前助手是否还没有在内存中的历史记录字典里
        or not st.session_state.history[
            ASSISTANT_ID
        ]  # 检查当前助手的历史记录是否为空列表 []
    ):
        # 满足任意一个条件就执行加载历史记录操作
        _LOGGER.info(f"Loading history for assistant: {ASSISTANT_ID}")
        st.session_state.history[ASSISTANT_ID] = load_history(ASSISTANT_ID, THREAD_ID)

    # 每次脚本执行后，同步当前的线程 ID 到 URL（必须保留！）
    # - 目的：确保 URL 始终反映当前对话状态，支持链接分享和书签保存
    # - 覆盖场景：
    #   1. 用户从 URL 恢复对话：同步当前 thread_id 到 URL（即使已有旧参数）
    #   2. 用户切换助手：设置新助手对应的 thread_id
    #   3. 用户切换对话（侧边栏 History）：同步新对话的 thread_id
    #   4. 用户刷新页面（F5）：确保 URL 保持不变，状态不丢失
    #   5. 程序启动时：同步新创建的线程到 URL
    # - 防御性编程：即使其他地方（如新建对话）也设置了 URL，这里做双重保险
    # 这行代码的唯一直接作用就是修改浏览器地址栏的 URL，不会做任何其他操作。
    st.query_params[f"thread_{ASSISTANT_ID[:8]}"] = THREAD_ID

    # -------------------------------------------------------------------------
    # 2. 历史对话列表
    # -------------------------------------------------------------------------
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📜 History")

    # 获取所有历史对话
    all_conversations = get_all_conversations(ASSISTANT_ID)

    if all_conversations:
        for conv in all_conversations:
            # 每个对话一个按钮
            thread_id = conv["thread_id"]
            preview = conv["preview"]
            msg_count = conv["message_count"]

            # 判断是否是当前对话
            is_current = THREAD_ID == thread_id

            # 按钮标签
            label = f"{'✓ ' if is_current else ''}{preview}"

            if st.sidebar.button(
                label,
                key=f"conv_{thread_id}",
                use_container_width=True,
            ):
                _LOGGER.info(f"Switching to conversation: {thread_id}")
                # 切换到这个对话 - 更新 Session State 和 URL
                st.session_state.threads[ASSISTANT_ID] = thread_id
                st.session_state.history[ASSISTANT_ID] = load_history(
                    ASSISTANT_ID, thread_id
                )
                st.query_params[f"thread_{ASSISTANT_ID[:8]}"] = thread_id
                # 强制重新运行以更新界面
                st.rerun()
    else:
        st.sidebar.info("No history")


# ==============================================================================
# JavaScript 容器：用于执行 JavaScript 代码
# ==============================================================================

# 创建一个高度为1像素的不可见容器，用于放置 JavaScript 代码
# 这里主要用于关闭页面上已展开的所有推理面板
JS_CONTAINER = st.container(height=1, border=False)


# ==============================================================================
# 辅助函数：创建消息框和占位符
# ==============================================================================


def _create_message_box(persona, tool_name):
    """
    为流式消息创建空的消息框和占位符

    参数:
        persona: 消息角色 ("user", "ai", "tool")
        tool_name: 工具名称（仅当 persona="tool" 时使用）

    返回:
        (reasoning_contents, message_contents): 两个空占位符
            - reasoning_contents: 用于显示模型的推理/思考过程
            - message_contents: 用于显示实际的回复内容
    """
    # 第一步：关闭页面上所有已展开的推理面板（expander）
    # 这是通过 JavaScript 代码实现的，查找所有带有 open 属性的 <details> 元素并移除 open 属性
    # 使用 JS_CONTAINER 容器来执行这段 JavaScript
    with JS_CONTAINER:
        components.html(
            """
            <script>
            parent.document.querySelectorAll('details[open]').forEach(details => {
                details.removeAttribute('open');
            });
            </script>
            """,
            height=1,  # 容器高度设为1像素，几乎不可见
        )
        # 等待0.1秒确保 JavaScript 执行完成
        time.sleep(0.1)

    # 第二步：创建新的聊天消息框
    # CHAT.chat_message() 创建一个带有头像的消息容器
    # AVATARS.get(persona, "🤖") 根据 persona 获取对应的头像
    message_box = CHAT.chat_message(AVATARS.get(persona, "🤖"))

    # 第三步：如果消息来自工具调用，将其包装在可折叠的面板中
    # 工具调用通常返回较长的输出，使用 expander 可以默认收起，保持界面整洁
    if persona == "tool":
        # 创建折叠面板，标题为 "Using {tool_name}..."，默认收起 (expanded=False)
        message_box = message_box.expander(f"Using {tool_name}...", expanded=False)

    # 第四步：创建两个空占位符
    # 这些占位符可以在后续被填充内容，实现"流式"更新效果
    # - reasoning_contents: 用于推理内容
    # - message_contents: 用于实际回复内容
    return message_box.empty(), message_box.empty()


def _create_streaming_message_box(persona, tool_name):
    """
    为流式消息创建消息框（与 _create_message_box 相同）

    注意：为了累积显示流式内容，使用 _create_message_box 即可
    这里保留此函数是为了代码兼容性
    """
    return _create_message_box(persona, tool_name)


# ==============================================================================
# 主聊天界面：渲染历史消息
# ==============================================================================

# 创建一个容器用于存放聊天消息
CHAT = st.container()

# 创建聊天输入框（始终显示在页面底部）
# 当用户输入内容并按下回车时，USER_INPUT 将包含输入的文本
USER_INPUT = st.chat_input("💬 How can I help you?")

# 遍历并渲染历史消息
# st.session_state.history.get(ASSISTANT_ID, []) 获取当前助手的历史消息列表
# 如果没有历史记录，返回空列表
for msg in st.session_state.history.get(ASSISTANT_ID, []):
    # 为每条消息创建消息框和占位符
    # msg["role"] 决定使用哪个头像
    # msg.get("name") 获取工具名称（如果是工具消息）
    reasoning_contents, message_contents = _create_message_box(
        msg["role"], msg.get("name")
    )

    # 如果消息包含 "think" 字段（推理内容），创建折叠面板显示
    if "think" in msg and msg["think"]:
        # 创建折叠面板，标题为 "Reasoning"，默认收起
        reasoning_expander = reasoning_contents.expander("Reasoning", expanded=False)
        # 在折叠面板中显示推理内容
        reasoning_expander.markdown(msg["think"])

    # 在消息框中显示实际内容
    # 只有当 content 不为空时才显示
    if msg.get("content"):
        message_contents.markdown(msg["content"])


# ==============================================================================
# 处理用户输入：发送消息并接收响应
# ==============================================================================

# 当用户输入内容并按下回车时触发
if USER_INPUT:
    _LOGGER.info(f"User input (thread: {THREAD_ID}): {USER_INPUT}")

    # 1. 将用户消息添加到历史记录
    st.session_state.history.setdefault(ASSISTANT_ID, []).append(
        {"role": "user", "content": USER_INPUT}
    )

    # 保存历史记录到文件
    save_history(ASSISTANT_ID, THREAD_ID, st.session_state.history[ASSISTANT_ID])

    # 2. 立即在界面上显示用户消息
    with CHAT.chat_message("user"):
        st.markdown(USER_INPUT)

    # 3. 接收 AI 响应
    # 初始化占位符为 None，以便首次创建
    message_contents = None
    reasoning_contents = None

    # 累积内容变量，用于收集流式响应中的所有内容片段
    accumulated_content = ""

    # 记录处理前的历史长度（包含用户消息）
    # 用户消息已经在第664-666行添加到历史中，所以这里包含用户消息
    initial_history_length = len(st.session_state.history.get(ASSISTANT_ID, []))

    # 用于跟踪已显示的消息，避免重复显示（跨事件去重）
    # 初始化时包含所有历史消息的标识
    displayed_messages = set()
    for hist_msg in st.session_state.history.get(ASSISTANT_ID, []):
        hist_role = hist_msg.get("role") or hist_msg.get("type")
        hist_persona = hist_role
        if hist_role == "assistant":
            hist_persona = "ai"
        elif hist_role == "human":
            hist_persona = "user"
        hist_content = hist_msg.get("content", "")
        hist_name = hist_msg.get("name", "")
        # 同时包含 think/reasoning_content 以区分只有推理内容的消息
        hist_think = hist_msg.get("think", "") or hist_msg.get(
            "additional_kwargs", {}
        ).get("reasoning_content", "")
        # 使用更完整的键，包含 think 内容的前100个字符
        think_snippet = hist_think[:100] if hist_think else ""
        msg_key = f"{hist_persona}_{hist_name}_{hist_content}_{think_snippet}"
        displayed_messages.add(msg_key)

    # 确定流式模式：部分模型可能不支持流式响应
    # STREAMING=True: ["updates", "messages"] - 实时显示流式消息
    # STREAMING=False: ["updates", "values"] - 等待完整响应后处理
    stream_mode = ["updates", "messages"] if STREAMING else ["updates", "values"]

    # 开始请求
    for msg in CLIENT.runs.stream(
        thread_id=THREAD_ID,  # 会话线程 ID
        assistant_id=ASSISTANT_ID,  # 助手 ID
        input={"messages": [{"role": "user", "content": USER_INPUT}]},  # 用户输入
        stream_mode=stream_mode,  # 流式模式
    ):
        # 解析事件类型和数据
        event = msg.event.split("/")  # 事件格式如 "values/partially_complete"

        # 跳过元数据事件
        if "metadata" in event:
            continue

        data = msg.data  # 事件携带的数据

        # =====================================================================
        # 处理非流式模式的最终响应（STREAMING=False）
        # =====================================================================

        # 当 event[0] == "values" 时，表示收到了完整响应（未启用流式）
        if event[0] == "values":
            # 确保消息存在
            if not data.get("messages"):
                continue

            # 遍历所有消息并显示，只显示新增的非用户消息
            all_messages = data.get("messages")

            for idx, message in enumerate(all_messages):
                # API返回格式使用 type，历史记录使用 role
                msg_type = message.get("type")
                msg_role = message.get("role")

                # 确定消息角色，优先使用 type
                if msg_type == "human" or msg_role == "user":
                    persona = "user"
                elif msg_type == "ai" or msg_role == "assistant":
                    persona = "ai"
                elif msg_type == "tool" or msg_role == "tool":
                    persona = "tool"
                elif msg_role:
                    persona = msg_role
                else:
                    persona = "ai"

                msg_content = message.get("content", "")
                msg_name = message.get("name", "")

                # 跳过用户消息（因为已经在界面上显示了）
                if persona == "user":
                    continue

                # 跳过历史消息（只显示索引 >= initial_history_length 的消息）
                if idx < initial_history_length:
                    continue

                # 提取推理内容（用于生成唯一键）
                reasoning_content = message.get("think", "") or message.get(
                    "additional_kwargs", {}
                ).get("reasoning_content", "")

                # 生成唯一消息标识（用于跨事件去重），包含 think 内容的前100个字符
                think_snippet = reasoning_content[:100] if reasoning_content else ""
                msg_key = f"{persona}_{msg_name}_{msg_content}_{think_snippet}"

                # 检查此消息是否已经在本次请求中显示过
                if msg_key in displayed_messages:
                    continue

                # 标记为已显示
                displayed_messages.add(msg_key)

                # 提取实际内容
                content = message.get("content", "")

                # 只有当有内容或有推理内容时才创建消息框
                if not content and not reasoning_content:
                    continue

                # 创建消息框
                reasoning_contents, message_contents = _create_message_box(
                    persona, msg_name
                )

                # 显示推理内容（如果有）
                if reasoning_content:
                    reasoning_expander = reasoning_contents.expander(
                        "� Reasoning", expanded=False
                    )
                    reasoning_expander.markdown(reasoning_content)

                # 显示实际内容（如果有）
                if content:
                    # 工具消息用代码块显示（通常是JSON格式）
                    if persona == "tool":
                        message_contents.code(content, language="json")
                    else:
                        message_contents.markdown(content)

        # =====================================================================
        # 处理流式消息（event[0] == "messages"）
        # =====================================================================

        elif event[0] == "messages":
            # 获取消息类型（ai, user, tool 等）
            persona = data[0].get("type", "ai")
            # 获取对应的节点/工具名称
            graph_node_name = data[0].get("name", "")

            # 首次创建消息框和占位符
            if reasoning_contents is None or message_contents is None:
                reasoning_contents, message_contents = _create_streaming_message_box(
                    persona, graph_node_name
                )

            # 提取并显示推理内容（如果有）
            reasoning_content = (
                data[0].get("additional_kwargs", {}).get("reasoning_content", "")
            )
            if reasoning_content:
                reasoning_expander = reasoning_contents.expander(
                    "� Reasoning",
                    expanded=True,  # 流式响应时展开
                )
                reasoning_expander.markdown(reasoning_content)

            # 累积实际的回复内容
            content = data[0].get("content", "")
            if content:
                accumulated_content += content
                message_contents.markdown(accumulated_content)

        # =====================================================================
        # 处理消息完成事件（event[0] == "updates"）
        # =====================================================================

        elif event[0] == "updates":
            # 重置占位符，为下一条消息做准备
            message_contents = None
            reasoning_contents = None
            accumulated_content = ""

            # 在非流式模式下，消息已经通过 values 事件显示过了，这里只保存历史记录
            # 在流式模式下，这里保存工具调用结果

            # 从 updates 事件中提取工具调用结果
            for tool_call in data.get("tools", {}).get("messages", []):
                tool_message = {
                    "role": "tool",
                    "content": tool_call["content"],
                    "name": tool_call["name"],
                }
                # 在非流式模式下，检查是否已存在相同的工具消息
                if STREAMING or not any(
                    m.get("role") == "tool"
                    and m.get("name") == tool_call["name"]
                    and m.get("content") == tool_call["content"]
                    for m in st.session_state.history.get(ASSISTANT_ID, [])
                ):
                    st.session_state.history[ASSISTANT_ID].append(tool_message)

            # 从 updates 事件中提取 AI 的最终回复
            for agent_message in data.get("model", {}).get("messages", []):
                agent_message = {
                    "role": "ai",
                    "content": agent_message["content"],
                    "name": agent_message["name"],
                    "think": agent_message.get("additional_kwargs", {}).get(
                        "reasoning_content", ""
                    ),
                }
                # 在非流式模式下，检查是否已存在相同的 AI 消息
                if STREAMING or not any(
                    m.get("role") == "ai"
                    and m.get("content") == agent_message["content"]
                    and m.get("think") == agent_message["think"]
                    for m in st.session_state.history.get(ASSISTANT_ID, [])
                ):
                    st.session_state.history[ASSISTANT_ID].append(agent_message)

            # 保存历史记录到文件
            save_history(
                ASSISTANT_ID, THREAD_ID, st.session_state.history[ASSISTANT_ID]
            )
