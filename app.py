import streamlit as st
import google.generativeai as genai
# import gspread # 나중에 실제 연동 시 사용
# from oauth2client.service_account import ServiceAccountCredentials
import requests
import json
import os


# ==========================================
# 1. Configuration & Data Structures
# ==========================================

# 페이지 설정
st.set_page_config(
    page_title="AI Smart Notification",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 7대 업종별 체크리스트 데이터 (Pre-defined Checklists)
INDUSTRY_TEMPLATES = {
    "Child Care": {
        "icon": "👶",
        "items": {
            "mood": {"type": "radio", "label": "기분 (Mood)", "options": ["매우 좋음", "좋음", "보통", "조금 칭얼댐", "컨디션 저조"]},
            "meal": {"type": "slider", "label": "식사량 (Meal Intake)", "min": 0, "max": 100, "step": 10, "unit": "%"},
            "nap": {"type": "radio", "label": "낮잠 (Nap)", "options": ["안 잠", "30분 미만", "1시간", "1시간 30분", "2시간 이상"]},
            "toilet": {"type": "multiselect", "label": "배변 (Toilet)", "options": ["소변", "대변", "실수함", "특이사항 없음"]},
            "activity": {"type": "text", "label": "주요 활동 (Activity)", "placeholder": "예: 블록 놀이, 그림 그리기"},
            "health": {"type": "checkbox", "label": "건강 체크 (Health)", "options": ["열이 조금 있음", "콧물", "기침", "상처/멍"]}
        }
    },
    "Dog Kindergarten": {
        "icon": "🐶",
        "items": {
            "condition": {"type": "radio", "label": "컨디션 (Condition)", "options": ["날아다님", "활발함", "차분함", "피곤해함", "아파보임"]},
            "poop": {"type": "radio", "label": "배변 상태 (Stool)", "options": ["양호 (Good)", "묽음 (Soft)", "설사 (Diarrhea)", "없음 (None)"]},
            "food": {"type": "checkbox", "label": "식사/간식 (Intake)", "options": ["사료 완밥", "사료 남김", "간식 먹음", "약 복용"]},
            "play": {"type": "multiselect", "label": "활동/놀이 (Play)", "options": ["공놀이", "터그놀이", "노즈워크", "술래잡기", "수영"]},
            "social": {"type": "slider", "label": "사회성 (Social)", "min": 1, "max": 5, "help": "1:혼자 돎 ~ 5:핵인싸"},
            "rest": {"type": "radio", "label": "휴식 (Rest)", "options": ["충분히 잠", "중간중간 쉼", "거의 안 쉼"]}
        }
    },
    "Dog Grooming": {
        "icon": "✂️",
        "items": {
            "style": {"type": "text", "label": "미용 스타일 (Style)", "placeholder": "예: 스포팅, 곰돌이컷, 3mm 클리핑"},
            "tangle": {"type": "slider", "label": "털 엉킴 (Tangles)", "min": 1, "max": 5, "help": "1:없음 ~ 5:심함(추가요금)"},
            "manner": {"type": "radio", "label": "미용 매너 (Manner)", "options": ["천사", "얌전함", "보통", "조금 싫어함", "입질 있음"]},
            "skin": {"type": "multiselect", "label": "피부/건강 (Skin/Health)", "options": ["습진", "각질", "귀 발적", "슬개골 주의", "사마귀"]},
            "procedure": {"type": "checkbox", "label": "시술 내용 (Procedures)", "options": ["목욕", "위생미용", "전체미용", "스파", "팩"]}
        }
    },
    "Senior Care": {
        "icon": "👵",
        "items": {
            "vitals": {"type": "text", "label": "바이탈 (Vitals)", "placeholder": "혈압 120/80, 체온 36.5"},
            "meal_amount": {"type": "radio", "label": "식사량 (Intake)", "options": ["전량 섭취", "1/2 섭취", "소량 섭취", "거부"]},
            "medication": {"type": "radio", "label": "투약 (Meds)", "options": ["투약 완료", "미투약", "거부"]},
            "mood_senior": {"type": "radio", "label": "기분 (Mood)", "options": ["평온함", "즐거움", "우울함", "불안함"]},
            "activity_physical": {"type": "multiselect", "label": "신체 활동 (Activity)", "options": ["산책", "체조", "물리치료", "인지 프로그램"]},
            "sleep": {"type": "radio", "label": "수면 (Sleep)", "options": ["숙면", "자다 깸", "불면"]}
        }
    },
    "Academy": {
        "icon": "📚",
        "items": {
            "progress": {"type": "text", "label": "오늘의 진도 (Progress)", "placeholder": "예: 수학 3단원, 영어 단어 20개"},
            "attitude": {"type": "slider", "label": "수업 태도 (Attitude)", "min": 1, "max": 10, "help": "10점 만점"},
            "homework": {"type": "radio", "label": "과제 수행 (Homework)", "options": ["완벽 수행", "대부분 수행", "일부 수행", "미수행"]},
            "understanding": {"type": "radio", "label": "이해도 (Understanding)", "options": ["빠름", "보통", "노력이 필요함"]},
            "notice": {"type": "checkbox", "label": "알림 사항 (Notice)", "options": ["교재비 납부", "보강 필요", "다음 주 휴강", "시험 예정"]}
        }
    },
    "Sports (Taekwondo/Gym)": {
        "icon": "🥋",
        "items": {
            "program": {"type": "text", "label": "운동 프로그램 (Program)", "placeholder": "예: 품새, 줄넘기, 스파링"},
            "energy": {"type": "slider", "label": "에너지 레벨 (Energy)", "min": 1, "max": 10},
            "manners": {"type": "radio", "label": "예절/태도 (Manners)", "options": ["모범적임", "바름", "주의 산만", "지도가 필요함"]},
            "performance": {"type": "radio", "label": "수행 능력 (Performance)", "options": ["탁월함", "성실함", "보통", "어려워함"]},
            "friends": {"type": "radio", "label": "교우 관계 (Social)", "options": ["리더십 발휘", "잘 어울림", "다툼 있었음"]}
        }
    },
    "PT / Pilates": {
        "icon": "💪",
        "items": {
            "body_part": {"type": "multiselect", "label": "운동 부위 (Parts)", "options": ["상체", "하체", "코어", "전신", "유산소"]},
            "intensity": {"type": "slider", "label": "수행 강도 (Intensity)", "min": 1, "max": 10},
            "condition_pt": {"type": "text", "label": "통증/컨디션 (Pain/Condition)", "placeholder": "예: 허리 통증 호소, 컨디션 좋음"},
            "diet": {"type": "radio", "label": "식단 체크 (Diet)", "options": ["잘 지킴", "보통", "폭식함", "피드백 필요"]},
            "next_goal": {"type": "text", "label": "다음 목표 (Next Goal)", "placeholder": "예: 스쿼트 중량 증량, 체지방 감량"}
        }
    }
}

# 다국어 팩 (Language Pack)
LANG_PACK = {
    "Korean": {
        "title": "AI 스마트 알림장",
        "select_industry": "업종을 선택하세요",
        "generate_btn": "AI 알림장 생성하기",
        "result_header": "생성된 알림장",
        "memo_label": "특이사항 / 메모 (직접 입력)",
        "login_fail": "로그인에 실패했습니다.",
        "welcome": "환영합니다, 사용자님!",
        "sidebar_title": "설정",
        "industries": {
            "Child Care": "어린이집",
            "Dog Kindergarten": "애견 유치원",
            "Dog Grooming": "애견 미용",
            "Senior Care": "요양 보호 (시니어 케어)",
            "Academy": "학원 / 공부방",
            "Sports (Taekwondo/Gym)": "태권도 / 체육관",
            "PT / Pilates": "PT / 필라테스"
        },
        "customer_label": "고객 이름 (아이/반려견/회원명)",
        "store_label": "매장/기관 이름"
    },
    "English": {
        "title": "AI Smart Notification",
        "select_industry": "Select Industry",
        "generate_btn": "Generate Notification",
        "result_header": "Generated Notification",
        "memo_label": "Special Notes / Memo (Manual Input)",
        "login_fail": "Login failed.",
        "welcome": "Welcome, User!",
        "sidebar_title": "Settings",
        "industries": {
            "Child Care": "Child Care",
            "Dog Kindergarten": "Dog Kindergarten",
            "Dog Grooming": "Dog Grooming",
            "Senior Care": "Senior Care",
            "Academy": "Academy",
            "Sports (Taekwondo/Gym)": "Sports (Taekwondo/Gym)",
            "PT / Pilates": "PT / Pilates"
        },
        "customer_label": "Customer Name (Child/Pet/Member)",
        "store_label": "Store/Institution Name"
    },
    "Japanese": {
        "title": "AI スマート連絡帳",
        "select_industry": "業種を選択してください",
        "generate_btn": "AI 連絡帳を作成",
        "result_header": "作成された連絡帳",
        "memo_label": "特記事項 / メモ (直接入力)",
        "login_fail": "ログインに失敗しました。",
        "welcome": "ようこそ、ユーザー様！",
        "sidebar_title": "設定",
        "industries": {
            "Child Care": "保育園",
            "Dog Kindergarten": "犬の幼稚園",
            "Dog Grooming": "トリミングサロン",
            "Senior Care": "介護 (シニアケア)",
            "Academy": "塾 / 教室",
            "Sports (Taekwondo/Gym)": "テコンドー / ジム",
            "PT / Pilates": "パーソナルトレーニング"
        },
        "customer_label": "お客様の名前 (子供/ペット/会員)",
        "store_label": "店舗/施設名"
    }
}

# ==========================================
# 2. Helper Functions
# ==========================================

def detect_language():
    """
    간단한 언어 감지 로직. (실제 배포 시 request headers 활용)
    여기서는 한국어를 기본값으로 설정.
    """
    return "Korean"

def check_login():
    """
    Google Sheets 연동 로그인 시뮬레이션.
    실제 구현 시 gspread로 유저 DB 시트를 조회.
    """
    # 실제 연동 코드는 주석 처리
    # scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    # creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
    # client = gspread.authorize(creds)
    # ...
    return True # 무조건 로그인 성공으로 처리 (데모용)

def generate_ai_content(api_key, industry, data_summary, lang, customer_name, store_name):
    """
    Gemini API를 사용하여 알림장 텍스트 생성
    """
    if not api_key:
        return "⚠️ 오류: Gemini API 키가 설정되지 않았습니다. 사이드바에서 키를 입력해주세요."
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemma-3-27b-it')
        
        prompt = f"""
        당신은 {industry} 분야의 베테랑 전문가입니다.
        아래 입력된 항목들을 바탕으로 고객(학부모/보호자/회원)에게 보낼 정중하고 전문적인 '일일 알림장(리포트)'을 작성해주세요.
        
        [기본 정보]
        - 수신자(아이/반려견/회원 이름): {customer_name}
        - 발신자(매장/기관 이름): {store_name}

        [입력 데이터]
        {data_summary}
        
        [지시사항]
        1. 언어: {lang}
        2. 분량: 300~500자 내외
        3. 톤앤매너: 친절함, 전문적, 신뢰감
        4. 형식:
           - 인사말 (반드시 수신자 이름을 포함)
           - 주요 활동 및 상태 요약 (입력된 데이터 기반)
           - 긍정적인 피드백 또는 당부 사항
           - 마무리 인사 (반드시 발신자 이름을 포함)
        5. 이모지를 적절히 사용하여 가독성을 높여주세요.
        6. **중요**: 마크다운 헤더('#')는 절대 사용하지 마세요. 대신 굵은 글씨('**')나 구분선 등을 사용하세요.
        """
        
        with st.spinner('AI가 알림장을 작성 중입니다... (Writing report...)'):
            response = model.generate_content(prompt)
            return response.text
    except Exception as e:
        return f"⚠️ 에러 발생: {str(e)}"

# ==========================================
# 3. Main Application Logic
# ==========================================

def main():
    # 1. 초기 설정 (언어 및 로그인)
    if "lang" not in st.session_state:
        st.session_state.lang = detect_language()
    
    # 사이드바 설정
    with st.sidebar:
        st.title(LANG_PACK[st.session_state.lang]["sidebar_title"])
        
        # 언어 변경
        selected_lang = st.selectbox(
            "Language", 
            ["Korean", "English", "Japanese"], 
            index=["Korean", "English", "Japanese"].index(st.session_state.lang)
        )
        if selected_lang != st.session_state.lang:
            st.session_state.lang = selected_lang
            st.rerun()

        # API Key (secrets.toml에서 로드)
        if "GEMINI_API_KEY" in st.secrets:
             api_key = st.secrets["GEMINI_API_KEY"]
             # st.sidebar.success("API Key Loaded secure!") 
        else:
             api_key = st.text_input("Gemini API Key", type="password")
             if not api_key:
                st.warning("API Key가 필요합니다.")

        st.divider()
        st.info("💡 **Tip**: 7개 업종별 템플릿을 사용하여 빠르고 간편하게 알림장을 작성하세요.")

    # 2. 메인 타이틀
    st.title(LANG_PACK[st.session_state.lang]["title"])

    # 로그인 체크
    if not check_login():
        st.error(LANG_PACK[st.session_state.lang]["login_fail"])
        return
    
    # 3. 업종 선택
    st.subheader("1. " + LANG_PACK[st.session_state.lang]["select_industry"])
    
    industry_names = list(INDUSTRY_TEMPLATES.keys())
    # 보기 좋게 아이콘과 함께 표시하기 위한 포맷팅
    def format_func(key):
        return f"{INDUSTRY_TEMPLATES[key]['icon']} {LANG_PACK[st.session_state.lang]['industries'][key]}"

    # 공통 입력 필드 (매장 이름, 고객 이름)
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        store_name = st.text_input(LANG_PACK[st.session_state.lang]["store_label"], placeholder="예: 햇살 어린이집, 멍멍 유치원")
    with col_info2:
        customer_name = st.text_input(LANG_PACK[st.session_state.lang]["customer_label"], placeholder="예: 김철수, 뽀삐")
        
    st.divider()

    selected_industry_key = st.radio("", industry_names, format_func=format_func, horizontal=True)
    
    if selected_industry_key:
        template = INDUSTRY_TEMPLATES[selected_industry_key]
        st.markdown(f"### {template['icon']} {selected_industry_key}")
        
        # 4. 동적 폼 생성 (Dynamic Form Generation)
        user_inputs = {}
        
        # UI 레이아웃을 위해 컬럼 분할 (2열)
        col1, col2 = st.columns(2)
        items = list(template["items"].items())
        half = (len(items) + 1) // 2
        
        # 왼쪽 컬럼
        with col1:
            for key, config in items[:half]:
                if config["type"] == "radio":
                    user_inputs[key] = st.radio(config["label"], config["options"], key=key)
                elif config["type"] == "checkbox":
                    # Checkbox group implementation via multiselect or customized checkboxes
                    # 여기서는 여러 옵션을 선택할 수 있는 multiselect가 더 깔끔함.
                    # 단, config['type']이 checkbox지만 실제로는 다중 선택 의미라면 multiselect 권장
                    # 사용자 요청 스펙에 'Checkbox'가 있으므로, UI 적 구현을 위해 multiselect 로 대체하거나 여러개 st.checkbox 생성
                    # 여기서는 'options' 리스트가 있으므로 multiselect가 적합
                    if "options" in config:
                        user_inputs[key] = st.multiselect(config["label"], config["options"], key=key)
                    else:
                        # 단일 체크박스
                        user_inputs[key] = st.checkbox(config["label"], key=key)
                elif config["type"] == "slider":
                    user_inputs[key] = st.slider(config["label"], 
                                                 min_value=config.get("min", 0), 
                                                 max_value=config.get("max", 10),
                                                 step=config.get("step", 1),
                                                 help=config.get("help", ""),
                                                 key=key)
                elif config["type"] == "text":
                    user_inputs[key] = st.text_input(config["label"], placeholder=config.get("placeholder", ""), key=key)
                elif config["type"] == "multiselect":
                    user_inputs[key] = st.multiselect(config["label"], config["options"], key=key)

        # 오른쪽 컬럼
        with col2:
            for key, config in items[half:]:
                # 위와 동일한 로직 (함수로 빼면 좋지만 직관성을 위해 반복)
                if config["type"] == "radio":
                    user_inputs[key] = st.radio(config["label"], config["options"], key=key)
                elif config["type"] == "checkbox":
                    if "options" in config:
                        user_inputs[key] = st.multiselect(config["label"], config["options"], key=key)
                    else:
                        user_inputs[key] = st.checkbox(config["label"], key=key)
                elif config["type"] == "slider":
                    user_inputs[key] = st.slider(config["label"], 
                                                 min_value=config.get("min", 0), 
                                                 max_value=config.get("max", 10),
                                                 step=config.get("step", 1),
                                                 help=config.get("help", ""),
                                                 key=key)
                elif config["type"] == "text":
                    user_inputs[key] = st.text_input(config["label"], placeholder=config.get("placeholder", ""), key=key)
                elif config["type"] == "multiselect":
                    user_inputs[key] = st.multiselect(config["label"], config["options"], key=key)

        # 공통: 특이사항 메모
        st.markdown("---")
        memo = st.text_area(LANG_PACK[st.session_state.lang]["memo_label"], height=100)
        user_inputs["memo"] = memo

        # 5. 생성 버튼 및 AI 요청
        if st.button(LANG_PACK[st.session_state.lang]["generate_btn"], type="primary", use_container_width=True):
            # 입력값 정리 (프롬프트용 문자열 생성)
            data_summary = ""
            for k, v in user_inputs.items():
                # 리스트인 경우 (multiselect)
                if isinstance(v, list):
                    v_str = ", ".join(v) if v else "없음"
                else:
                    v_str = str(v)
                
                # 라벨 찾기 (memo 제외)
                label = k
                if k in template["items"]:
                    label = template["items"][k]["label"]
                
                data_summary += f"- {label}: {v_str}\n"

            # AI 생성 호출
            result_text = generate_ai_content(api_key, selected_industry_key, data_summary, st.session_state.lang, customer_name, store_name)
            
            # 6. 결과 출력
            st.divider()
            st.subheader(LANG_PACK[st.session_state.lang]["result_header"])
            st.success("✅ 작성이 완료되었습니다!")
            st.text_area("Result", value=result_text, height=400)
            
            # 복사 기능 (Streamlit 실험적 기능 활용 or 텍스트 선택 유도)
            st.caption("위 텍스트를 복사하여 사용하세요.")

if __name__ == "__main__":
    main()
