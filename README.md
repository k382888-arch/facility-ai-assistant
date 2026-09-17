# 시설관리 AI 업무비서 1차 데모

## 실행 방법
1. Python 3.10 이상 설치
2. 폴더에서 터미널 실행
3. `pip install -r requirements.txt`
4. `streamlit run app.py`
5. 휴대폰에서 사용하려면 Streamlit Community Cloud 등에 배포

## 포함 기능
- 대시보드
- 설비 등록
- 고장 진단
- 전기·수도 검침 계산
- 점검 일정
- 월간 보고서
- 설비/고장 이력 검색

## 주의
- 현재 1차 버전은 로컬 CSV 저장 방식입니다.
- 여러 명이 동시에 쓰거나 외부 고객에게 판매하려면 Supabase/PostgreSQL 등 DB 연결이 필요합니다.
- 실제 AI API 연결은 2차 버전에서 추가하는 것이 좋습니다.
