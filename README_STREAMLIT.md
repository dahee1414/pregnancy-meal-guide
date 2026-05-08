# 🤰 Streamlit 임신 중 영양 가이드

## 📋 개요

이 Streamlit 애플리케이션은 임신 단계별로 필요한 영양 정보와 식이 조언을 제공합니다.

## ✨ 주요 기능

- ✅ **임신 주차 자동 계산** - 마지막 생리일 입력으로 현재 임신 주차 자동 계산
- ✅ **단계별 영양 정보** - 임신 초기, 중기, 후기별 맞춤형 영양 정보
- ✅ **권장 음식 가이드** - 각 단계에서 권장하는 음식 목록
- ✅ **주의 음식 정보** - 피해야 할 음식과 주의 식품 정보
- ✅ **예상 출산일 계산** - 마지막 생리일 기준 예상 출산일 계산
- ✅ **반응형 UI** - 모든 기기에서 최적화된 사용자 인터페이스

## 🚀 설치 및 실행

### 1. 필수 환경
- Python 3.8 이상
- pip (Python 패키지 관리자)

### 2. 라이브러리 설치

```bash
pip install -r requirements.txt
```

### 3. 앱 실행

```bash
streamlit run streamlit_app.py
```

앱이 자동으로 브라우저에서 열립니다: `http://localhost:8501`

## 📁 파일 구조

```
pregnancy-meal-guide/
├── streamlit_app.py          # 메인 Streamlit 애플리케이션
├── requirements.txt           # Python 라이브러리 종속성
├── .streamlit/
│   └── config.toml           # Streamlit 테마 설정
├── script.js                 # 원본 JavaScript 코드 (웹버전용)
├── style.css                 # 원본 CSS 스타일
├── index.html                # 원본 HTML 파일
└── data/
    └── nutrition_guide.json  # 영양 정보 데이터 (선택사항)
```

## 💾 데이터 파일 (선택사항)

기본적으로 앱은 내장된 기본 영양 정보를 사용합니다.

커스텀 데이터를 사용하려면 `data/nutrition_guide.json` 파일을 생성하세요:

```json
{
  "pregnancy_stages": {
    "early": {
      "name": "임신 초기 (1-13주)",
      "description": "임신 초기 설명...",
      "nutrition_requirements": { ... },
      "important_nutrients": [ ... ],
      "food_recommendations": [ ... ],
      "food_cautions": [ ... ]
    },
    "middle": { ... },
    "late": { ... }
  }
}
```

## 🎯 사용 방법

1. **마지막 생리 시작일 입력**
   - 사이드바의 날짜 선택기에서 정확한 날짜를 입력합니다
   - 정확한 정보를 위해 생리 첫날을 선택합니다

2. **정보 확인**
   - 현재 임신 주차, 일 차, 단계가 자동으로 계산됩니다
   - 예상 출산일이 표시됩니다

3. **영양 정보 확인**
   - 현재 단계별 권장 영양량을 확인합니다
   - 각 영양소의 효과와 음식 출처를 확인합니다

4. **음식 가이드 확인**
   - 권장하는 음식 목록을 확인합니다
   - 주의해야 할 음식을 확인합니다

## 🌐 배포 (Streamlit Cloud)

### 1. GitHub에 코드 푸시
```bash
git add .
git commit -m "Update Streamlit app"
git push origin main
```

### 2. Streamlit Cloud 설정
1. https://streamlit.io/cloud 방문
2. GitHub 계정으로 로그인
3. "New app" 클릭
4. Repository: `dahee1414/pregnancy-meal-guide`
5. Branch: `main`
6. Main file path: `streamlit_app.py`
7. "Deploy" 클릭

완료! 공개 URL로 누구나 접근 가능합니다.

## ⚙️ 커스터마이징

### 테마 변경
`.streamlit/config.toml` 파일을 수정하여 색상을 변경할 수 있습니다:

```toml
[theme]
primaryColor = "#ff69b4"        # 주요 색상
backgroundColor = "#ffffff"     # 배경색
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"
```

### 영양 정보 수정
`DEFAULT_NUTRITION_DATA` 딕셔너리 또는 `data/nutrition_guide.json` 파일을 수정합니다.

## ⚠️ 중요 안내

- 이 앱의 정보는 참고용입니다
- 개인의 건강 상태에 따라 영양 필요량이 다를 수 있습니다
- **반드시 담당 의사나 영양사와 상담하세요**
- 특별한 임신 상태(당뇨병, 고혈압 등)는 의료진 지도를 받으세요

## 🔧 문제 해결

### 문제: "요청에 실패했습니다" 오류
- 터미널에서 앱을 다시 시작합니다
- Streamlit을 최신 버전으로 업그레이드합니다: `pip install --upgrade streamlit`

### 문제: 데이터 파일을 찾을 수 없습니다
- `data/nutrition_guide.json` 파일이 없으면 기본 데이터를 사용합니다
- 커스텀 데이터 파일을 사용하려면 정확한 경로를 확인합니다

### 문제: 포트 8501이 이미 사용 중입니다
```bash
streamlit run streamlit_app.py --logger.level=debug --client.showErrorDetails=true --server.port 8502
```

## 📞 지원

문제가 있으면 GitHub Issues에 보고해주세요.

## 📄 라이선스

MIT License

---

**작성일:** 2026-05-08  
**최종 수정일:** 2026-05-08
