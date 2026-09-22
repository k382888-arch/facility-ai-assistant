
import os
from datetime import date, timedelta
import pandas as pd
import streamlit as st
from supabase import create_client, Client

st.set_page_config(
    page_title="시설관리 AI",
    page_icon="🏢",
    layout="wide"
)

# -----------------------------
# Supabase 연결
# -----------------------------
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_ANON_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase 연결정보가 없습니다. Streamlit Secrets에 SUPABASE_URL, SUPABASE_ANON_KEY를 등록하세요.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------
# 세션
# -----------------------------
if "user" not in st.session_state:
    st.session_state.user = None
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None

def set_auth_session(access_token, refresh_token):
    supabase.auth.set_session(access_token, refresh_token)

def current_user_id():
    user = st.session_state.user
    return user.id if user else None

def require_login():
    if st.session_state.user is None:
        st.warning("로그인이 필요합니다.")
        st.stop()

# -----------------------------
# 로그인 / 회원가입
# -----------------------------
if st.session_state.user is None:
    st.title("🏢 시설관리 AI")
    st.caption("로그인한 사용자마다 자기 데이터만 저장·조회합니다.")

    tab1, tab2 = st.tabs(["로그인", "회원가입"])

    with tab1:
        email = st.text_input("이메일", key="login_email")
        password = st.text_input("비밀번호", type="password", key="login_pw")
        if st.button("로그인", type="primary"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.session_state.access_token = res.session.access_token
                st.session_state.refresh_token = res.session.refresh_token
                st.rerun()
            except Exception as e:
                st.error("로그인에 실패했습니다. 이메일/비밀번호를 확인하세요.")

    with tab2:
        email2 = st.text_input("이메일", key="signup_email")
        password2 = st.text_input("비밀번호", type="password", key="signup_pw")
        password3 = st.text_input("비밀번호 확인", type="password", key="signup_pw2")
        if st.button("회원가입"):
            if password2 != password3:
                st.error("비밀번호가 일치하지 않습니다.")
            elif len(password2) < 6:
                st.error("비밀번호는 6자 이상으로 입력하세요.")
            else:
                try:
                    supabase.auth.sign_up({"email": email2, "password": password2})
                    st.success("회원가입 요청이 완료되었습니다. 이메일 인증 설정에 따라 인증 메일을 확인한 뒤 로그인하세요.")
                except Exception:
                    st.error("회원가입에 실패했습니다.")

    st.stop()

# 로그인 세션 적용
set_auth_session(st.session_state.access_token, st.session_state.refresh_token)
uid = current_user_id()

# -----------------------------
# 공통 DB 함수
# -----------------------------
def fetch_table(table, order_col=None, desc=True):
    q = supabase.table(table).select("*")
    if order_col:
        q = q.order(order_col, desc=desc)
    res = q.execute()
    return pd.DataFrame(res.data or [])

def insert_row(table, payload):
    payload = dict(payload)
    payload["user_id"] = uid
    return supabase.table(table).insert(payload).execute()

def delete_row(table, row_id):
    return supabase.table(table).delete().eq("id", row_id).execute()

# -----------------------------
# 상단
# -----------------------------
c1, c2 = st.columns([4,1])
with c1:
    st.title("🏢 시설관리 AI")
    st.caption(f"로그인 계정: {st.session_state.user.email}")
with c2:
    if st.button("로그아웃"):
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
        st.session_state.user = None
        st.session_state.access_token = None
        st.session_state.refresh_token = None
        st.rerun()

tabs = st.tabs(["대시보드","설비등록","고장진단","검침","점검일정","보고서","이력검색"])

# -----------------------------
# 대시보드
# -----------------------------
with tabs[0]:
    eq = fetch_table("equipment", "created_at")
    issues = fetch_table("issues", "created_at")
    meters = fetch_table("meters", "meter_date")
    schedules = fetch_table("schedules", "next_date", desc=False)

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("등록 설비", len(eq))
    open_issues = 0
    if not issues.empty and "status" in issues.columns:
        open_issues = (issues["status"] != "완료").sum()
    c2.metric("미처리 고장", int(open_issues))
    c3.metric("검침 기록", len(meters))
    c4.metric("점검 일정", len(schedules))

    st.subheader("최근 고장 이력")
    st.dataframe(issues.head(5), use_container_width=True)

    st.subheader("다가오는 점검")
    st.dataframe(schedules.head(10), use_container_width=True)

# -----------------------------
# 설비등록
# -----------------------------
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
            insert_row("equipment", {
                "category": kind,
                "name": name,
                "model": model,
                "spec": spec,
                "location": loc,
                "note": note
            })
            st.success("설비를 저장했습니다.")
            st.rerun()

    eq = fetch_table("equipment", "created_at")
    if not eq.empty:
        show_cols = [c for c in ["category","name","model","spec","location","note"] if c in eq.columns]
        st.dataframe(eq[show_cols], use_container_width=True)

# -----------------------------
# 고장진단
# -----------------------------
def diagnose(text):
    t = text.lower()
    if any(k in t for k in ["ch03","ch3","03"]):
        return [
            "1순위: 유선리모컨↔실내기 통신 이상 또는 주소/통신선 문제",
            "2순위: 리모컨 전원 및 통신선 단선·접촉불량",
            "3순위: 실내기 PCB 또는 통신부 이상 가능성",
            "현장 확인: 에러코드 기록 → 통신선 외관/단자 확인 → 반복 시 전문업체 호출"
        ]
    if any(k in t for k in ["차단기","vcb","전기","과전류"]):
        return [
            "1순위: 트립 원인 및 보호계전기 표시/이력 확인",
            "2순위: 부하 급증·단락·지락 여부 확인",
            "3순위: 계전기 설정값 및 CT/PT 계통 확인",
            "주의: 고압 수전설비는 비전문가 직접 조작 금지"
        ]
    if any(k in t for k in ["펌프","압력","소화전"]):
        return [
            "1순위: 전원/차단기/운전신호 확인",
            "2순위: 흡입측 밸브·공기 유입·압력스위치 확인",
            "3순위: 모터·임펠러·베어링 이상 확인",
            "주의: 소방펌프 임의 정지·설정값 변경 금지"
        ]
    return [
        "1순위: 전원·운전표시·알람코드 확인",
        "2순위: 최근 점검·수리 이력 확인",
        "3순위: 배선·센서·밸브·압력·온도 등 기본 상태 확인",
        "주의: 고압전기·소방·냉매회로·회전체 분해는 자격자/전문업체 작업"
    ]

with tabs[2]:
    st.subheader("고장 진단")
    eq_name = st.text_input("설비명 또는 위치")
    symptom = st.text_area("고장 증상 / 에러코드")
    if st.button("진단하기", type="primary"):
        if symptom.strip():
            result = diagnose(symptom)
            for line in result:
                st.write("•", line)
            insert_row("issues", {
                "equipment_name": eq_name,
                "symptom": symptom,
                "diagnosis": " | ".join(result),
                "status": "미처리"
            })
            st.success("진단 결과와 이력을 저장했습니다.")
        else:
            st.warning("증상을 입력하세요.")

# -----------------------------
# 검침
# -----------------------------
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
            insert_row("meters", {
                "meter_date": str(d),
                "meter_name": meter,
                "prev_value": prev,
                "curr_value": curr,
                "multiplier": mult,
                "usage": usage
            })
            st.success(f"사용량: {usage:,.3f}")
            st.rerun()

    mdf = fetch_table("meters", "meter_date")
    if not mdf.empty:
        show_cols = [c for c in ["meter_date","meter_name","prev_value","curr_value","multiplier","usage"] if c in mdf.columns]
        st.dataframe(mdf[show_cols], use_container_width=True)

# -----------------------------
# 점검일정
# -----------------------------
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
            insert_row("schedules", {
                "item": item,
                "last_date": str(recent),
                "cycle_days": int(cycle),
                "next_date": str(nxt),
                "owner": owner
            })
            st.success(f"다음 점검일: {nxt}")
            st.rerun()

    sdf = fetch_table("schedules", "next_date", desc=False)
    if not sdf.empty:
        show_cols = [c for c in ["item","last_date","cycle_days","next_date","owner"] if c in sdf.columns]
        st.dataframe(sdf[show_cols], use_container_width=True)

# -----------------------------
# 보고서
# -----------------------------
with tabs[5]:
    st.subheader("월간 시설관리 보고서")
    month = st.text_input("보고월", value=date.today().strftime("%Y-%m"))

    if st.button("보고서 생성"):
        eq = fetch_table("equipment", "created_at")
        issues = fetch_table("issues", "created_at")
        meters = fetch_table("meters", "meter_date")
        schedules = fetch_table("schedules", "next_date", desc=False)

        monthly_m = meters[meters["meter_date"].astype(str).str.startswith(month)] if not meters.empty else meters
        monthly_i = issues[issues["created_at"].astype(str).str.startswith(month)] if (not issues.empty and "created_at" in issues.columns) else issues
        total_usage = monthly_m["usage"].sum() if (not monthly_m.empty and "usage" in monthly_m.columns) else 0

        report = f"""# {month} 시설관리 월간보고서

## 1. 설비 현황
- 등록 설비: {len(eq)}건

## 2. 검침 현황
- 월 검침 기록: {len(monthly_m)}건
- 합계 사용량: {total_usage:,.3f}

## 3. 고장/이슈
- 신규 고장 이력: {len(monthly_i)}건

## 4. 점검 일정
- 등록 점검 일정: {len(schedules)}건

## 5. 특이사항
- 현장 확인 후 추가 기재
"""
        st.text_area("보고서", report, height=350)

# -----------------------------
# 이력검색
# -----------------------------
with tabs[6]:
    st.subheader("이력 검색")
    q = st.text_input("검색어 예: 발전기, CH03, 소화전")
    if q:
        eq = fetch_table("equipment", "created_at")
        issues = fetch_table("issues", "created_at")

        if not eq.empty:
            eqmask = eq.astype(str).apply(lambda col: col.str.contains(q, case=False, na=False)).any(axis=1)
            st.markdown("#### 설비")
            st.dataframe(eq[eqmask], use_container_width=True)

        if not issues.empty:
            imask = issues.astype(str).apply(lambda col: col.str.contains(q, case=False, na=False)).any(axis=1)
            st.markdown("#### 고장이력")
            st.dataframe(issues[imask], use_container_width=True)

st.divider()
st.caption("주의: 본 앱은 시설관리 업무보조용입니다. 고압전기·소방설비·냉매회로 등 법정 자격·전문성이 필요한 작업은 자격자/전문업체 기준을 따르십시오.")
