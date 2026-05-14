import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv

# ---------- 页面配置 ----------
st.set_page_config(
    page_title="DeepSeek 聊天助手",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="auto",
)

# ---------- 自定义 CSS（美化界面） ----------
st.markdown("""
<style>
    /* 整体背景 */
    .stApp {
        background-color: #f0f2f6;
    }

    /* 聊天气泡：用户消息 */
    .chat-row-user {
        display: flex;
        justify-content: flex-end;
        margin: 8px 0;
    }
    .chat-bubble-user {
        background-color: #1a73e8;
        color: white;
        border-radius: 18px 18px 4px 18px;
        padding: 12px 18px;
        max-width: 70%;
        font-size: 15px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }

    /* 聊天气泡：AI 消息 */
    .chat-row-ai {
        display: flex;
        justify-content: flex-start;
        margin: 8px 0;
    }
    .chat-bubble-ai {
        background-color: white;
        color: #202124;
        border-radius: 18px 18px 18px 4px;
        padding: 12px 18px;
        max-width: 70%;
        font-size: 15px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
    }

    /* 思考过程折叠面板 */
    .thinking-expander {
        background-color: #fef9e7;
        border-left: 4px solid #f4b400;
        padding: 8px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ---------- 加载 API Key ----------
load_dotenv("D:/my_ai_test/.env")
api_key = st.secrets.get("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    st.error("未找到 API Key！请设置 .env 或 Streamlit Secrets。")
    st.stop()

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)

# ---------- 侧边栏：新对话按钮 ----------
with st.sidebar:
    st.title("🤖 控制台")
    if st.button("✨ 新对话", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.markdown("---")
    st.caption("对话历史将在开始新对话时清空。")

# ---------- 主界面标题 ----------
st.title("🤖 DeepSeek 聊天助手")
st.caption("支持思考模式 · 流式回复 · 随时开始新对话")

# ---------- 初始化聊天历史 ----------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------- 显示历史消息（使用聊天气泡） ----------
for idx, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        # 用户消息右对齐
        with st.container():
            st.markdown(f'<div class="chat-row-user"><div class="chat-bubble-user">{msg["content"]}</div></div>',
                        unsafe_allow_html=True)
    else:
        # AI 消息左对齐
        with st.container():
            st.markdown(f'<div class="chat-row-ai"><div class="chat-bubble-ai">{msg["content"]}</div></div>',
                        unsafe_allow_html=True)
        # 如果有思考过程（存储在 extra 里），显示可折叠面板
        if "reasoning" in msg and msg["reasoning"]:
            with st.expander("🧠 查看思考过程"):
                st.markdown(f'<div class="thinking-expander">{msg["reasoning"]}</div>',
                            unsafe_allow_html=True)

# ---------- 用户输入 ----------
if prompt := st.chat_input("在这里输入你的问题..."):
    # 记录并显示用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.container():
        st.markdown(f'<div class="chat-row-user"><div class="chat-bubble-user">{prompt}</div></div>',
                    unsafe_allow_html=True)

    # 调用 API（流式 + 思考模式）
    with st.chat_message("assistant"):
        # 占位符：用于动态显示 AI 回复
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

            # 流式处理
            for chunk in stream:
                delta = chunk.choices[0].delta

                # 处理思考过程
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    reasoning_text += delta.reasoning_content
                    # 实时显示思考过程（折叠框内）
                    with reasoning_placeholder.container():
                        with st.expander("🧠 思考中...", expanded=True):
                            st.markdown(reasoning_text)

                # 处理正式回答
                if delta.content:
                    full_content += delta.content
                    content_placeholder.markdown(full_content)

            # 循环结束，保存消息（含思考过程）
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_content,
                "reasoning": reasoning_text  # 额外存储思考过程
            })

            # 最终显示：如果思考过程不为空，折叠展示；内容已显示
            if reasoning_text:
                with reasoning_placeholder.container():
                    with st.expander("🧠 思考过程（点击展开）", expanded=False):
                        st.markdown(reasoning_text)

            # 因为已经动态显示了，不需要再重复显示 full_content，但为了气泡样式，我们重新渲染整个聊天区
            # 简单做法：调用 rerun 刷新页面，让历史消息重新用气泡绘制
            st.rerun()

        except Exception as e:
            st.error(f"请求出错：{e}")
