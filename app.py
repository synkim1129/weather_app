import streamlit as st
from weather import get_answer, get_info

st.title("Weather Agent")

# 사용자 질문 입력 받기
question = st.text_input("질문을 입력하세요:")

# 질문 전송 버튼
if st.button("질문 전송"):
    if question:
        with st.spinner("답변을 기다리는 중..."):
            weather_info, answer = get_answer(question)
        st.markdown("### 답변")
        st.markdown(answer)
        st.markdown("### 관련 날씨 정보")
        st.markdown(weather_info)
    else:
        st.markdown("질문을 입력해 주세요.")

# 내일 날씨 버튼
if st.button("내일 날씨"):
    with st.spinner("정보를 가져오는 중..."):
        info = get_info()
    st.markdown(info)