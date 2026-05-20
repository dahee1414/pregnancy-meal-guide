import streamlit as st
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import re

# 페이지 설정
st.set_page_config(
    page_title="임산부 급식 가이드",
    page_icon="👶",
    layout="wide"
)

# 서울과학고등학교 급식 정보 불러오기 함수
# 인증키 없이 공개 급식 조회 페이지를 크롤링하는 방식입니다.

PUBLIC_SCHOOL_CODE = "7010084"      # 서울과학고등학교 공개 페이지 코드
KOREACHARTS_SCHOOL_ID = "B000011789"


def clean_food_line(line):
    """급식 메뉴 한 줄 정리"""
    line = line.strip()
    line = re.sub(r"^[*•\-\s]+", "", line)        # 앞의 *, •, - 제거
    line = re.sub(r"\([^)]*\)", "", line)         # 알레르기 번호, 괄호 설명 제거
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def is_not_menu_line(line):
    """메뉴가 아닌 줄 거르기"""
    skip_keywords = [
        "급식인원수",
        "칼로리",
        "영양정보",
        "탄수화물",
        "단백질",
        "지방",
        "비타민",
        "칼슘",
        "철분",
        "원산지정보",
        "목록으로",
        "학교 급식",
        "검색",
        "주소",
        "전화번호",
        "FAX",
        "Copyright",
    ]
    return any(keyword in line for keyword in skip_keywords)


def extract_meal_by_korean_date(page_text, target_date, meal_type="중식"):
    """
    예: '2026년 04월 24일 중식' 제목 아래의 메뉴를 추출합니다.
    school.yourland.kr, lunch.ourstory.kr 같은 페이지에 대응합니다.
    """
    year = target_date.year
    month = target_date.month
    day = target_date.day

    date_patterns = [
        rf"{year}년\s*{month:02d}월\s*{day:02d}일\s*{meal_type}",
        rf"{year}년\s*{month}월\s*{day}일\s*{meal_type}",
    ]

    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in page_text.split("\n")
        if line.strip()
    ]

    start_idx = None

    for i, line in enumerate(lines):
        if any(re.search(pattern, line) for pattern in date_patterns):
            start_idx = i
            break

    if start_idx is None:
        return None

    menu_items = []

    for line in lines[start_idx + 1:]:
        # 다음 날짜의 조식/중식/석식이 나오면 종료
        if re.search(r"20\d{2}년\s*\d{1,2}월\s*\d{1,2}일\s*(조식|중식|석식)", line):
            break

        # 급식인원수, 칼로리, 영양정보가 나오면 메뉴 구간 종료
        if is_not_menu_line(line):
            break

        cleaned = clean_food_line(line)

        if cleaned and len(cleaned) > 1:
            menu_items.append(cleaned)

    if menu_items:
        return ", ".join(menu_items)

    return None


def extract_meal_from_koreacharts(page_text, target_date, meal_type="중식"):
    """
    koreacharts 월간 급식표 페이지에서 특정 날짜의 중식을 추출합니다.
    """
    day = target_date.day

    # 월간 표에서 '8, 금요일' 같은 날짜 블록 찾기
    block_pattern = rf"(?:^|\n)\s*{day}\s*,[^\n]*\n(.*?)(?=\n\s*\d{{1,2}}\s*,|\Z)"
    block_match = re.search(block_pattern, page_text, flags=re.S)

    if not block_match:
        return None

    block = block_match.group(1)

    # 해당 날짜 블록 안에서 [중식]부터 다음 [조식]/[석식] 전까지 추출
    meal_pattern = rf"\[{meal_type}\](.*?)(?=\n\s*\[(조식|중식|석식)\]|\Z)"
    meal_match = re.search(meal_pattern, block, flags=re.S)

    if not meal_match:
        return None

    meal_text = meal_match.group(1)

    raw_items = [
        item.strip()
        for item in re.split(r"\n| {2,}", meal_text)
        if item.strip()
    ]

    menu_items = []

    for item in raw_items:
        cleaned = clean_food_line(item)
        if cleaned and not is_not_menu_line(cleaned):
            menu_items.append(cleaned)

    if menu_items:
        return ", ".join(menu_items)

    return None


def get_public_page_text(url):
    """공개 웹페이지 HTML을 텍스트로 변환"""
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    return soup.get_text("\n")


def get_school_meal(target_date=None, meal_type="중식"):
    """
    선택한 날짜와 식사 종류의 급식 정보를 인증키 없이 공개 웹페이지에서 불러옵니다.
    meal_type: "중식" 또는 "석식"
    """
    try:
        # 날짜가 없으면 한국 시간 기준 오늘 사용
        if target_date is None:
            target_date = datetime.utcnow() + timedelta(hours=9)

        # st.date_input은 datetime.date를 반환하므로 datetime처럼 쓸 수 있게 처리
        if not hasattr(target_date, "hour"):
            target_date = datetime.combine(target_date, datetime.min.time())

        yyyymm = target_date.strftime("%Y%m")

        public_urls = [
            {
                "name": "yourland",
                "url": f"https://school.yourland.kr/food.php?code={PUBLIC_SCHOOL_CODE}",
                "type": "korean_date",
            },
            {
                "name": "ourstory",
                "url": f"https://lunch.ourstory.kr/food.php?code={PUBLIC_SCHOOL_CODE}",
                "type": "korean_date",
            },
            {
                "name": "koreacharts",
                "url": f"https://school.koreacharts.com/school/meals/{KOREACHARTS_SCHOOL_ID}/{yyyymm}.html",
                "type": "koreacharts",
            },
        ]

        for source in public_urls:
            try:
                page_text = get_public_page_text(source["url"])

                if source["type"] == "korean_date":
                    menu = extract_meal_by_korean_date(page_text, target_date, meal_type)
                else:
                    menu = extract_meal_from_koreacharts(page_text, target_date, meal_type)

                if menu:
                    st.caption(f"급식 정보 출처: {source['name']}")
                    return menu

            except Exception:
                continue

        st.error(
            f"공개 급식 페이지에서 {target_date.strftime('%Y-%m-%d')} {meal_type} 정보를 찾지 못했습니다. "
            "주말, 방학, 급식 없는 날이거나 페이지 구조가 바뀌었을 수 있습니다."
        )
        return None

    except Exception as e:
        st.error(f"급식 정보 조회 중 오류: {e}")
        return None
        
# 요일별 샘플 메뉴
def get_sample_menu():
    """
    요일별 샘플 급식 메뉴를 반환합니다.
    """
    today = datetime.now()
    weekday = today.weekday()  # 0=월, 1=화, 2=수, 3=목, 4=금
    
    sample_menus = {
        0: "밥, 미역국, 소시지계란말이, 브로콜리나물, 깍두기, 요구르트",
        1: "흰쌀밥, 된장찌개, 돈까스, 양배추샐러드, 김, 수박",
        2: "잡곡밥, 고등어구이, 감자국, 시금치나물, 오이무침, 딸기요거트",
        3: "밥, 계란국, 치킨너겟, 옥수수수염차, 당근글라제, 포도",
        4: "밥, 소고기미역국, 생선까스, 브로콜리, 깍두기, 우유",
    }
    
    return sample_menus.get(weekday, sample_menus[0])

# 사이드바 - 임신 정보 입력
st.sidebar.title("📅 임신 정보")

# 마지막 생리 시작일 입력
last_period_date = st.sidebar.date_input(
    "마지막 생리 시작일",
    value=datetime(2026, 4, 12),
    max_value=datetime.now()
)

# 현재 날짜
today = datetime.now()

# 임신 주수 계산 (의료 기준: LMP 기준)
days_since_lmp = (today - datetime.combine(last_period_date, datetime.min.time())).days
weeks = days_since_lmp // 7
days = days_since_lmp % 7

# 임신 시기 판정
if weeks < 13:
    trimester = "1분기 (초기 임신)"
    trimester_num = 1
elif weeks < 27:
    trimester = "2분기 (중기 임신)"
    trimester_num = 2
else:
    trimester = "3분기 (후기 임신)"
    trimester_num = 3

# 예정일 계산 (LMP + 280일)
due_date = datetime.combine(last_period_date, datetime.min.time()) + timedelta(days=280)

# 사이드바에 임신 정보 표시
st.sidebar.success(f"""
### 현재 상태
- **임신 주수:** {weeks}주 {days}일
- **임신 시기:** {trimester}
- **예정일:** {due_date.strftime('%Y-%m-%d')}
""")

# 메인 페이지
st.title("👶 임산부 급식 가이드")
st.write("학교 급식표를 보고 임신 시기별 섭취 조언을 제공하는 사이트입니다.")

# 임신 시기별 영양소 권장량
nutrition_recommendations = {
    1: {
        "칼로리": 2000,
        "단백질": 70,
        "철분": 27,
        "칼슘": 1000,
        "dha": 200
    },
    2: {
        "칼로리": 2340,
        "단백질": 85,
        "철분": 27,
        "칼슘": 1000,
        "dha": 250
    },
    3: {
        "칼로리": 2450,
        "단백질": 100,
        "철분": 27,
        "칼슘": 1000,
        "dha": 300
    }
}

# 임신 시기별 주의사항
cautions = {
    1: "초기 임신으로 유산 위험이 높은 시기입니다. 충분한 휴식과 엽산 섭취가 중요합니다.",
    2: "빠른 성장 시기입니다. 단백질과 칼슘 섭취에 주의하세요.",
    3: "분만 준비 시기입니다. 철분과 단백질을 충분히 섭취하세요."
}

# 탭 생성
tab1, tab2, tab3, tab4 = st.tabs(["🍽️ 급식 분석", "📚 영양소 가이드", "💡 임신 시기별 조언", "ℹ️ 정보"])

# ===== TAB 1: 급식 분석 =====
with tab1:
    st.header("🍽️ 급식 분석")

    # 한국 시간 기준 오늘 날짜
    today_kst = datetime.utcnow() + timedelta(hours=9)

    col_date, col_meal = st.columns([1, 1])

    with col_date:
        selected_date = st.date_input(
            "조회할 날짜",
            value=today_kst.date()
        )

    with col_meal:
        selected_meal_type = st.radio(
            "식사 선택",
            ["점심", "저녁"],
            horizontal=True
        )

    # 화면 표시용 / 크롤링용 식사명 변환
    meal_type_map = {
        "점심": "중식",
        "저녁": "석식"
    }

    meal_type_for_search = meal_type_map[selected_meal_type]

    selected_date_label = selected_date.strftime("%Y년 %m월 %d일")

    st.info(f"📅 선택한 날짜: **{selected_date_label}** · 🍽️ 선택한 식사: **{selected_meal_type}**")

    # 세션 상태 초기화
    if "meal_data" not in st.session_state:
        st.session_state.meal_data = None

    if "meal_loaded_key" not in st.session_state:
        st.session_state.meal_loaded_key = None

    # 날짜와 식사 종류가 바뀌면 자동으로 다시 불러오기
    current_key = f"{selected_date.strftime('%Y%m%d')}_{meal_type_for_search}"

    if st.session_state.meal_loaded_key != current_key:
        with st.spinner(f"{selected_date_label} {selected_meal_type} 급식 정보를 불러오는 중입니다..."):
            st.session_state.meal_data = get_school_meal(
                target_date=selected_date,
                meal_type=meal_type_for_search
            )
            st.session_state.meal_loaded_key = current_key

    # 급식 불러오기 결과 표시
    if st.session_state.meal_data:
        st.success(f"✅ {selected_date_label} {selected_meal_type} 급식 정보를 불러왔습니다.")
    else:
        st.warning(
            f"⚠️ {selected_date_label} {selected_meal_type} 급식 정보를 자동으로 불러오지 못했습니다. "
            "아래 입력창에 직접 입력할 수 있습니다."
        )

    st.divider()

    # 자동으로 불러온 메뉴를 보여주되, 사용자가 수정 가능하게 함
    menu_input = st.text_area(
        f"{selected_date_label} {selected_meal_type} 급식 메뉴",
        value=st.session_state.meal_data or "",
        placeholder="예: 밥, 미역국, 닭고기오븐구이, 시금치나물, 깍두기, 요구르트",
        height=100,
        help="자동으로 불러온 급식 메뉴가 틀리면 직접 수정할 수 있습니다."
    )
    
    if menu_input:
        menus = [menu.strip() for menu in menu_input.split(",")]
        
        st.subheader("📋 메뉴별 맞춤 조언")
        st.divider()
        
        # 영양소 데이터베이스
        nutrition_db = {
            "밥": [195, 4.3, 0.3, 10, 0],
            "흰쌀밥": [195, 4.3, 0.3, 10, 0],
            "잡곡밥": [210, 5.2, 1.2, 35, 0],
            "미역국": [25, 3.0, 5.0, 150, 0],
            "미역": [30, 2.5, 5.0, 120, 0],
            "계란": [155, 13.0, 2.7, 56, 180],
            "계란말이": [190, 14.0, 2.5, 50, 170],
            "소시지계란말이": [210, 15.0, 2.3, 45, 160],
            "소시지": [150, 12.0, 0.5, 20, 0],
            "브로콜리": [34, 2.8, 0.7, 47, 0],
            "브로콜리나물": [45, 3.2, 0.8, 55, 0],
            "깍두기": [30, 1.2, 0.3, 30, 0],
            "김치": [35, 1.5, 0.5, 50, 0],
            "요구르트": [100, 3.5, 0.1, 120, 50],
            "우유": [150, 7.7, 0.1, 276, 100],
            "치즈": [115, 7.0, 0.7, 202, 75],
            "고등어": [200, 20.0, 1.5, 50, 1500],
            "고등어구이": [220, 21.0, 1.6, 55, 1600],
            "연어": [210, 22.0, 0.8, 25, 2000],
            "생선": [180, 20.0, 0.5, 30, 800],
            "생선까스": [280, 22.0, 1.2, 40, 900],
            "소고기": [250, 26.0, 2.6, 25, 0],
            "소고기미역국": [60, 6.0, 2.5, 100, 0],
            "돼지고기": [200, 27.0, 0.6, 15, 0],
            "닭고기": [165, 31.0, 0.3, 20, 100],
            "치킨너겟": [280, 18.0, 0.5, 25, 50],
            "돈까스": [380, 25.0, 1.2, 50, 100],
            "두부": [76, 8.0, 1.5, 150, 0],
            "콩나물": [30, 3.3, 0.8, 30, 0],
            "시금치": [23, 2.9, 2.7, 99, 0],
            "시금치나물": [40, 3.2, 3.0, 110, 0],
            "당근": [41, 0.9, 0.3, 33, 0],
            "당근글라제": [80, 1.2, 0.5, 45, 0],
            "옥수수": [99, 3.3, 0.4, 3, 0],
            "옥수수수염차": [5, 0, 0, 0, 0],
            "감자국": [45, 2.5, 0.2, 30, 0],
            "된장찌개": [80, 6.0, 1.5, 80, 0],
            "고구마": [103, 1.6, 0.5, 30, 0],
            "호박": [25, 1.0, 0.2, 25, 0],
            "버터": [717, 0.9, 0, 24, 250],
            "포도": [67, 0.6, 0.4, 10, 0],
            "딸기": [32, 0.8, 0.3, 16, 0],
            "딸기요거트": [120, 4.0, 0.2, 130, 50],
            "바나나": [89, 1.1, 0.3, 5, 0],
            "사과": [52, 0.3, 0.1, 5, 0],
            "오렌지": [47, 0.9, 0.1, 40, 0],
            "수박": [30, 0.6, 0.2, 8, 0],
            "양배추샐러드": [50, 1.5, 0.3, 35, 0],
            "오이무침": [35, 1.2, 0.2, 25, 0],
            "김": [35, 6.0, 2.0, 50, 100],
        }
        
        # 임신 시기별 영양소 권장량
        nutrition_recommendations = {
            1: {  # 1분기
                "칼로리": 2000,
                "단백질": 70,
                "철분": 27,
                "칼슘": 1000,
                "dha": 200
            },
            2: {  # 2분기
                "칼로리": 2340,
                "단백질": 85,
                "철분": 27,
                "칼슘": 1000,
                "dha": 250
            },
            3: {  # 3분기
                "칼로리": 2450,
                "단백질": 100,
                "철분": 27,
                "칼슘": 1000,
                "dha": 300
            }
        }
        
        # 임신 시기별 주의사항
        cautions = {
            1: "초기 임신으로 유산 위험이 높은 시기입니다. 충분한 휴식과 엽산 섭취가 중요합니다.",
            2: "빠른 성장 시기입니다. 단백질과 칼슘 섭취에 주의하세요.",
            3: "분만 준비 시기입니다. 철분과 단백질을 충분히 섭취하세요."
        }
        
        # 임신 시기별 추천도 기준
        recommendation_scores = {
            1: {
                "높은 권장": ["계란", "우유", "치즈", "생선", "두부", "콩나물", "시금치", "당근", "요구르트"],
                "권장": ["소고기", "돼지고기", "닭고기", "밥", "호박", "브로콜리"],
                "주의": ["카페인", "생소시지", "날계란"],
                "피해야할": ["술", "담배", "과다한 카페인"]
            },
            2: {
                "높은 권장": ["고등어", "연어", "우유", "치즈", "계란", "소고기", "시금치"],
                "권장": ["두부", "콩나물", "당근", "브로콜리", "요구르트"],
                "주의": ["카페인", "과도한 염분"],
                "피해야할": ["술", "담배", "과다한 카페인", "생선회"]
            },
            3: {
                "높은 권장": ["소고기", "계란", "우유", "고등어", "연어", "시금치", "당근"],
                "권장": ["두부", "치즈", "밥", "호박", "브로콜리"],
                "주의": ["카페인", "과도한 염분", "매운음식"],
                "피해야할": ["술", "담배", "생선회", "덜익힌 음식"]
            }
        }
        
        total_nutrition = {
            "칼로리": 0,
            "단백질": 0,
            "철분": 0,
            "칼슘": 0,
            "dha": 0
        }
        
        def normalize_menu_name(menu):
            """메뉴명 정리: 공백, 괄호, 알레르기 번호 제거"""
            menu = str(menu).strip()
            menu = re.sub(r"\([^)]*\)", "", menu)
            menu = re.sub(r"[0-9.]", "", menu)
            menu = menu.replace(" ", "")
            return menu.lower()


        def find_nutrition(menu):
            """
            정확한 메뉴명이 없어도 키워드로 영양소를 추정합니다.
            반환값: 영양정보, 매칭된 기준명
            """
            clean_menu = normalize_menu_name(menu)
            
            # 0. 구체적인 복합 메뉴는 일반 키워드보다 먼저 분류
            specific_nutrition_rules = [
                {
                    "keywords": ["마파두부덮밥", "마파두부", "마파두부밥"],
                    "name": "마파두부덮밥류",
                    "nutrition": [520, 18.0, 2.2, 130, 0],
                },
                {
                    "keywords": ["유린기", "유린기소스"],
                    "name": "유린기류",
                    "nutrition": [360, 24.0, 1.2, 35, 0],
                },
                {
                    "keywords": ["치즈돈까스", "치즈돈가스", "치즈돈까스소스", "치즈돈가스소스"],
                    "name": "치즈돈까스류",
                    "nutrition": [430, 24.0, 1.2, 150, 0],
                },
                {
                    "keywords": ["돈까스", "돈가스", "수제돈까스", "등심돈까스"],
                    "name": "돈까스류",
                    "nutrition": [380, 25.0, 1.2, 50, 0],
                },
                {
                    "keywords": ["김치볶음밥", "김치볶음밥계란", "김치볶음밥볶음"],
                    "name": "김치볶음밥류",
                    "nutrition": [420, 10.0, 1.5, 45, 0],
                },
                {
                    "keywords": ["볶음밥", "새우볶음밥", "야채볶음밥", "햄볶음밥", "계란볶음밥"],
                    "name": "볶음밥류",
                    "nutrition": [400, 10.0, 1.2, 40, 0],
                },
                {
                    "keywords": ["비빔밥", "나물비빔밥", "산채비빔밥"],
                    "name": "비빔밥류",
                    "nutrition": [450, 13.0, 2.0, 80, 0],
                },
                {
                    "keywords": ["오므라이스", "하이라이스", "카레라이스", "짜장밥", "덮밥"],
                    "name": "덮밥/라이스류",
                    "nutrition": [500, 14.0, 1.8, 70, 0],
                },
                {
                    "keywords": ["미니우동", "우동", "유부우동", "어묵우동", "가락국수"],
                    "name": "우동류",
                    "nutrition": [300, 9.0, 1.0, 45, 0],
                },
                {
                    "keywords": ["국수", "잔치국수", "비빔국수", "칼국수", "쌀국수"],
                    "name": "면류",
                    "nutrition": [350, 10.0, 1.2, 50, 0],
                },
                {
                    "keywords": ["시금치올리브샐러드", "올리브샐러드", "시금치샐러드"],
                    "name": "시금치올리브샐러드류",
                    "nutrition": [120, 3.0, 1.5, 70, 0],
                },
                {
                    "keywords": ["버터갈릭난", "갈릭난", "버터난", "난"],
                    "name": "난/빵류",
                    "nutrition": [260, 7.0, 1.2, 45, 0],
                },
                {
                    "keywords": ["망고라씨", "라씨", "망고요거트음료"],
                    "name": "라씨/요거트음료류",
                    "nutrition": [180, 5.0, 0.2, 160, 0],
                },
                {
                    "keywords": ["김자반", "김가루자반", "돌자반", "자반김"],
                    "name": "김자반류",
                    "nutrition": [70, 3.0, 1.0, 40, 100],
                },
                {
                    "keywords": ["떡갈비구이", "떡갈비", "수제떡갈비", "떡갈비조림"],
                    "name": "떡갈비구이류",
                    "nutrition": [320, 18.0, 1.8, 35, 0],
                },
            ]

            for item in specific_nutrition_rules:
                if any(keyword in clean_menu for keyword in item["keywords"]):
                    return item["nutrition"], item["name"]
            def is_soup_or_stew(clean_menu):
                """국/찌개/탕류 판정: 단어 끝이 국, 찌개, 탕인 경우만"""
    
                # 예외: 탕이 들어가지만 국물 음식이 아닌 메뉴
                soup_exceptions = ["탕수육", "찹쌀탕수육", "탕후루"]

                if any(exception in clean_menu for exception in soup_exceptions):
                    return False

                return (
                    clean_menu.endswith("국")
                    or clean_menu.endswith("찌개")
                    or clean_menu.endswith("탕")
                )
            # 1. 정확히 일치하는 경우
            if clean_menu in nutrition_db:
                return nutrition_db[clean_menu], clean_menu

            # 2. 기존 nutrition_db 안에서 부분 일치 찾기
            for key, value in nutrition_db.items():
                clean_key = normalize_menu_name(key)

                # 너무 넓은 키워드는 부분 일치에서 제외
                # 예: 김치볶음밥이 '밥'으로, 치즈돈까스가 '치즈'로 잡히는 문제 방지
                too_generic_keys = ["밥", "국", "탕", "면", "치즈", "김치", "우유", "두부"]

                if clean_key in too_generic_keys:
                    continue

                if len(clean_key) >= 3 and (clean_key in clean_menu or clean_menu in clean_key):
                    return value, key
            # 전복영양갈비탕은 일반 국/찌개류보다 먼저 따로 분류
            if "전복영양갈비탕" in clean_menu or ("전복" in clean_menu and "갈비탕" in clean_menu):
                return [520, 28.0, 3.0, 90, 200], "전복영양갈비탕류"   
                
            # 마라탕은 일반 국/찌개류보다 먼저 따로 분류
            if "마라탕" in clean_menu:
                return [450, 18.0, 2.0, 120, 0], "마라탕류"
                
             # 3. 국/찌개/탕류는 '포함'이 아니라 '마지막 글자' 기준으로 분류
            if is_soup_or_stew(clean_menu):
                return [80, 5.0, 1.0, 60, 0], "국/찌개류"

            # 4. 급식 메뉴에 자주 나오는 일반 키워드로 추정
            keyword_nutrition = [
                {
                    "keywords": ["쭈꾸미삼겹살", "주꾸미삼겹살", "쭈삼", "주삼"],
                    "name": "쭈꾸미삼겹살볶음류",
                    "nutrition": [360, 28.0, 2.5, 45, 300],
                },           
                {
                    "keywords": ["사천식해물잡채", "사천해물잡채", "해물잡채", "해물볶음잡채"],
                    "name": "해물잡채류",
                    "nutrition": [280, 12.0, 1.8, 45, 250],
                },
                                {
                    "keywords": ["골뱅이야채무침", "골뱅이무침", "골뱅이", "해물야채무침", "해물채소무침"],
                    "name": "해산물무침류",
                    "nutrition": [150, 15.0, 1.5, 45, 150],
                },
                {
                    "keywords": ["언양식불고기", "언양불고기", "바싹불고기"],
                    "name": "언양식불고기류",
                    "nutrition": [280, 22.0, 2.2, 30, 0],
                },
                {
                    "keywords": ["새송이버섯볶음", "새송이볶음", "새송이버섯", "버섯볶음", "버섯"],
                    "name": "버섯볶음류",
                    "nutrition": [80, 3.0, 0.8, 20, 0],
                },
                {
                    "keywords": ["아삭이고추무침", "고추무침", "오이고추무침", "아삭이고추", "오이고추"],
                    "name": "고추무침류",
                    "nutrition": [45, 1.2, 0.5, 25, 0],
                },
                {
                    "keywords": ["애호박부추전", "호박부추전", "애호박전", "부추전", "야채전", "채소전"],
                    "name": "채소전류",
                    "nutrition": [180, 5.0, 1.0, 45, 0],
                },
                {
                    "keywords": ["단무지", "짜사이무침", "짜사이", "자차이", "절임무", "무절임"],
                    "name": "절임류",
                    "nutrition": [25, 0.5, 0.2, 15, 0],
                },
                {
                    "keywords": ["꽈리고추멸치볶음", "꽈리고추멸치", "멸치볶음", "꽈리고추", "잔멸치볶음"],
                    "name": "멸치볶음류",
                    "nutrition": [130, 9.0, 1.2, 180, 150],
                },
                {
                    "keywords": ["동태전", "동태부침", "생선전", "명태전"],
                    "name": "생선전류",
                    "nutrition": [180, 16.0, 1.0, 40, 300],
                },
                {
                    "keywords": ["두바이쫀득쿠키", "쫀득쿠키", "두바이쿠키", "쿠키"],
                    "name": "쿠키/디저트류",
                    "nutrition": [220, 3.0, 0.6, 40, 0],
                },
                {
                    "keywords": ["아이스홍시", "홍시", "감", "아이스감"],
                    "name": "과일/디저트류",
                    "nutrition": [90, 0.5, 0.2, 10, 0],
                },
                {
                    "keywords": ["씨없는포도", "포도", "청포도", "적포도", "샤인머스캣", "거봉"],
                    "name": "포도류",
                    "nutrition": [67, 0.6, 0.4, 10, 0],
                },
                {
                    "keywords": ["청포묵김가루무침", "청포묵무침", "청포묵", "묵무침", "김가루무침"],
                    "name": "묵무침류",
                    "nutrition": [90, 2.0, 0.6, 25, 0],
                },
                {
                    "keywords": ["마늘종명엽채볶음", "마늘쫑명엽채볶음", "명엽채볶음", "명엽채", "마늘종", "마늘쫑"],
                    "name": "명엽채볶음류",
                    "nutrition": [160, 9.0, 1.0, 40, 100],
                },
                {
                    "keywords": ["해물", "새우", "오징어", "낙지", "쭈꾸미", "주꾸미", "문어", "조개", "홍합"],
                    "name": "해산물류",
                    "nutrition": [140, 18.0, 1.8, 40, 300],
                },
                {
                    "keywords": ["삼겹살", "돼지고기볶음", "제육볶음", "돼지불고기"],
                    "name": "돼지고기볶음류",
                    "nutrition": [320, 22.0, 1.2, 25, 0],
                },
                {
                    "keywords": ["잡채", "버섯잡채", "야채잡채"],
                    "name": "잡채류",
                    "nutrition": [230, 6.0, 1.2, 35, 0],
                },
                {
                    "keywords": ["피자", "고르곤졸라피자", "고르곤졸라"],
                    "name": "피자류",
                    "nutrition": [330, 14.0, 1.0, 180, 0],
                },
                {
                    "keywords": ["야채쌈", "채소쌈", "상추쌈", "쌈채소", "상추", "깻잎"],
                    "name": "쌈채소류",
                    "nutrition": [25, 1.5, 0.8, 45, 0],
                },
                {
                    "keywords": ["쌈장", "된장양념"],
                    "name": "쌈장류",
                    "nutrition": [45, 2.0, 0.8, 25, 0],
                },
                {
                    "keywords": ["스파게티", "파스타", "로제스파게티", "크림파스타", "토마토파스타"],
                    "name": "파스타류",
                    "nutrition": [420, 14.0, 1.8, 90, 0],
                },
                {
                    "keywords": ["샐러드", "시트러스샐러드", "양상추", "채소샐러드"],
                    "name": "샐러드류",
                    "nutrition": [60, 1.5, 0.5, 35, 0],
                },
                {
                    "keywords": ["닭다리", "닭고기", "치킨", "오븐구이", "닭"],
                    "name": "닭고기류",
                    "nutrition": [220, 27.0, 1.0, 25, 100],
                },
                {
                    "keywords": ["감자", "회오리감자", "감자튀김", "웨지감자"],
                    "name": "감자류",
                    "nutrition": [180, 3.0, 0.8, 20, 0],
                },
                {
                    "keywords": ["오이", "피클", "오이피클", "오이무침"],
                    "name": "오이/피클류",
                    "nutrition": [25, 0.8, 0.2, 20, 0],
                },
                {
                    "keywords": ["코코리치", "음료", "주스", "푸딩", "젤리", "디저트"],
                    "name": "음료/디저트류",
                    "nutrition": [100, 0.5, 0.1, 20, 0],
                },
                {
                    "keywords": ["밥", "쌀밥", "백미", "현미", "잡곡"],
                    "name": "밥류",
                    "nutrition": [200, 4.5, 0.5, 15, 0],
                },
                {
                    "keywords": ["미역국", "된장국", "계란국", "감자국", "콩나물국", "어묵국", "김치찌개", "된장찌개", "순두부찌개", "부대찌개", "갈비탕", "설렁탕", "곰탕", "삼계탕", "육개장"],
                    "name": "국/찌개류",
                    "nutrition": [80, 5.0, 1.0, 60, 0],
                },
                {
                    "keywords": ["생선", "고등어", "삼치", "연어", "생선까스"],
                    "name": "생선류",
                    "nutrition": [220, 22.0, 1.2, 50, 1000],
                },
                {
                    "keywords": ["오리불고기", "오리고기", "훈제오리", "오리", "크러쉬알리오오리불고기"],
                    "name": "오리불고기류",
                    "nutrition": [320, 24.0, 2.2, 25, 0],
                },
                {
                    "keywords": ["돼지갈비엿장조림", "돼지갈비조림", "돼지갈비", "돈갈비", "돼지장조림"],
                    "name": "돼지갈비조림류",
                    "nutrition": [330, 24.0, 1.4, 35, 0],
                },
                {
                    "keywords": ["소고기", "쇠고기", "소불고기", "쇠불고기", "한우", "소고기장조림", "쇠고기장조림"],
                    "name": "소고기류",
                    "nutrition": [250, 26.0, 2.6, 25, 0],
                },
                {
                    "keywords": ["돼지고기", "제육", "돈까스", "탕수육"],
                    "name": "돼지고기류",
                    "nutrition": [280, 24.0, 1.0, 30, 0],
                },
                {
                    "keywords": ["계란", "달걀", "계란찜", "달걀말이", "오믈렛"],
                    "name": "계란류",
                    "nutrition": [160, 13.0, 2.5, 55, 150],
                },
                {
                    "keywords": ["우유", "요구르트", "요거트", "치즈"],
                    "name": "유제품류",
                    "nutrition": [120, 5.0, 0.2, 180, 50],
                },
                {
                    "keywords": ["김치", "깍두기", "배추김치"],
                    "name": "김치류",
                    "nutrition": [30, 1.2, 0.4, 35, 0],
                },
            ]

            for item in keyword_nutrition:
                if any(keyword in clean_menu for keyword in item["keywords"]):
                    return item["nutrition"], item["name"]

            return None, None


        def get_menu_advice(menu):
            """임신 시기별 메뉴 조언 생성"""
            clean_menu = normalize_menu_name(menu)

            # 피해야 할 메뉴
            avoid_keywords = ["생선회", "광어회", "연어회", "참치회", "육회", "날계란", "반숙", "생굴", "술", "알코올"]
            if any(keyword in clean_menu for keyword in avoid_keywords):
                return "⭐ (피하기)", "임신 중에는 식중독 위험을 줄이기 위해 날것이나 덜 익힌 음식은 피하는 것이 안전합니다."

            if "마라탕" in clean_menu:
                return "⭐⭐⭐ (적당히)", "마라탕은 고기, 두부, 채소가 들어가면 단백질과 식이섬유 섭취에 도움이 될 수 있지만, 국물의 나트륨과 매운 양념이 많을 수 있습니다. 임신 중 속쓰림이나 부종이 걱정된다면 건더기 위주로 먹고 국물은 적게 드세요."

            if "마파두부덮밥" in clean_menu or "마파두부" in clean_menu:
                return "⭐⭐⭐ (적당히)", "마파두부덮밥은 두부로 단백질을 섭취할 수 있지만, 매운 양념과 나트륨이 많을 수 있습니다. 속쓰림이 있거나 자극적인 음식이 부담되면 양을 조절하고 물을 충분히 드세요."

            if "유린기" in clean_menu:
                return "⭐⭐⭐ (적당히)", "유린기는 닭고기 단백질을 섭취할 수 있지만, 튀기거나 기름에 조리한 닭고기에 새콤달콤한 소스가 더해져 당과 나트륨이 많을 수 있습니다. 채소 반찬과 함께 적당량 드세요."

            if "김자반" in clean_menu or "김가루자반" in clean_menu or "돌자반" in clean_menu or "자반김" in clean_menu:
                return "⭐⭐⭐ (적당히)", "김자반은 김의 무기질 섭취에 도움이 될 수 있지만, 조미된 반찬이라 나트륨이 많을 수 있습니다. 밥에 곁들이는 정도로 조금만 드세요."

            if "떡갈비구이" in clean_menu or "떡갈비" in clean_menu:
                return "⭐⭐⭐ (적당히)", "떡갈비구이는 단백질 섭취에 도움이 될 수 있지만, 양념육이라 당과 나트륨이 많을 수 있습니다. 채소 반찬과 함께 적당량 드세요."

            if "시금치올리브샐러드" in clean_menu or "올리브샐러드" in clean_menu or "시금치샐러드" in clean_menu:
                return "⭐⭐⭐⭐ (권장)", "시금치와 샐러드 채소는 엽산, 비타민, 식이섬유 섭취에 도움이 됩니다. 다만 드레싱이나 올리브오일이 많으면 열량이 올라갈 수 있으니 적당히 드세요."

            if "버터갈릭난" in clean_menu or "갈릭난" in clean_menu or "버터난" in clean_menu:
                return "⭐⭐⭐ (적당히)", "난은 에너지 공급에 도움이 되는 빵류입니다. 다만 버터와 갈릭소스가 들어가면 지방과 나트륨이 많을 수 있으니 카레나 단백질 반찬과 함께 적당량 드세요."

            if "망고라씨" in clean_menu or "라씨" in clean_menu:
                return "⭐⭐⭐ (적당히)", "라씨는 요거트 기반 음료라 칼슘 섭취에 도움이 될 수 있지만, 망고라씨는 당이 많은 편일 수 있습니다. 후식이나 음료로 소량 드세요."
            
            if "애호박부추전" in clean_menu or "호박부추전" in clean_menu or "애호박전" in clean_menu or "부추전" in clean_menu:
                return "⭐⭐⭐ (적당히)", "애호박과 부추가 들어가 비타민과 식이섬유 섭취에 도움이 될 수 있습니다. 다만 전류는 기름에 부친 음식이라 많이 먹기보다 적당량 드세요."
                
            if "전복영양갈비탕" in clean_menu or ("전복" in clean_menu and "갈비탕" in clean_menu):
                return "⭐⭐⭐⭐ (권장)", "전복과 갈비가 들어간 국물 메뉴로 단백질과 철분 섭취에 도움이 될 수 있습니다. 다만 갈비탕 국물은 나트륨과 지방이 많을 수 있으니 건더기 위주로 먹고 국물은 적게 드세요."

            if "꽈리고추멸치볶음" in clean_menu or "멸치볶음" in clean_menu:
                return "⭐⭐⭐ (적당히)", "멸치는 칼슘 섭취에 도움이 될 수 있지만, 볶음 양념은 짜거나 달 수 있습니다. 꽈리고추가 매울 수 있으니 속쓰림이 있으면 양을 조절하세요."

            if "동태전" in clean_menu or "생선전" in clean_menu or "명태전" in clean_menu:
                return "⭐⭐⭐⭐ (권장)", "동태전은 익힌 생선과 달걀옷으로 단백질 섭취에 도움이 될 수 있습니다. 다만 기름에 부친 음식이므로 많이 먹기보다 적당량 드세요."

            if "두바이쫀득쿠키" in clean_menu or "쫀득쿠키" in clean_menu or "두바이쿠키" in clean_menu or "쿠키" in clean_menu:
                return "⭐⭐⭐ (적당히)", "쿠키류는 당과 지방이 많은 디저트일 수 있습니다. 식사 대용보다는 후식으로 소량만 드세요."
                
            if "치즈돈까스" in clean_menu or "치즈돈가스" in clean_menu:
                return "⭐⭐⭐ (적당히)", "치즈돈까스는 단백질과 칼슘 섭취에 도움이 될 수 있지만 튀김류라 지방과 나트륨이 많을 수 있습니다. 소스는 적당히 먹고 채소 반찬과 함께 드세요."

            if "돈까스" in clean_menu or "돈가스" in clean_menu:
                return "⭐⭐⭐ (적당히)", "돈까스는 단백질을 섭취할 수 있지만 튀김류라 기름진 편입니다. 속쓰림이 있으면 양을 조절하세요."

            if "김치볶음밥" in clean_menu:
                return "⭐⭐⭐ (적당히)", "김치볶음밥은 에너지 공급에는 좋지만 김치와 양념 때문에 나트륨이 많을 수 있습니다. 단백질 반찬이나 채소와 함께 먹으면 더 균형 잡힌 식사가 됩니다."

            if "볶음밥" in clean_menu:
                return "⭐⭐⭐ (적당히)", "볶음밥은 에너지 공급에는 좋지만 기름과 나트륨이 많을 수 있습니다. 채소나 단백질 반찬과 함께 드세요."

            if "미니우동" in clean_menu or "우동" in clean_menu:
                return "⭐⭐⭐ (적당히)", "우동은 먹을 수 있지만 면과 국물 위주의 메뉴라 나트륨이 많을 수 있습니다. 국물은 적게 먹고, 단백질 반찬이나 채소를 함께 챙기면 좋습니다."

            if "청포묵김가루무침" in clean_menu or "청포묵" in clean_menu or "묵무침" in clean_menu:
                return "⭐⭐⭐⭐ (권장)", "청포묵은 비교적 부담이 적은 반찬이고 김가루와 함께 먹으면 무기질 섭취에 도움이 될 수 있습니다. 다만 양념이 짜면 양을 조절하세요."

            if "마늘종명엽채볶음" in clean_menu or "마늘쫑명엽채볶음" in clean_menu or "명엽채" in clean_menu:
                return "⭐⭐⭐ (적당히)", "명엽채볶음은 단백질 섭취에 도움이 될 수 있지만, 볶음 양념에 당과 나트륨이 많을 수 있습니다. 조금씩 곁들여 드세요."

            if "돼지갈비엿장조림" in clean_menu or "돼지갈비조림" in clean_menu or "돼지갈비" in clean_menu:
                return "⭐⭐⭐ (적당히)", "돼지갈비는 단백질 섭취에 도움이 되지만 엿장 양념은 당과 나트륨이 많을 수 있습니다. 채소 반찬과 함께 먹고 양념은 적당히 드세요."
            
            # 주의 메뉴
            caution_keywords = ["커피", "카페인", "콜라", "홍차", "녹차"]
            salty_keywords = ["피클", "장아찌", "젓갈", "김치", "깍두기", "단무지", "짜사이", "자차이", "쌈장", "된장", "고추장"]
            fried_keywords = ["튀김", "감자튀김", "회오리감자", "돈까스", "치킨너겟", "전", "부침"]
            spicy_keywords = ["쭈꾸미", "주꾸미", "낙지볶음", "제육볶음", "쭈꾸미삼겹살", "주꾸미삼겹살", "사천식", "사천", "해물잡채", "사천식해물잡채", "골뱅이무침", "골뱅이야채무침", "아삭이고추무침", "고추무침", "마라", "마라탕", "한국식마라탕", "볶음"]
            fatty_keywords = ["삼겹살", "피자", "고르곤졸라", "치즈피자"]

            if "사천식해물잡채" in clean_menu or "해물잡채" in clean_menu:
                return "⭐⭐⭐ (적당히)", "해물과 채소가 들어가 단백질과 무기질 섭취에 도움이 될 수 있습니다. 다만 사천식 양념은 맵고 나트륨이 많을 수 있으니 속쓰림이 있으면 양을 조절하세요."
            
            if any(keyword in clean_menu for keyword in spicy_keywords):
                return "⭐⭐⭐ (적당히)", "단백질과 철분 섭취에는 도움이 될 수 있지만, 매운 양념이나 나트륨이 많을 수 있어 속쓰림이 있으면 양을 조절하세요."

            if any(keyword in clean_menu for keyword in fatty_keywords):
                return "⭐⭐⭐ (적당히)", "먹을 수 있지만 지방과 나트륨이 많은 편일 수 있습니다. 채소와 함께 먹고 양을 조절하세요."

            if any(keyword in clean_menu for keyword in caution_keywords):
                return "⭐⭐ (주의)", "카페인 섭취량을 확인하세요. 임신 중에는 카페인을 과하게 섭취하지 않는 것이 좋습니다."

            if any(keyword in clean_menu for keyword in salty_keywords):
                return "⭐⭐⭐ (적당히)", "먹을 수 있지만 짠 음식일 수 있으므로 양을 조절하세요. 국물이나 절임류는 조금만 드시는 것이 좋습니다."

            if any(keyword in clean_menu for keyword in fried_keywords):
                return "⭐⭐⭐ (적당히)", "먹을 수 있지만 기름지거나 나트륨이 많을 수 있어 양을 조절하세요."

            if "오리불고기" in clean_menu or "크러쉬알리오오리불고기" in clean_menu:
                return "⭐⭐⭐ (적당히)", "오리고기는 단백질과 철분 섭취에 도움이 될 수 있지만, 불고기 양념은 나트륨과 당이 많을 수 있어 양을 조절하세요. 충분히 익힌 상태라면 섭취 가능합니다."

            if "골뱅이야채무침" in clean_menu or "골뱅이무침" in clean_menu or "골뱅이" in clean_menu:
                return "⭐⭐⭐ (적당히)", "골뱅이는 단백질 섭취에 도움이 될 수 있지만, 무침 양념은 맵고 짤 수 있습니다. 속쓰림이 있거나 입덧이 심하면 양을 조절하세요."

            if "언양식불고기" in clean_menu or "언양불고기" in clean_menu or "바싹불고기" in clean_menu:
                return "⭐⭐⭐⭐ (권장)", "단백질과 철분 섭취에 도움이 될 수 있습니다. 다만 양념 불고기는 나트륨과 당이 많을 수 있으니 채소와 함께 적당히 드세요."

            if "새송이버섯볶음" in clean_menu or "새송이" in clean_menu or "버섯볶음" in clean_menu:
                return "⭐⭐⭐⭐ (권장)", "버섯은 식이섬유와 무기질 섭취에 도움이 됩니다. 기름이 많은 볶음이라면 양을 적당히 조절하세요."

            if "아삭이고추무침" in clean_menu or "고추무침" in clean_menu or "아삭이고추" in clean_menu:
                return "⭐⭐⭐ (적당히)", "채소 반찬으로 먹을 수 있지만, 고추와 양념이 속쓰림을 유발할 수 있습니다. 매운 음식이 부담되면 조금만 드세요."

            if "단무지" in clean_menu or "짜사이" in clean_menu or "자차이" in clean_menu:
                return "⭐⭐⭐ (적당히)", "절임류는 나트륨이 많을 수 있습니다. 입맛을 돋우는 정도로 조금만 드세요."

            if "아이스홍시" in clean_menu or "홍시" in clean_menu:
                return "⭐⭐⭐⭐ (권장)", "과일 디저트로 비타민과 식이섬유 섭취에 도움이 될 수 있습니다. 다만 당이 많을 수 있으니 양을 적당히 조절하세요."

            # 적극 권장 메뉴
            high_keywords = ["닭", "소고기", "쇠고기", "돼지고기", "삼겹살", "오리", "오리불고기", "훈제오리", "생선", "쭈꾸미", "주꾸미", "오징어", "낙지", "계란", "두부", "콩", "우유", "요구르트", "요거트", "치즈", "시금치", "브로콜리"]
            if any(keyword in clean_menu for keyword in high_keywords):
                if trimester_num == 1:
                    return "⭐⭐⭐⭐⭐ (적극 권장)", "현재 임신 초기에는 단백질, 엽산, 철분을 챙기는 것이 좋습니다. 충분히 익힌 상태라면 좋은 선택입니다."
                elif trimester_num == 2:
                    return "⭐⭐⭐⭐⭐ (적극 권장)", "임신 중기에는 태아 성장에 필요한 단백질, 칼슘, 철분 섭취가 중요합니다."
                else:
                    return "⭐⭐⭐⭐⭐ (적극 권장)", "임신 후기에는 단백질과 철분을 꾸준히 챙기면 좋습니다."

            # 채소/과일
            vegetable_keywords = ["샐러드", "오이", "당근", "양배추", "상추", "깻잎", "야채쌈", "채소쌈", "쌈채소", "나물", "버섯", "새송이", "고추", "아삭이고추", "과일", "사과", "오렌지", "딸기", "귤", "감", "홍시", "포도", "청포도", "적포도", "샤인머스캣", "거봉", "시트러스"]
            if any(keyword in clean_menu for keyword in vegetable_keywords):
                return "⭐⭐⭐⭐ (권장)", "비타민과 식이섬유 섭취에 도움이 됩니다. 다만 드레싱이나 절임류는 양을 조절하세요."

            # 탄수화물 위주 메뉴
            carb_keywords = ["스파게티", "파스타", "면", "빵", "감자", "우동", "국수"]
            plain_rice_names = ["밥", "쌀밥", "흰쌀밥", "백미밥", "잡곡밥", "현미밥", "보리밥"]

            if clean_menu in plain_rice_names or any(keyword in clean_menu for keyword in carb_keywords):
                return "⭐⭐⭐⭐ (권장)", "에너지 공급에 도움이 됩니다. 단백질 반찬이나 채소와 함께 먹으면 더 균형 잡힌 식사가 됩니다."

            return "⭐⭐⭐ (보통)", "특별한 위험 식품은 아니지만, 전체 식단의 균형을 보며 적당히 드세요."


        # 메뉴별 분석 결과를 먼저 모아두기
        menu_results = []

        for menu in menus:
            if not menu.strip():
                continue

            nutrition, matched_name = find_nutrition(menu)
            recommendation_level, advice = get_menu_advice(menu)

            if nutrition:
                cal, protein, iron, calcium, dha = nutrition

                total_nutrition["칼로리"] += cal
                total_nutrition["단백질"] += protein
                total_nutrition["철분"] += iron
                total_nutrition["칼슘"] += calcium
                total_nutrition["dha"] += dha
            else:
                cal, protein, iron, calcium, dha = 0, 0, 0, 0, 0
                matched_name = "분류 없음"

            menu_results.append({
                "menu": menu,
                "matched_name": matched_name,
                "recommendation_level": recommendation_level,
                "advice": advice,
                "cal": cal,
                "protein": protein,
                "iron": iron,
                "calcium": calcium,
                "dha": dha,
            })
        # ===== 표로 한 번 더 요약 =====
        st.subheader("📊 메뉴별 요약표")

        summary_rows = []

        for item in menu_results:
            summary_rows.append({
                "메뉴": item["menu"],
                "판정": item["recommendation_level"],
                "분류": item["matched_name"],
                "칼로리": item["cal"],
                "단백질(g)": item["protein"],
                "철분(mg)": item["iron"],
                "칼슘(mg)": item["calcium"],
            })

        st.dataframe(summary_rows, use_container_width=True, hide_index=True)
        
        # ===== 한눈에 보는 요약 =====
        st.subheader("🔎 한눈에 보는 오늘 급식")

        high_count = sum("적극 권장" in item["recommendation_level"] for item in menu_results)
        good_count = sum("권장" in item["recommendation_level"] and "적극" not in item["recommendation_level"] for item in menu_results)
        caution_count = sum("주의" in item["recommendation_level"] or "적당히" in item["recommendation_level"] for item in menu_results)
        avoid_count = sum("피하기" in item["recommendation_level"] for item in menu_results)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("적극 권장", f"{high_count}개")
        with col2:
            st.metric("권장", f"{good_count}개")
        with col3:
            st.metric("적당히/주의", f"{caution_count}개")
        with col4:
            st.metric("피하기", f"{avoid_count}개")

        # 오늘의 한 줄 코멘트
        if avoid_count > 0:
            st.error("오늘 급식에는 피하는 것이 좋은 메뉴가 있습니다. 해당 메뉴는 대체하거나 섭취를 피하세요.")
        elif caution_count > 0:
            st.warning("오늘 급식은 대체로 괜찮지만, 일부 메뉴는 양을 조절해서 드세요.")
        else:
            st.success("오늘 급식은 임신 시기 기준으로 비교적 무난한 편입니다.")

        st.divider()

        # ===== 카드형 메뉴 표시 =====
        st.subheader("📋 메뉴별 맞춤 조언")

        cards_per_row = 3

        for i in range(0, len(menu_results), cards_per_row):
            cols = st.columns(cards_per_row)

            for col, item in zip(cols, menu_results[i:i + cards_per_row]):
                with col:
                    # 추천도에 따른 배경색
                    if "피하기" in item["recommendation_level"]:
                        bg_color = "#ffe5e5"
                        border_color = "#ff8a8a"
                    elif "주의" in item["recommendation_level"] or "적당히" in item["recommendation_level"]:
                        bg_color = "#fff7d6"
                        border_color = "#ffd666"
                    elif "적극 권장" in item["recommendation_level"]:
                        bg_color = "#e6f7ec"
                        border_color = "#74d99f"
                    else:
                        bg_color = "#eaf3ff"
                        border_color = "#91caff"

                    short_advice = item["advice"]
                    if len(short_advice) > 55:
                        short_advice = short_advice[:55] + "..."

                    st.markdown(
                        f"""
                        <div style="
                            background-color: {bg_color};
                            border: 1px solid {border_color};
                            border-radius: 16px;
                            padding: 16px;
                            min-height: 230px;
                            margin-bottom: 14px;
                        ">
                            <h3 style="margin: 0 0 8px 0; font-size: 20px;">
                                {item["menu"]}
                            </h3>
                            <div style="
                                font-weight: 700;
                                margin-bottom: 10px;
                                color: #222;
                            ">
                                {item["recommendation_level"]}
                            </div>
                            <div style="font-size: 14px; line-height: 1.6;">
                                <b>분류</b>: {item["matched_name"]}<br>
                                <b>열량</b>: {item["cal"]} kcal<br>
                                <b>단백질</b>: {item["protein"]}g<br>
                                <b>철분</b>: {item["iron"]}mg<br>
                                <b>칼슘</b>: {item["calcium"]}mg
                            </div>
                            <p style="
                                margin-top: 12px;
                                font-size: 14px;
                                line-height: 1.5;
                            ">
                                💬 {short_advice}
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )



        # ===== 자세한 조언은 접어두기 =====
        with st.expander("🔍 메뉴별 자세한 조언 보기"):
            for item in menu_results:
                st.markdown(f"### {item['menu']}")
                st.markdown(f"**판정:** {item['recommendation_level']}")
                st.markdown(f"**분류:** {item['matched_name']}")
                st.markdown(f"""
- 칼로리: {item['cal']} kcal
- 단백질: {item['protein']}g
- 철분: {item['iron']}mg
- 칼슘: {item['calcium']}mg
- DHA: {item['dha']}mg
                """)
                st.markdown(f"**💬 조언:** {item['advice']}")
                st.divider()
        
        # 총 영양소 요약
        st.subheader("📊 오늘의 총 영양소 섭취량")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        rec = nutrition_recommendations[trimester_num]
        
        with col1:
            st.metric(
                "칼로리",
                f"{total_nutrition['칼로리']:.0f}",
                f"{total_nutrition['칼로리'] - rec['칼로리']:.0f}",
                delta_color="normal"
            )
        
        with col2:
            st.metric(
                "단백질 (g)",
                f"{total_nutrition['단백질']:.1f}",
                f"{total_nutrition['단백질'] - rec['단백질']:.1f}",
                delta_color="normal"
            )
        
        with col3:
            st.metric(
                "철분 (mg)",
                f"{total_nutrition['철분']:.1f}",
                f"{total_nutrition['철분'] - rec['철분']:.1f}",
                delta_color="normal"
            )
        
        with col4:
            st.metric(
                "칼슘 (mg)",
                f"{total_nutrition['칼슘']:.0f}",
                f"{total_nutrition['칼슘'] - rec['칼슘']:.0f}",
                delta_color="normal"
            )
        
        with col5:
            st.metric(
                "DHA (mg)",
                f"{total_nutrition['dha']:.0f}",
                f"{total_nutrition['dha'] - rec['dha']:.0f}",
                delta_color="normal"
            )
        
        st.info(f"⚠️ {cautions[trimester_num]}")
    else:
        st.info("🔄 위의 버튼 중 하나를 클릭하여 급식 정보를 불러오거나 메뉴를 입력해주세요.")

# ===== TAB 2: 영양소 가이드 =====
with tab2:
    st.header("📚 임신 중 영양소 가이드")
    
    rec = nutrition_recommendations[trimester_num]
    
    st.subheader(f"현재 임신 시기({trimester})의 일일 영양소 권장량")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("칼로리", f"{rec['칼로리']} kcal")
    with col2:
        st.metric("단백질", f"{rec['단백질']}g")
    with col3:
        st.metric("철분", f"{rec['철분']}mg")
    with col4:
        st.metric("칼슘", f"{rec['칼슘']}mg")
    with col5:
        st.metric("DHA", f"{rec['dha']}mg")
    
    st.divider()
    
    st.subheader("🥗 주요 영양소별 좋은 음식")
    
    nutrients_info = {
        "단백질 (70-100g)": {
            "설명": "태아의 성장과 모체의 건강 유지에 필수적입니다.",
            "음식": ["계란", "소고기", "돼지고기", "닭고기", "생선", "우유", "치즈", "두부", "콩"],
            "이점": "근육 발달, 호르몬 생성, 면역력 강화"
        },
        "철분 (27mg)": {
            "설명": "혈액량 증가와 태아의 혈액 형성에 필수적입니다.",
            "음식": ["소고기", "돼지고기", "닭고기", "시금치", "미역", "굴"],
            "이점": "빈혈 예방, 산소 운반"
        },
        "칼슘 (1,000mg)": {
            "설명": "태아의 뼈와 치아 형성에 중요합니다.",
            "음식": ["우유", "치즈", "요구르트", "멸치", "미역", "브로콜리"],
            "이점": "뼈 건강, 신경 전달"
        },
        "엽산 (600mcg)": {
            "설명": "태아의 신경계 발달과 척추 발달에 필수적입니다.",
            "음식": ["시금치", "브로콜리", "아스파라거스", "콩", "계란"],
            "이점": "선천성 결손증 예방, DNA 합성"
        },
        "DHA (200-300mg)": {
            "설명": "태아의 뇌 발달과 시력 발달에 중요합니다.",
            "음식": ["고등어", "연어", "멸치", "계란", "우유"],
            "이점": "뇌 발달, 시력 향상"
        }
    }
    
    for nutrient, info in nutrients_info.items():
        with st.expander(f"📌 {nutrient}"):
            st.write(f"**설명:** {info['설명']}")
            st.write(f"**좋은 음식:** {', '.join(info['음식'])}")
            st.write(f"**이점:** {info['이점']}")
    
    st.divider()
    
    st.subheader("⚠️ 피해야 할 음식")
    
    avoid_foods = {
        "생선회, 생굴": "리스테리아 세균 감염 위험",
        "덜 익힌 고기": "톡소플라즈마 감염 위험",
        "과다한 카페인": "유산 위험 증가",
        "알코올": "태아 알코올 증후군 위험",
        "과다한 염분": "임신중독증 위험",
        "고수은 생선": "신경계 발달 저해",
        "미처리 우유 제품": "세균 감염 위험"
    }
    
    for food, reason in avoid_foods.items():
        st.warning(f"❌ **{food}**: {reason}")

# ===== TAB 3: 임신 시기별 조언 =====
with tab3:
    st.header("💡 임신 시기별 건강 가이드")
    
    st.subheader(f"현재: {trimester} ({weeks}주 {days}일)")
    st.divider()
    
    trimester_info = {
        1: {
            "title": "1분기 (1-13주)",
            "description": "초기 임신 단계로 태아의 기본 기관이 형성되는 시기입니다.",
            "symptoms": [
                "오심, 구토",
                "피로감",
                "유방 확대 및 압통",
                "빈뇨",
                "기분 변화"
            ],
            "diet": [
                "엽산 충분한 섭취 (시금치, 브로콜리)",
                "소량 자주 먹기",
                "비타민 B6 풍부한 음식 (생선, 닭고기)",
                "충분한 수분 섭취",
                "소화가 잘 되는 음식 선택"
            ],
            "caution": [
                "충분한 휴식 취하기",
                "스트레스 최소화",
                "격렬한 운동 피하기",
                "음주, 흡연 절대 금지",
                "생고기, 알코올, 고수은 생선 피하기"
            ],
            "activity": [
                "가벼운 산책",
                "요가 (안전한 동작만)",
                "수영 (의사 상담 후)",
                "명상"
            ]
        },
        2: {
            "title": "2분기 (14-27주)",
            "description": "태아가 빠르게 성장하는 시기로, 산모도 눈에 띄는 변화가 생깁니다.",
            "symptoms": [
                "배가 나옴",
                "태동 느낌",
                "피로감 감소",
                "피부 변화",
                "허리 통증"
            ],
            "diet": [
                "단백질 충분한 섭취 (고기, 생선, 계란)",
                "칼슘 충분한 섭취 (우유, 치즈, 브로콜리)",
                "철분 섭취 (소고기, 시금치)",
                "DHA 섭취 (연어, 고등어)",
                "규칙적인 식사"
            ],
            "caution": [
                "임신중독증 증상 주의",
                "과도한 체중 증가 피하기",
                "배 부위에 무리 주지 않기",
                "너무 자극적인 음식 피하기",
                "충분한 수면"
            ],
            "activity": [
                "안전한 산책",
                "임산부 요가",
                "임산부 수영",
                "가벼운 스트레칭",
                "케겔 운동"
            ]
        },
        3: {
            "title": "3분기 (28-40주)",
            "description": "분만 준비 단계로 태아가 자궁 내에서 위치를 잡는 시기입니다.",
            "symptoms": [
                "호흡 곤란",
                "소화 불편",
                "빈뇨 심화",
                "수면 어려움",
                "허리 통증 심화"
            ],
            "diet": [
                "철분 충분한 섭취",
                "단백질 충분한 섭취",
                "칼슘 충분한 섭취",
                "가벼운 끼니 자주 먹기",
                "과도한 염분 제한"
            ],
            "caution": [
                "경미한 수축 증상 주의",
                "갑작스런 복통 주의",
                "출혈 주의",
                "과로 피하기",
                "장시간 서있기 피하기"
            ],
            "activity": [
                "천천한 산책",
                "가벼운 스트레칭",
                "케겔 운동 강화",
                "분만 호흡법 연습",
                "이완 운동"
            ]
        }
    }
    
    info = trimester_info[trimester_num]
    
    st.markdown(f"### {info['title']}")
    st.write(info['description'])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🤰 일반적 증상")
        for symptom in info['symptoms']:
            st.write(f"• {symptom}")
        
        st.markdown("#### 🏃 권장 활동")
        for activity in info['activity']:
            st.write(f"• {activity}")
    
    with col2:
        st.markdown("#### 🥘 식단 권장사항")
        for diet in info['diet']:
            st.write(f"• {diet}")
        
        st.markdown("#### ⚠️ 건강 주의사항")
        for caution in info['caution']:
            st.write(f"• {caution}")

# ===== TAB 4: 정보 =====
with tab4:
    st.header("ℹ️ 앱 정보")
    
    st.markdown("""
    ### 👶 임산부 급식 가이드
    
    이 앱은 임산부가 학교 급식 메뉴를 기반으로 임신 시기별 맞춤형 영양 조언을 받을 수 있도록 설계되었습니다.
    
    #### 주요 기능
    - **🍽️ 급식 분석**: 오늘의 급식 메뉴를 입력하면 메뉴별 영양소 정보와 임신 시기별 조언을 제공합니다.
    - **📚 영양소 가이드**: 임신 시기별 필요한 영양소와 좋은 음식, 피해야 할 음식을 안내합니다.
    - **💡 임신 시기별 조언**: 현재 임신 시기의 신체 증상, 식단 권장사항, 주의사항을 제공합니다.
    - **🔄 자동 급식 불러오기**: 서울과학고등학교의 점심 급식 정보를 자동으로 불러옵니다.
    
    #### 사용 방법
    1. 좌측 사이드바에서 마지막 생리 시작일을 입력합니다.
    2. 현재 임신 정보가 자동으로 계산됩니다.
    3. "🍽️ 급식 분석" 탭에서 다음 중 하나를 선택합니다:
       - **🔄 급식 정보 불러오기**: 자동으로 오늘의 급식을 불러옵니다
       - **📋 샘플 메뉴 사용**: 요일별 샘플 메뉴를 사용합니다
       - **✏️ 직접 입력**: 수동으로 메뉴를 입력합니다
    4. 메뉴별 맞춤형 조언과 총 영양소 섭취량을 확인합니다.
    
    #### ⚠️ 중요 공지
    이 앱은 일반적인 정보 제공을 목적으로 하며, 의료 전문가의 조언을 대체할 수 없습니다.
    임신 중 특이 사항이나 건강 문제가 있을 경우 반드시 담당 의사와 상담하세요.
    
    #### 📋 데이터 출처
    - 임신 시기별 영양소 권장량: 대한산부인과학회, 한국영양학회
    - 음식별 영양소 정보: 한국식품영양학회, USDA 데이터베이스
    """)
