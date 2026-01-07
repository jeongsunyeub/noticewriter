import streamlit as st
import google.generativeai as genai
import requests
import json
import os

# ==========================================
# 1. Configuration & Data Structures
# ==========================================

st.set_page_config(
    page_title="AI Smart Notification",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 7대 업종별 체크리스트 데이터 (Updated V2)
# 'type': 'multiselect_dynamic' -> User can add/remove items. Default is all options.
INDUSTRY_TEMPLATES = {
    "Child Care": {
        "icon": "👶",
        "label_ko": "어린이집/유치원 (아이 돌봄)",
        "label_en": "Child Care / Kindergarten",
        "label_ja": "保育園 / 幼稚園",
        "is_pet": False,
        "items": {
            "mood": {"type": "radio", "label": "기분 (Mood)", "options": ["매우 좋음", "좋음", "보통", "조금 칭얼댐", "컨디션 저조"]},
            "meal": {"type": "slider", "label": "식사량 (Meal Intake)", "min": 0, "max": 100, "step": 10, "unit": "%"},
            "nap": {"type": "radio", "label": "낮잠 (Nap)", "options": ["안 잠", "30분 미만", "1시간", "1시간 30분", "2시간 이상"]},
            "toilet": {"type": "multiselect_dynamic", "label": "배변 (Toilet)", "options": ["소변", "대변", "실수함", "특이사항 없음"]},
            "activity": {"type": "multiselect_dynamic", "label": "주요 활동 (Activity)", "options": ["블록 놀이", "그림 그리기", "동화책 읽기", "바깥 놀이", "율동 시간"]},
            "health": {"type": "multiselect_dynamic", "label": "건강 체크 (Health)", "options": ["열이 조금 있음", "콧물", "기침", "상처/멍", "매우 건강함"]}
        }
    },
    "Dog Kindergarten": {
        "icon": "🐶",
        "label_ko": "애견 유치원",
        "label_en": "Dog Kindergarten",
        "label_ja": "犬の幼稚園",
        "is_pet": True,
        "items": {
            "condition": {"type": "radio", "label": "컨디션 (Condition)", "options": ["날아다님", "활발함", "차분함", "피곤해함", "아파보임"]},
            "poop": {"type": "radio", "label": "배변 상태 (Stool)", "options": ["양호 (Good)", "묽음 (Soft)", "설사 (Diarrhea)", "없음 (None)"]},
            "food": {"type": "multiselect_dynamic", "label": "식사/간식 (Intake)", "options": ["사료 완밥", "사료 남김", "간식 먹음", "약 복용"]},
            "play": {"type": "multiselect_dynamic", "label": "활동/놀이 (Play)", "options": ["공놀이", "터그놀이", "노즈워크", "술래잡기", "수영", "낮잠 시간"]},
            "social": {"type": "slider", "label": "사회성 (Social)", "min": 1, "max": 5, "help": "1:혼자 돎 ~ 5:핵인싸"},
            "rest": {"type": "radio", "label": "휴식 (Rest)", "options": ["충분히 잠", "중간중간 쉼", "거의 안 쉼"]}
        }
    },
    "Dog Grooming": {
        "icon": "✂️",
        "label_ko": "애견 미용",
        "label_en": "Dog Grooming",
        "label_ja": "トリミングサロン",
        "is_pet": True,
        "items": {
            "style": {"type": "text", "label": "미용 스타일 (Style)", "placeholder": "예: 스포팅, 곰돌이컷, 3mm 클리핑"},
            "tangle": {"type": "slider", "label": "털 엉킴 (Tangles)", "min": 1, "max": 5, "help": "1:없음 ~ 5:심함(추가요금)"},
            "manner": {"type": "radio", "label": "미용 매너 (Manner)", "options": ["천사", "얌전함", "보통", "조금 싫어함", "입질 있음"]},
            "skin": {"type": "multiselect_dynamic", "label": "피부/건강 (Skin/Health)", "options": ["습진", "각질", "귀 발적", "슬개골 주의", "사마귀", "피부 깨끗함"]},
            "procedure": {"type": "multiselect_dynamic", "label": "시술 내용 (Procedures)", "options": ["목욕", "위생미용", "전체미용", "스파", "팩", "발톱 정리"]}
        }
    },
    "Senior Care": {
        "icon": "👵",
        "label_ko": "요양 보호 (시니어 케어)",
        "label_en": "Senior Care",
        "label_ja": "介護 (シニアケア)",
        "is_pet": False,
        "items": {
            "vitals": {"type": "text", "label": "바이탈 (Vitals)", "placeholder": "혈압 120/80, 체온 36.5"},
            "meal_amount": {"type": "radio", "label": "식사량 (Intake)", "options": ["전량 섭취", "1/2 섭취", "소량 섭취", "거부"]},
            "medication": {"type": "radio", "label": "투약 (Meds)", "options": ["투약 완료", "미투약", "거부"]},
            "mood_senior": {"type": "radio", "label": "기분 (Mood)", "options": ["평온함", "즐거움", "우울함", "불안함"]},
            "activity_physical": {"type": "multiselect_dynamic", "label": "신체 활동 (Activity)", "options": ["산책", "체조", "물리치료", "인지 프로그램", "TV 시청"]},
            "sleep": {"type": "radio", "label": "수면 (Sleep)", "options": ["숙면", "자다 깸", "불면"]}
        }
    },
    "Academy": {
        "icon": "📚",
        "label_ko": "학원 / 공부방",
        "label_en": "Academy",
        "label_ja": "塾 / 教室",
        "is_pet": False,
        "items": {
            "progress": {"type": "text", "label": "오늘의 진도 (Progress)", "placeholder": "예: 수학 3단원, 영어 단어 20개"},
            "attitude": {"type": "slider", "label": "수업 태도 (Attitude)", "min": 1, "max": 10, "help": "10점 만점"},
            "homework": {"type": "radio", "label": "과제 수행 (Homework)", "options": ["완벽 수행", "대부분 수행", "일부 수행", "미수행"]},
            "understanding": {"type": "radio", "label": "이해도 (Understanding)", "options": ["빠름", "보통", "노력이 필요함"]},
            "notice": {"type": "multiselect_dynamic", "label": "알림 사항 (Notice)", "options": ["교재비 납부", "보강 필요", "다음 주 휴강", "시험 예정", "숙제 잘 해옴"]}
        }
    },
    "Sports (Taekwondo/Gym)": {
        "icon": "🥋",
        "label_ko": "태권도 / 체육관",
        "label_en": "Sports (Taekwondo/Gym)",
        "label_ja": "テコンドー / ジム",
        "is_pet": False,
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
        "label_ko": "PT / 필라테스",
        "label_en": "PT / Pilates",
        "label_ja": "パーソナルトレーニング",
        "is_pet": False,
        "items": {
            "body_part": {"type": "multiselect_dynamic", "label": "운동 부위 (Parts)", "options": ["상체", "하체", "코어", "전신", "유산소", "스트레칭"]},
            "intensity": {"type": "slider", "label": "수행 강도 (Intensity)", "min": 1, "max": 10},
            "condition_pt": {"type": "text", "label": "통증/컨디션 (Pain/Condition)", "placeholder": "예: 허리 통증 호소, 컨디션 좋음"},
            "diet": {"type": "radio", "label": "식단 체크 (Diet)", "options": ["잘 지킴", "보통", "폭식함", "피드백 필요"]},
            "next_goal": {"type": "text", "label": "다음 목표 (Next Goal)", "placeholder": "예: 스쿼트 중량 증량, 체지방 감량"}
        }
    }
}

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
        "customer_label": "고객 이름 (아이/반려견/회원명)",
        "store_label": "매장/기관 이름",
        "custom_add": "+ 직접 추가",
        "tier_label": "멤버십 등급",
        "length_label": "글자 수 제한"
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
        "customer_label": "Customer Name (Child/Pet/Member)",
        "store_label": "Store/Institution Name",
        "custom_add": "+ Add Custom",
        "tier_label": "Membership Tier",
        "length_label": "Character Limit"
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
        "customer_label": "お客様の名前 (子供/ペット/会員)",
        "store_label": "店舗/施設名",
        "custom_add": "+ 直接追加",
        "tier_label": "会員ランク",
        "length_label": "文字数制限"
    }
}

# ==========================================
# 2. Helper Functions
# ==========================================

def detect_language():
    return "Korean"

def check_login():
    return True

def generate_ai_content(api_key, industry, data_summary, lang, customer_name, store_name, is_pet, target_length):
    """
    Gemini API를 사용하여 알림장 텍스트 생성
    """
    if not api_key:
        return "⚠️ 오류: API 키가 설정되지 않았습니다 (secrets.toml 확인 필요)."
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemma-3-27b-it')
        
        # Tone & Manner Instructions
        tone_instruction = ""
        if is_pet:
            tone_instruction = "- **주의**: 대상이 '개(반려동물)'이므로, 이름 뒤에 '님'이나 존칭을 붙이지 마세요. (예: '초코님' X -> '초코' O). 보호자에게는 정중하게 존댓말을 사용하세요."
        else:
            tone_instruction = "- 대상(사람)에게 적절한 호칭과 존댓말을 사용하세요."

        prompt = f"""
        당신은 {industry} 분야의 베테랑 전문가입니다.
        아래 입력된 항목들을 바탕으로 고객(학부모/보호자/회원)에게 보낼 정중하고 전문적인 '일일 알림장(리포트)'을 작성해주세요.
        
        [기본 정보]
        - 수신자(이름): {customer_name}
        - 발신자(매장/기관): {store_name}

        [입력 데이터]
        {data_summary}
        
        [지시사항]
        1. 언어: {lang}
        2. 목표 글자 수: 공백 포함 약 {target_length}자
        3. 톤앤매너: 친절함, 전문적, 신뢰감
        {tone_instruction}
        4. 형식:
           - 인사말 (수신자 이름 포함)
           - 주요 활동 및 상태 요약 (데이터 기반으로 자연스럽게 서술)
           - 긍정적인 피드백 또는 당부 사항
           - 마무리 인사 (발신자 이름 포함)
        5. 이모지: 적절히 사용하여 가독성을 높임.
        6. **금지사항**: 마크다운 볼드체('**')는 절대 사용하지 마세요. 모든 텍스트는 일반 텍스트(Plain Text)로 출력하세요.
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
    if "lang" not in st.session_state:
        st.session_state.lang = detect_language()
    
    # ------------------------------------
    # Sidebar: Settings & Tier System
    # ------------------------------------
    with st.sidebar:
        st.title(LANG_PACK[st.session_state.lang]["sidebar_title"])
        
        # Language
        selected_lang = st.selectbox(
            "Language", 
            ["Korean", "English", "Japanese"], 
            index=["Korean", "English", "Japanese"].index(st.session_state.lang)
        )
        if selected_lang != st.session_state.lang:
            st.session_state.lang = selected_lang
            st.rerun()

        st.divider()
        
        # Checking Secrets for API Key
        if "GEMINI_API_KEY" not in st.secrets:
            st.error("❌ `secrets.toml`에 API Key가 없습니다.")
            st.stop()
        api_key = st.secrets["GEMINI_API_KEY"]

        # Tier Simulation
        st.subheader(LANG_PACK[st.session_state.lang]["tier_label"])
        user_tier = st.radio("Membership", ["Free", "Pro"], index=0, horizontal=True)
        
        if user_tier == "Pro":
            target_length = st.select_slider(
                LANG_PACK[st.session_state.lang]["length_label"], 
                options=[300, 600, 900], 
                value=600
            )
        else:
            # Free tier fixed to 50
            target_length = 50
            st.caption(f"Free Plan: {target_length}자 제한")

        st.divider()
        st.info("💡 **Pro Tip**: 유료 회원은 글자 수 조절이 가능합니다.")

    # ------------------------------------
    # Main Content
    # ------------------------------------
    st.title(LANG_PACK[st.session_state.lang]["title"])

    if not check_login():
        st.error(LANG_PACK[st.session_state.lang]["login_fail"])
        return
    
    # Industry Inputs
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        store_name = st.text_input(LANG_PACK[st.session_state.lang]["store_label"], placeholder="매장/기관명")
    with col_info2:
        customer_name = st.text_input(LANG_PACK[st.session_state.lang]["customer_label"], placeholder="이름")
        
    st.divider()

    # Industry Select (Checklist Style Radio)
    st.subheader("1. " + LANG_PACK[st.session_state.lang]["select_industry"])
    
    industry_keys = list(INDUSTRY_TEMPLATES.keys())
    
    # Dynamic Label Function
    def format_func(key):
        template = INDUSTRY_TEMPLATES[key]
        lang_code = st.session_state.lang  # Korean, English, Japanese
        if lang_code == "Korean":
            label = template["label_ko"]
        elif lang_code == "Japanese":
            label = template["label_ja"]
        else:
            label = template["label_en"]
        return f"{template['icon']} {label}"

    selected_industry_key = st.radio("", industry_keys, format_func=format_func, horizontal=False) # Vertical list as requested "Checklist style" often implies vertical radio or checkboxes
    
    if selected_industry_key:
        template = INDUSTRY_TEMPLATES[selected_industry_key]
        st.markdown(f"### {format_func(selected_industry_key)}")
        
        # Dynamic Form
        user_inputs = {}
        
        items = list(template["items"].items())
        col1, col2 = st.columns(2)
        half = (len(items) + 1) // 2
        
        def render_item(key, config):
            value = None
            if config["type"] == "radio":
                value = st.radio(config["label"], config["options"], key=key)
            
            elif config["type"] == "slider":
                value = st.slider(config["label"], 
                                  min_value=config.get("min", 0), 
                                  max_value=config.get("max", 10),
                                  step=config.get("step", 1),
                                  help=config.get("help", ""),
                                  key=key)
            
            elif config["type"] == "text":
                value = st.text_input(config["label"], placeholder=config.get("placeholder", ""), key=key)
            
            elif config["type"] == "multiselect_dynamic":
                # Session State Key for Options
                opt_key = f"{key}_options"
                
                # Initialize options in session state if not exists
                if opt_key not in st.session_state:
                    st.session_state[opt_key] = config["options"].copy()
                
                # Custom Add Logic
                def add_custom_item():
                    new_item = st.session_state[f"{key}_custom_input"]
                    if new_item and new_item not in st.session_state[opt_key]:
                        st.session_state[opt_key].append(new_item)
                        # Optional: Automatically select the new item
                        # st.session_state[f"{key}_select"] = st.session_state.get(f"{key}_select", []) + [new_item]

                # 1. Multiselect (Default empty)
                selected = st.multiselect(
                    config["label"], 
                    options=st.session_state[opt_key], 
                    default=[], # Start empty
                    key=f"{key}_select"
                )
                
                # 2. Add Custom Input (with on_change callback)
                st.text_input(
                    f"{config['label']} ({LANG_PACK[st.session_state.lang]['custom_add']})", 
                    key=f"{key}_custom_input",
                    on_change=add_custom_item
                )
                
                value = selected

            return value

        # Render Columns
        with col1:
            for key, config in items[:half]:
                user_inputs[key] = render_item(key, config)
        with col2:
            for key, config in items[half:]:
                user_inputs[key] = render_item(key, config)

        st.markdown("---")
        memo = st.text_area(LANG_PACK[st.session_state.lang]["memo_label"], height=100)
        user_inputs["memo"] = memo

        # Generate Button
        if st.button(LANG_PACK[st.session_state.lang]["generate_btn"], type="primary", use_container_width=True):
            # Format Data Summary
            data_summary = ""
            for k, v in user_inputs.items():
                if isinstance(v, list):
                    v_str = ", ".join(v) if v else "없음"
                else:
                    v_str = str(v)
                
                label = k
                if k in template["items"]:
                    label = template["items"][k]["label"]
                
                data_summary += f"- {label}: {v_str}\n"

            # Call AI
            result_text = generate_ai_content(
                api_key, 
                selected_industry_key, 
                data_summary, 
                st.session_state.lang, 
                customer_name, 
                store_name,
                template["is_pet"],
                target_length
            )
            
            st.divider()
            st.subheader(LANG_PACK[st.session_state.lang]["result_header"])
            st.success("✅ Complete!")
            st.text_area("Result", value=result_text, height=400)
            st.caption("Copy the text above.")

if __name__ == "__main__":
    main()
