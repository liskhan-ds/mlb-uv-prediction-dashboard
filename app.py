import streamlit as st

# ==============================================================================
# 1. 페이지 기본 설정
# ==============================================================================
st.set_page_config(
    page_title="MLB WUV Game Predictor (9.0 UV 기준)",
    page_icon="⚾",
    layout="wide"
)

# ==============================================================================
# 2. 상단 네비게이션
# ==============================================================================
col_nav1, col_nav2, _ = st.columns([2, 2, 6])
with col_nav1:
    st.link_button(
        "🏀 NBA 대시보드 이동",
        "https://nba-uv-prediction-dashboard-6ahdkhmixcsa3uybaz6ez6.streamlit.app/",
        use_container_width=True
    )
with col_nav2:
    st.button("⚾ MLB 대시보드 (현재)", disabled=True, use_container_width=True)

st.divider()

# 메인 타이틀 및 설명
st.title("⚾ MLB WUV Game Predictor (9.0 UV 기준)")
st.caption("농구 5.0 체계와 동일하게 9.0 UV(수비 4.5 + 공격 4.5) 기준으로 정규화된 MLB 1경기 단일 예측 대시보드")

st.write("")

# ==============================================================================
# 3. 대시보드 본문 (SD vs ATL 검증 데이터 시각화)
# ==============================================================================
st.subheader("🔥 검증 경기 예측 리포트: San Diego Padres (원정) vs Atlanta Braves (홈)")

# 최종 예측 결과 카드
st.markdown("#### 🏆 최종 예측 요약")
col_res1, col_res2, col_res3 = st.columns(3)
with col_res1:
    st.metric(label="예측 승리팀", value="San Diego Padres", delta="승리 예측")
with col_res2:
    st.metric(label="예상 스코어", value="4.2 : 3.5", delta="SD 4.2점 vs ATL 3.5점")
with col_res3:
    st.metric(label="UV 격차 (ΔUV)", value="+0.75 UV", delta="San Diego Padres 우세")

st.markdown("---")

# 팀별 세부 UV 비교
col_away, col_home = st.columns(2)

with col_away:
    st.markdown("### ✈️ 원정팀: San Diego Padres")
    st.info("**최종 팀 UV:** `9.32 / 9.00 UV`")
    
    st.markdown("#### 🛡️ 수비 지분: `4.90 / 4.50 UV`")
    st.write("- **투수 지분:** `2.90 UV` (종합 투수 5.80 UV의 50%)")
    st.write("- **포수 지분:** `0.52 UV` (포수 수비 1.04 UV의 50%)")
    st.write("- **야수 지분:** `1.48 UV` (야수 7인 2.96 UV의 50%)")
    st.caption("⚾ **투수 세부:** Dylan Cease (6.20 UV, 6.0이닝) + 불펜 (5.00 UV, 3.0이닝) -> 투수 5.80 UV")
    
    st.markdown("#### ⚔️ 공격 지분: `4.42 / 4.50 UV`")
    st.write("- **1~9번 타선 지분:** `4.42 UV` (타선 합산 8.83 UV의 50%)")

with col_home:
    st.markdown("### 🏠 홈팀: Atlanta Braves")
    st.success("**최종 팀 UV:** `8.57 / 9.00 UV`")
    
    st.markdown("#### 🛡️ 수비 지분: `4.57 / 4.50 UV`")
    st.write("- **투수 지분:** `2.53 UV` (종합 투수 5.06 UV의 50%)")
    st.write("- **포수 지분:** `0.50 UV` (포수 수비 1.00 UV의 50%)")
    st.write("- **야수 지분:** `1.54 UV` (야수 7인 3.08 UV의 50%)")
    st.caption("⚾ **투수 세부:** Reynaldo López (5.08 UV, 6.5이닝) + 불펜 (5.00 UV, 2.5이닝) -> 투수 5.06 UV")
    
    st.markdown("#### ⚔️ 공격 지분: `4.00 / 4.50 UV`")
    st.write("- **1~9번 타선 지분:** `4.00 UV` (타선 합산 8.01 UV의 50%)")

st.markdown("---")
st.caption("© 2026 MLB WUV Predictor | Built with Streamlit")
