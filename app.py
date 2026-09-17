
import os
from datetime import date, datetime, timedelta
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="시설관리 AI 업무비서", page_icon="🏢", layout="wide")

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

EQUIP_FILE = DATA_DIR / "equipment.csv"
METER_FILE = DATA_DIR / "meters.csv"
ISSUE_FILE = DATA_DIR / "issues.csv"
SCHEDULE_FILE = DATA_DIR / "schedules.csv"

def ensure_csv(path, columns, rows=None):
    if not path.exists():
        pd.DataFrame(rows or [], columns=columns).to_csv(path, index=False, encoding="utf-8-sig")

ensure_csv(
    EQUIP_FILE,
    ["설비구분","설비명","모델","용량/사양","설치위치","비고"],
    [
        ["전기","신관 VCB PANEL","LS GIPAM115 FI","22.9kV / 25.8kV 630A","신관 전기실","OCR/OCGR/OVR/UVR"],
        ["전기","신관 변압기 1","-","500kVA / 22.9kV→380/220V","신관 전기실",""],
        ["전기","신관 변압기 2","-","450kVA / 22.9kV→380/220V","신관 전기실",""],
        ["비상발전기","본관 비상발전기","GNC-750-D","750kW / 938kVA","본관 발전기실","380/220V"],
        ["비상발전기","신관 비상발전기","-","250kW / 313kVA","신관 발전기실",""],
        ["지열","본관 지열 히트펌프","DHGW45N-C4-01","냉방 143.5kW / 난방 181.6kW","본관 기계실","4대"],
        ["지열","신관 지열 시스템","RGUW200C9E","냉방 56kW / 난방 63kW","신관 기계실","LG MULTI V GEO IV"],
        ["축열","신관 축열조","-","236t (유효 172t)","신관 기계실",""],
        ["소방","신관 옥내소화전 주/예비펌프","DMT505SGG-4","0.26㎥/min, 57m, 15kW","신관 펌프실",""],
        ["태양광","신관 인버터","EK36","36kW","신관",""]
    ],
)

ensure_csv(METER_FILE, ["날짜","계량기","전일값","금일값","배율","사용량"], [])
ensure_csv(ISSUE_FILE, ["등록일","설비","증상","진단결과","조치상태"], [])
ensure_csv(SCHEDULE_FILE, ["점검항목","최근점검일","주기일","다음점검일","담당/업체"], [])

def load(path):
    return pd.read_csv(path)

def save(df, path):
    df.to_csv(path, index=False, encoding="utf-8-sig")

def diagnose(text):
    t = text.lower()
    rules = []
    if any(k in t for k in ["ch03","ch3","03"]):
        rules = [
            "1순위: 유선리모컨↔실내기 통신 이상 또는 주소/통신선 문제 확인",
            "2순위: 리모컨 전원 및 통신선 단선·접촉불량 확인",
            "3순위: 실내기 PCB 또는 통신부 이상 가능성",
            "현장 확인: 차단기 리셋 전 에러코드 기록 → 통신선 단자 풀림/손상 확인 → 반복 발생 시 전문업체 호출"
        ]
    elif any(k in t for k in ["펌프","압력","소화전"]):
        rules = [
            "1순위: 전원/차단기/마그네트 및 운전신호 확인",
            "2순위: 흡입측 밸브, 공기 유입, 압력스위치 상태 확인",
            "3순위: 모터·임펠러·베어링 이상 여부 확인",
            "주의: 소방펌프 임의 정지·설정값 변경은 금지하고 전문업체 또는 자격자 확인"
        ]
    elif any(k in t for k in ["차단기","vcb","전기","과전류"]):
        rules = [
            "1순위: 트립 원인 및 보호계전기 표시/이력 확인",
            "2순위: 부하 급증·단락·지락 여부 확인",
            "3순위: 계전기 설정값 및 CT/PT 계통 확인",
            "주의: 고압 수전설비는 비전문가 직접 조작 금지. 전기안전관리자/전문업체 확인"
        ]
    elif any(k in t for k in ["드라이어","에어드라이어","과열","압축기"]):
        rules = [
            "1순위: 전원 입력 및 보호장치 트립 여부 확인",
            "2순위: 콘덴서 오염, 환기불량, 냉매/압축기 과열 확인",
            "3순위: 온도센서 또는 제어회로 이상 확인",
            "현장 확인: 외관·팬·통풍 상태 확인까지. 냉동회로 분해·냉매 작업은 전문업체 호출"
        ]
    else:
        rules = [
            "1순위: 전원·운전표시·알람코드 확인",
            "2순위: 최근 점검·수리 이력과 동일 증상 여부 확인",
            "3순위: 배선·센서·밸브·압력·온도 등 기본 상태 확인",
            "안전: 고압전기·소방설비·냉매회로·회전체 분해는 전문업체 또는 자격자 작업"
        ]
    return "\n".join(rules)

st.title("🏢 시설관리 AI 업무비서")
st.caption("설비관리 · 고장진단 · 검침 · 점검일정 · 보고서 · 이력검색")

tabs = st.tabs(["대시보드","설비등록","고장진단","검침","점검일정","보고서","이력검색"])

with tabs[0]:
    eq = load(EQUIP_FILE)
    issues = load(ISSUE_FILE)
    meters = load(METER_FILE)
    schedules = load(SCHEDULE_FILE)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("등록 설비", len(eq))
    c2.metric("미처리 고장", 0 if issues.empty else (issues["조치상태"]!="완료").sum())
    c3.metric("검침 기록", len(meters))
    c4.metric("점검 일정", len(schedules))
    st.subheader("최근 고장 이력")
    st.dataframe(issues.tail(5), use_container_width=True)
    st.subheader("다가오는 점검")
    if schedules.empty:
        st.info("등록된 점검 일정이 없습니다.")
    else:
        tmp = schedules.copy()
        tmp["다음점검일"] = pd.to_datetime(tmp["다음점검일"], errors="coerce")
        st.dataframe(tmp.sort_values("다음점검일").head(10), use_container_width=True)

with tabs[1]:
    st.subheader("설비 등록")
    with st.form("equipment_form"):
        kind = st.selectbox("설비구분", ["전기","소방","승강기","냉난방","지열","펌프","비상발전기","급수/저수조","자동제어","태양광","기타"])
        name = st.text_input("설비명")
        model = st.text_input("모델명")
        spec = st.text_input("용량/사양")
        loc = st.text_input("설치위치")
        note = st.text_area("비고")
        ok = st.form_submit_button("설비 저장")
        if ok and name:
            df = load(EQUIP_FILE)
            df.loc[len(df)] = [kind,name,model,spec,loc,note]
            save(df,EQUIP_FILE)
            st.success("설비를 저장했습니다.")
    st.dataframe(load(EQUIP_FILE), use_container_width=True)

with tabs[2]:
    st.subheader("고장 진단")
    eq_name = st.text_input("설비명 또는 위치")
    symptom = st.text_area("고장 증상 / 에러코드")
    if st.button("진단하기", type="primary"):
        if symptom.strip():
            result = diagnose(symptom)
            st.markdown("### 진단 결과")
            st.code(result)
            issues = load(ISSUE_FILE)
            issues.loc[len(issues)] = [str(date.today()), eq_name, symptom, result.replace("\n"," | "), "미처리"]
            save(issues, ISSUE_FILE)
        else:
            st.warning("증상을 입력하세요.")

with tabs[3]:
    st.subheader("전기·수도 검침")
    with st.form("meter_form"):
        d = st.date_input("날짜", value=date.today())
        meter = st.text_input("계량기명")
        prev = st.number_input("전일값", value=0.0, format="%.3f")
        curr = st.number_input("금일값", value=0.0, format="%.3f")
        mult = st.number_input("배율", value=1.0, min_value=0.0, format="%.3f")
        submit = st.form_submit_button("계산 및 저장")
        if submit and meter:
            usage = (curr-prev)*mult
            df = load(METER_FILE)
            df.loc[len(df)] = [str(d), meter, prev, curr, mult, usage]
            save(df, METER_FILE)
            st.success(f"사용량: {usage:,.3f}")
    mdf = load(METER_FILE)
    if not mdf.empty:
        st.dataframe(mdf.sort_values("날짜", ascending=False), use_container_width=True)

with tabs[4]:
    st.subheader("점검 일정")
    with st.form("schedule_form"):
        item = st.text_input("점검항목")
        recent = st.date_input("최근 점검일", value=date.today())
        cycle = st.number_input("주기(일)", min_value=1, value=365)
        owner = st.text_input("담당자/업체")
        submit = st.form_submit_button("일정 저장")
        if submit and item:
            nxt = recent + timedelta(days=int(cycle))
            df = load(SCHEDULE_FILE)
            df.loc[len(df)] = [item, str(recent), int(cycle), str(nxt), owner]
            save(df, SCHEDULE_FILE)
            st.success(f"다음 점검일: {nxt}")
    sdf = load(SCHEDULE_FILE)
    if not sdf.empty:
        st.dataframe(sdf.sort_values("다음점검일"), use_container_width=True)

with tabs[5]:
    st.subheader("월간 시설관리 보고서")
    eq = load(EQUIP_FILE)
    issues = load(ISSUE_FILE)
    meters = load(METER_FILE)
    schedules = load(SCHEDULE_FILE)
    month = st.text_input("보고월", value=date.today().strftime("%Y-%m"))
    if st.button("보고서 생성"):
        monthly_m = meters[meters["날짜"].astype(str).str.startswith(month)] if not meters.empty else meters
        monthly_i = issues[issues["등록일"].astype(str).str.startswith(month)] if not issues.empty else issues
        total_usage = monthly_m["사용량"].sum() if not monthly_m.empty else 0
        report = f"""# {month} 시설관리 월간보고서

## 1. 설비 현황
- 등록 설비: {len(eq)}건

## 2. 검침 현황
- 월 검침 기록: {len(monthly_m)}건
- 합계 사용량(등록 계량기 기준): {total_usage:,.3f}

## 3. 고장/이슈
- 신규 고장 이력: {len(monthly_i)}건

## 4. 점검 일정
- 등록 점검 일정: {len(schedules)}건

## 5. 특이사항
- 현장 확인 후 필요 내용을 추가 기재하십시오.
"""
        st.text_area("보고서", report, height=340)

with tabs[6]:
    st.subheader("이력 검색")
    q = st.text_input("검색어 예: CH03, 발전기, 축열조, 소화전")
    if q:
        eq = load(EQUIP_FILE)
        issues = load(ISSUE_FILE)
        mask_eq = eq.astype(str).apply(lambda col: col.str.contains(q, case=False, na=False)).any(axis=1)
        mask_i = issues.astype(str).apply(lambda col: col.str.contains(q, case=False, na=False)).any(axis=1) if not issues.empty else pd.Series(dtype=bool)
        st.markdown("#### 설비")
        st.dataframe(eq[mask_eq], use_container_width=True)
        st.markdown("#### 고장이력")
        if issues.empty:
            st.info("고장이력이 없습니다.")
        else:
            st.dataframe(issues[mask_i], use_container_width=True)

st.divider()
st.caption("주의: 본 앱은 시설관리 업무보조용입니다. 고압전기, 소방설비, 냉매회로 등 법정 자격·전문성이 필요한 작업은 자격자/전문업체 기준을 따르십시오.")
