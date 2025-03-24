import datetime
import requests
import json
import pandas as pd
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_community.chat_models import ChatOllama
from pydantic import BaseModel, Field
from typing import List


llm=ChatOllama(model="exaone3.5:32b",
            base_url='http://183.101.208.30:63001',)

df_coord = pd.read_csv("./data/coordinate.csv")

KEY_DICT = {
    'T1H': ['기온', '°C'],
    'TMP': ['기온', '°C'],
    'RN1': ['1시간 강수량(mm)', ''],
    'SKY': ['하늘상태', ''],
    # 'UUU': ['동서바람성분', 'm/s'],
    # 'VVV': ['남북바람성분', 'm/s'],
    'REH': ['습도', '%'],
    'PTY': ['강수형태', ''],
    # 'VEC': ['풍향', ''],
    'WSD': ['풍속', 'm/s'],
    'SKY': ['하늘상태', ''],
}

DEG_CODE = {0 : 'N', 360 : 'N', 180 : 'S', 270 : 'W', 90 : 'E', 22.5 :'NNE', 45 : 'NE', 67.5 : 'ENE', 112.5 : 'ESE', 135 : 'SE', 157.5 : 'SSE', 202.5 : 'SSW', 225 : 'SW', 247.5 : 'WSW', 292.5 : 'WNW', 315 : 'NW', 337.5 : 'NNW'}
PTY_CODE = {0 : '강수 없음', 1 : '비', 2 : '비/눈', 3 : '눈', 5 : '빗방울', 6 : '진눈깨비', 7 : '눈날림'}
SKY_CODE = {1 : '맑음', 3 : '구름 많음', 4 : '흐림'}

def deg_to_dir(deg):
    close_dir = ''
    min_abs = 360
    if deg not in DEG_CODE.keys():
        for key in DEG_CODE.keys():
            if abs(key - deg) < min_abs:
                min_abs = abs(key - deg)
                close_dir = DEG_CODE[key]
    else: 
        close_dir = DEG_CODE[deg]
    return close_dir

def pty_to_str(pyt):
    return PTY_CODE[pyt]

def sky_to_str(sky):
    return SKY_CODE[sky]

def get_region_1():
    return df_coord['region_1'].unique()

def get_region_2(region_1):
    return df_coord[df_coord['region_1'] == region_1]['region_2'].unique()

def get_region_3(region_1, region_2):
    return df_coord[(df_coord['region_1'] == region_1) & (df_coord['region_2'] == region_2)]['region_3'].unique()

def get_coord(region_1, region_2, region_3):
    return df_coord[(df_coord['region_1'] == region_1) & (df_coord['region_2'] == region_2) & (df_coord['region_3'] == region_3)][['nx', 'ny']].values[0]

def get_region_str(region_1, region_2, region_3):
    if region_2 == '-':
        return region_1
    if region_3 == '-':
        return region_1 + ' ' + region_2
    return region_1 + ' ' + region_2 + ' ' + region_3


class DatetimeInfo(BaseModel):
    year: str = Field(description="년도, 4 digits")
    month: str = Field(description="월, 2 digits(01~12)")
    day: str = Field(description="일, 2 digits(01~31)")
    hour: str = Field(description="시, 2 digits(00~23)")
    minute: str = Field(description="분, 2 digits(00~59)")
    
class DatetimeList(BaseModel):
    dates: List[DatetimeInfo] = Field(description="추출된 날짜 리스트")

def get_current_datetime():
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M")

def get_datetime_from_query(query):
    instruction_datetime = """
    사용자의 쿼리에서 어떤 날짜와 시간의 날씨 정보를 조회해야 하는지 알려주세요. 필요한 모든 날짜 및 시간을 제공하세요. 별도의 정보가 없다면 현재의 정보를 알려주세요. 날짜와 시간 정보 외의 불필요한 텍스트는 제거하세요.

    현재 날짜 및 시간: {current_datetime}
    Query: {query}

    Format:
    {format}
    """
    parser = PydanticOutputParser(pydantic_object=DatetimeList)
    prompt_get_datetime = PromptTemplate(
        template=instruction_datetime,
        input_variables=["query"],
        partial_variables={
            "current_datetime": get_current_datetime
        }
    ).partial(format=parser.get_format_instructions())
    chain = prompt_get_datetime | llm | parser
    response_datetime = chain.invoke(query)
    return response_datetime


class NoInformationError(Exception):
    pass

def ultra_short_ncst(base_date, base_time, location, nx, ny):
    url = f"https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstInfoService_2.0/getUltraSrtNcst?pageNo=1&numOfRows=100&dataType=JSON&base_date={base_date}&base_time={base_time}&nx={nx}&ny={ny}&authKey=aI3zL9-gS3uN8y_foAt71A"
    response = requests.get(url)
    try:
        result = json.loads(response.text)['response']['body']['items']['item']
    except:
        raise NoInformationError(response.text)

    informations = {}
    for item in result:
        category = item['category']
        value = item['obsrValue']
        if category in KEY_DICT.keys():
            if category == 'VEC':
                # value = deg_to_dir(float(value))
                continue
            if category == 'PTY':
                value = pty_to_str(int(value))
            informations[KEY_DICT[category][0]] = value + KEY_DICT[category][1]

    weather_info = f"""__{base_date[:4]}년 {base_date[4:6]}월 {base_date[-2:]}일 {base_time[:2]}시 {base_time[2:]}분 {location}의 날씨:__ \n""" 
    for key, value in informations.items():
        weather_info += f"   - {key} : {value}\n"
    return weather_info

def ultra_short_fcst(base_date, base_time, location, nx, ny):
    current_time = datetime.datetime.now().strftime("%H%M")
    url = f"https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstInfoService_2.0/getUltraSrtFcst?pageNo=1&numOfRows=100&dataType=JSON&base_date={base_date}&base_time={current_time}&nx={nx}&ny={ny}&authKey=aI3zL9-gS3uN8y_foAt71A"
    response = requests.get(url)
    try:
        result = json.loads(response.text)['response']['body']['items']['item']
    except:
        raise NoInformationError(response.text)
    
    # target_time보다 작거나 같은 값 중에서 가장 가까운 시간 찾기
    available_times = [item['fcstTime'] for item in result if item['fcstDate'] == base_date]
    closest_time = max([time for time in available_times if time <= base_time], default=None)

    informations = {}
    for item in result:
        if item['fcstTime'] == closest_time:
            category = item['category']
            value = item['fcstValue']
            if category in KEY_DICT.keys():
                if category == 'VEC':
                    # value = deg_to_dir(float(value))
                    continue
                if category == 'PTY':
                    value = pty_to_str(int(value))
                if category == 'SKY':
                    value = sky_to_str(int(value))
                informations[KEY_DICT[category][0]] = value + KEY_DICT[category][1]

    if not informations:
        raise NoInformationError("No information available")

    weather_info = f"""__{base_date[:4]}년 {base_date[4:6]}월 {base_date[-2:]}일 {base_time[:2]}시 {base_time[2:]}분 {location}의 날씨:__ \n""" 
    for key, value in informations.items():
        weather_info += f"   - {key} : {value}\n"
    return weather_info


# 단기예보 데이터 추출
def extract_closest_forecast(data, target_date, target_time):
    items = data['response']['body']['items']['item']
    
    available_times = [item['fcstTime'] for item in items if item['fcstDate'] == target_date]
    closest_time = max([time for time in available_times if time <= target_time], default=None)
    
    if closest_time is None:
        return []  # 해당 날짜에 유효한 시간이 없을 경우 빈 리스트 반환
    
    # 해당 날짜와 가장 가까운 시간에 해당하는 데이터 필터링
    filtered_items = [item for item in items if item['fcstDate'] == target_date and item['fcstTime'] == closest_time]
    
    return filtered_items

def short_fcst(base_date, base_time, location, nx, ny):
    current_date = datetime.datetime.now().strftime("%Y%m%d")
    url = f"https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstInfoService_2.0/getVilageFcst?pageNo=1&numOfRows=1000&dataType=JSON&base_date={current_date}&base_time=0500&nx={nx}&ny={ny}&authKey=aI3zL9-gS3uN8y_foAt71A"
    try:
        response = requests.get(url)
        result = extract_closest_forecast(json.loads(response.text), base_date, base_time)
    except:
        raise NoInformationError(response.text)
    
    informations = {}
    for item in result:
        category = item['category']
        value = item['fcstValue']
        if category in KEY_DICT.keys():
            if category == 'VEC':
                # value = deg_to_dir(float(value))
                continue
            if category == 'PTY':
                value = pty_to_str(int(value))
            if category == 'SKY':
                value = sky_to_str(int(value))
            informations[KEY_DICT[category][0]] = value + KEY_DICT[category][1]

    weather_info = f"""__{base_date[:4]}년 {base_date[4:6]}월 {base_date[-2:]}일 {base_time[:2]}시 {base_time[2:]}분 {location}의 날씨:__ \n""" 
    for key, value in informations.items():
        weather_info += f"   - {key} : {value}\n"
    return weather_info

def get_answer(query, region_1, region_2, region_3):
    location = get_region_str(region_1, region_2, region_3)
    nx, ny = get_coord(region_1, region_2, region_3)
    response_datetime = get_datetime_from_query(query)
    print(response_datetime)
    weather_info = ""
    for date in response_datetime.dates:
        date_dict = date.model_dump()
        base_date = f"{date_dict['year']}{date_dict['month']}{date_dict['day']}"
        base_time = f"{date_dict['hour']}{date_dict['minute']}"
        try:
            weather_info += ultra_short_ncst(base_date, base_time, location, nx, ny) # 초단기 실황
        except NoInformationError as e:
            try: 
                weather_info += ultra_short_fcst(base_date, base_time, location, nx, ny) # 초단기 예보
            except NoInformationError as e:
                weather_info += short_fcst(base_date, base_time, location, nx, ny) # 단기 예보보
        weather_info += "\n\n"
    
    
    instruction = """
    당신은 날씨 정보를 토대로 사용자에게 조언을 제공하는 비서입니다. 다음의 날씨 정보와 사용자의 일정 혹은 질문을 토대로 사용자에게 조언을 제공해주세요.

    사용자 위치: {location}
    
    오늘 날짜: {current_datetime}
    
    날씨 정보:
    {weather_info}

    사용자 일정/사용자 질문:
    {query}

    """
    current_datetime = get_current_datetime()
    prompt = ChatPromptTemplate.from_template(instruction)

    # 체인 생성
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"location": location, "current_datetime": current_datetime, "weather_info": weather_info, "query": query})

    return weather_info, answer

def get_info():
    # 사용자 일정을 토대로 내일 날씨 안내 및 조언언
    return "TODO: 사용자 일정을 토대로 내일 날씨 안내 및 조언"

