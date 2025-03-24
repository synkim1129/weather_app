import streamlit as st
from weather import get_answer, get_info, get_region_1, get_region_2, get_region_3

st.title("Weather Agent")
st.markdown("### 날씨 정보를 통해 사용자에게 조언을 제공하는 비서입니다.")
st.markdown("__지역 선택__")
region_1 = st.selectbox("1단계 지역 선택", get_region_1(), index=None)
if region_1:
    region_2 = st.selectbox("2단계 지역 선택", get_region_2(region_1))
    if region_2 != '-':
        region_3 = st.selectbox("3단계 지역 선택", get_region_3(region_1, region_2))
    else:
        region_3 = '-'
    
        
    
    
# 사용자 질문 입력 받기
if region_1: 
    question = st.text_input("질문을 입력하세요:")

# 질문 전송 버튼
if st.button("질문 전송"):
    if question:
        with st.spinner("답변을 기다리는 중..."):
            weather_info, answer = get_answer(question, region_1, region_2, region_3)
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