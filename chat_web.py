import streamlit as st
from openai import OpenAI
import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client

# ---------- 页面配置 ----------
st.set_page_config(page_title="DeepSeek 聊天助手", page_icon="🤖", layout="centered")

# ---------- 自定义 CSS ----------
st.markdown("""
<style>
    .stApp { background-color: #f0f2f6; }
    .chat-row-user { display: flex; justify-content: flex-end; margin: 8px 0; }
    .chat-bubble-user { background-color: #1a73e8; color: white; border-radius: 18px 18px 4px 18px; padding: 12px 18px; max-width: 70%; font-size: 15px; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }
    .chat-row-ai { display: flex; justify-content: flex-start; margin: 8px 0; }
    .chat-bubble-ai { background-color: white; color: #202124; border-radius: 18px 18px 18px 4px; padding: 12px 18px; max-width: 70%; font-size: 15px; box-shadow: 0 2px 6px rgba(0,0,0,0.08); }
    .thinking-expander { background-color: #fef9e7; border-left: 4px solid #f4b400; padding: 8px; border-radius: 6px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# ---------- 加载 API Key ----------
load_dotenv("D:/my_ai_test/.env")  # 本地开发用，云端可忽略
api_key = st.secrets.get("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    st.error("未找到 API Key！")
    st.stop()

client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

# ---------- 初始化 Supabase ----------
supabase_url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
supabase_key = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
if not supabase_url or not supabase_key:
    st.error("未配置 Supabase，请设置 Secrets 中的 SUPABASE_URL 和 SUPABASE_KEY。")
    st.stop()

supabase: Client = create_client(supabase_url, supabase_key)

# ---------- 房间名（多会话支持） ----------
query_params = st.query_params
room = query_params.get("room", "default")
if isinstance(room, list):
    room = room[0]

with st.sidebar:
    st.title("🤖 控制台")
    new_room = st.text_input("聊天室名称", value=room, help="相同房间名的设备将共享聊天记录")
    if new_room != room:
        st.query_params["room"] = new_room
        room = new_room
        st.rerun()

    if st.button("✨ 新对话", use_container_width=True):
        # 删除当前房间的数据库记录
        supabase.table("chats").delete().eq("session_id", room).execute()
        st.session_state.messages = []
        st.rerun()
    st.markdown("---")
    st.caption("房间名相同则聊天记录跨设备同步。")

# ---------- 从 Supabase 加载消息 ----------
def load_messages():
    try:
        response = supabase.table("chats").select("messages").eq("session_id", room).order("created_at", desc=False).execute()
        if response.data and len(response.data) > 0:
            raw = response.data[0]["messages"]
            if isinstance(raw, str):
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return []
            elif isinstance(raw, list):
                return raw
            else:
                return []
        return []
    except Exception as e:
        st.error(f"数据库读取失败: {e}")
        return []

# ---------- 保存消息到 Supabase ----------
def save_messages(messages):
    data = {
        "session_id": room,
        "messages": json.dumps(messages, ensure_ascii=False)
    }
    existing = supabase.table("chats").select("id").eq("session_id", room).execute()
    if existing.data:
        supabase.table("chats").update({"messages": json.dumps(messages, ensure_ascii=False)}).eq("session_id", room).execute()
    else:
        supabase.table("chats").insert(data).execute()

# ---------- 初始化聊天历史 ----------
if "messages" not in st.session_state:
    st.session_state.messages = load_messages()

# ---------- 主界面 ----------
st.title("🤖 DeepSeek 聊天助手")
st.caption("思考模式 · 流式输出 · 跨设备同步 · 永久保存")

# 显示历史消息
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="chat-row-user"><div class="chat-bubble-user">{msg["content"]}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="chat-row-ai"><div class="chat-bubble-ai">{msg["content"]}</div></div>', unsafe_allow_html=True)
        if "reasoning" in msg and msg["reasoning"]:
            with st.expander("🧠 查看思考过程"):
                st.markdown(f'<div class="thinking-expander">{msg["reasoning"]}</div>', unsafe_allow_html=True)

# 用户输入
if prompt := st.chat_input("在这里输入你的问题..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.container():
        st.markdown(f'<div class="chat-row-user"><div class="chat-bubble-user">{prompt}</div></div>', unsafe_allow_html=True)

    # 调用 API（流式+思考模式）
    with st.chat_message("assistant"):
        reasoning_placeholder = st.empty()
        content_placeholder = st.empty()
        reasoning_text = ""
        full_content = ""

        try:
            stream = client.chat.completions.create(
                model="deepseek-v4-pro",
                messages=st.session_state.messages,
                stream=True,
                extra_body={"thinking": {"type": "enabled"}}
            )
            for chunk in stream:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    reasoning_text += delta.reasoning_content
                    with reasoning_placeholder.container():
                        with st.expander("🧠 思考中...", expanded=True):
                            st.markdown(reasoning_text)
                if delta.content:
                    full_content += delta.content
                    content_placeholder.markdown(full_content)

            # 保存完整消息
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_content,
                "reasoning": reasoning_text
            })
            # 保存到 Supabase
            save_messages(st.session_state.messages)
            # 重新渲染
            st.rerun()

        except Exception as e:
            st.error(f"请求出错：{e}")
