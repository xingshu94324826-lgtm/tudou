import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv

# ---------- 加载 API Key ----------
load_dotenv("D:/my_ai_test/.env")
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

# ---------- 网页标题 ----------
st.set_page_config(page_title="DeepSeek 聊天助手", page_icon="🤖")
st.title("🤖 DeepSeek 聊天助手")

# ---------- 初始化聊天历史（保存在会话中） ----------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------- 显示历史消息 ----------
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# ---------- 用户输入框 ----------
if prompt := st.chat_input("在这里输入你的问题..."):
    # 显示用户消息
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 调用 DeepSeek API
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            response = client.chat.completions.create(
                model="deepseek-v4-pro",
                messages=st.session_state.messages,
                stream=False
            )
            reply = response.choices[0].message.content
            st.write(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})