import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import test_mlb_single as mlb_engine

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
st.caption("실시간 MLB 일정 및 9.0 WUV 정규화 모델(수비 4.5 + 공격 4.5) 기반 승부 예측 대시보드")

st.write("")

# ==============================================================================
# 3. 일정 및 경기 데이터 연동 (Cache 적용)
# ==============================================================================
@st.cache_data(ttl=1800)
def load_schedule(date_str):
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}&hydrate=probablePitcher,lineups,team"
    try:
        res = requests.get(url, timeout=5).json()
        dates = res.get("dates", [])
        if dates and dates[0].get("games"):
            return dates[0]["games"]
    except Exception:
        pass
    return []


# 경기 날짜 선택 (기본값: 내일 날짜)
tomorrow_date = datetime.now() + timedelta(days=1)
selected_date = st.date_input("🗓️ 경기 날짜 선택", value=tomorrow_date)
date_str = selected_date.strftime("%Y-%m-%d")

games = load_schedule(date_str)

if not games:
    st.warning(f"⚠️ 선택하신 날짜({date_str})에는 예정된 MLB 경기가 없거나 조회가 불가능합니다. 검증 데이터(SD vs ATL)로 결과를 표시합니다.")
    game_options = ["SD @ ATL (검증 경기 - 2024-05-20)"]
    selected_game_pk = None
else:
    game_options = []
    game_pk_map = {}
    for idx, g in enumerate(games, 1):
        away_name = g.get("teams", {}).get("away", {}).get("team", {}).get("name", "원정팀")
        home_name = g.get("teams", {}).get("home", {}).get("team", {}).get("name", "홈팀")
        
        away_sp = g.get("teams", {}).get("away", {}).get("probablePitcher", {}).get("fullName", "선발 미정")
        home_sp = g.get("teams", {}).get("home", {}).get("probablePitcher", {}).get("fullName", "선발 미정")

        g_time_raw = g.get("gameDate", "")
        time_label = ""
        if g_time_raw:
            try:
                dt = datetime.strptime(g_time_raw, "%Y-%m-%dT%H:%M:%SZ")
                kst_dt = dt + timedelta(hours=9)
                time_label = kst_dt.strftime("%H:%M KST")
            except Exception:
                time_label = g_time_raw

        label = f"[{idx}] {away_name} ({away_sp}) @ {home_name} ({home_sp}) - {time_label}"
        game_options.append(label)
        game_pk_map[label] = g.get("gamePk")

    selected_label = st.selectbox("⚾ 내일/선택 경기 매치업 선택", game_options)
    selected_game_pk = game_pk_map.get(selected_label)

st.markdown("---")

# ==============================================================================
# 4. 9.0 WUV 예측 엔진 실행 및 결과 시각화
# ==============================================================================
@st.cache_data(ttl=1800)
def get_prediction_result(game_pk, date_str):
    return mlb_engine.predict_single_game(game_pk=game_pk, date_str=date_str)


with st.spinner("9.0 WUV 예측 엔진 계산 중..."):
    res = get_prediction_result(selected_game_pk, date_str)

away_team = res["away_team_name"]
home_team = res["home_team_name"]
away_info = res["away_info"]
home_info = res["home_info"]
away_score = res["away_expected_score"]
home_score = res["home_expected_score"]
gap = res["gap"]
leading_team = res["leading_team"]
winner_team = res["winner_team"]

# 최종 예측 요약 카드
st.subheader(f"🔥 매치업 예측 리포트: {away_team} (원정) vs {home_team} (홈)")

st.markdown("#### 🏆 최종 예측 요약")
col_res1, col_res2, col_res3 = st.columns(3)

with col_res1:
    st.metric(
        label="예측 승리팀",
        value=winner_team,
        delta=f"{winner_team} 승리 예상"
    )
with col_res2:
    st.metric(
        label="예상 스코어",
        value=f"{away_score:.1f} : {home_score:.1f}",
        delta=f"{away_team} {away_score:.1f}점 vs {home_team} {home_score:.1f}점"
    )
with col_res3:
    st.metric(
        label="UV 전력 격차 (ΔUV)",
        value=f"+{gap:.2f} UV",
        delta=f"{leading_team} 우세"
    )

st.markdown("---")

# 양 팀 공/수 세부 지분 비교
st.markdown("#### 📊 양 팀 9.0 WUV 공/수 지분 상세 비교")

col_away, col_home = st.columns(2)

with col_away:
    st.markdown(f"### ✈️ 원정팀: {away_team}")
    st.info(f"**최종 팀 UV:** `{away_info['norm_team_uv']:.2f} / 9.00 UV`")
    
    st.markdown(f"#### 🛡️ 수비 지분: `{away_info['def_share']:.2f} / 4.50 UV`")
    st.write(f"- **투수 지분 (50%):** `{away_info['pitcher_share']:.2f} UV`")
    st.write(f"- **포수 지분 (10%):** `{away_info['c_share']:.2f} UV`")
    st.write(f"- **야수 7인 지분 (40%):** `{away_info['fld_share']:.2f} UV`")
    st.caption(
        f"⚾ **투수 세부:** {away_info['sp_name']} ({away_info['sp_uv']:.2f} UV, {away_info['exp_ip']:.1f}이닝) + "
        f"불펜 ({away_info['bp_uv']:.2f} UV, {away_info['bullpen_ip']:.1f}이닝) -> 종합 투수 {away_info['pitcher_overall_uv']:.2f} UV"
    )
    
    st.markdown(f"#### ⚔️ 공격 지분: `{away_info['off_share']:.2f} / 4.50 UV`")
    st.write(f"- **1~9번 타선 지분:** `{away_info['off_share']:.2f} UV` (wOBA / OPS 기반 4.50 정규화)")

with col_home:
    st.markdown(f"### 🏠 홈팀: {home_team}")
    st.success(f"**최종 팀 UV:** `{home_info['norm_team_uv']:.2f} / 9.00 UV`")
    
    st.markdown(f"#### 🛡️ 수비 지분: `{home_info['def_share']:.2f} / 4.50 UV`")
    st.write(f"- **투수 지분 (50%):** `{home_info['pitcher_share']:.2f} UV`")
    st.write(f"- **포수 지분 (10%):** `{home_info['c_share']:.2f} UV`")
    st.write(f"- **야수 7인 지분 (40%):** `{home_info['fld_share']:.2f} UV`")
    st.caption(
        f"⚾ **투수 세부:** {home_info['sp_name']} ({home_info['sp_uv']:.2f} UV, {home_info['exp_ip']:.1f}이닝) + "
        f"불펜 ({home_info['bp_uv']:.2f} UV, {home_info['bullpen_ip']:.1f}이닝) -> 종합 투수 {home_info['pitcher_overall_uv']:.2f} UV"
    )
    
    st.markdown(f"#### ⚔️ 공격 지분: `{home_info['off_share']:.2f} / 4.50 UV`")
    st.write(f"- **1~9번 타선 지분:** `{home_info['off_share']:.2f} UV` (wOBA / OPS 기반 4.50 정규화)")

st.markdown("---")

# 시각화 비교 데이터프레임 / 차트
st.markdown("#### 📈 공/수 지분 비교 차트")

chart_data = pd.DataFrame({
    "구분": ["수비 지분 (4.5 만점)", "공격 지분 (4.5 만점)", "최종 팀 UV (9.0 만점)"],
    f"{away_team} (원정)": [away_info["def_share"], away_info["off_share"], away_info["norm_team_uv"]],
    f"{home_team} (홈)": [home_info["def_share"], home_info["off_share"], home_info["norm_team_uv"]]
})

st.dataframe(chart_data, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("© 2026 MLB WUV Predictor | Live MLB Stats API Integration | Built with Streamlit")
