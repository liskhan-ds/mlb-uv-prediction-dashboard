import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
import os
from datetime import datetime
import test_mlb_single as engine

# -----------------------------------------------------------------------------
# 1. Page Configuration & Setup
# -----------------------------------------------------------------------------
st.set_page_config(page_title="MLB AI Match Predictor", page_icon="⚾", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "mlb_data.db")

def load_data():
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            query = "SELECT * FROM predictions ORDER BY date ASC, rowid ASC"
            df = pd.read_sql(query, conn)
            conn.close()
            if not df.empty:
                return df
        except Exception:
            pass
            
    # Fallback Data (2026-08-26)
    data = [{
        "date": "2026-08-26",
        "home_team": "Atlanta Braves",
        "visit_team": "Los Angeles Dodgers",
        "predicted_winner": "Los Angeles Dodgers",
        "predicted_gap": 0.02,
        "home_uv": 8.88,
        "visit_uv": 8.90,
        "actual_winner": "",
        "is_correct": None
    }]
    return pd.DataFrame(data)

df = load_data()

# -----------------------------------------------------------------------------
# Top Navigation Bar (7 Leagues)
# -----------------------------------------------------------------------------
nav_cols = st.columns(7)
with nav_cols[0]:
    st.link_button("🏀 NBA ↗", "https://nba-uv-prediction.streamlit.app/", use_container_width=True)
with nav_cols[1]:
    st.button("⚾ MLB (Current)", disabled=True, use_container_width=True)
with nav_cols[2]:
    st.link_button("⚽ EPL ↗", "https://epl-uv-prediction.streamlit.app/", use_container_width=True)
with nav_cols[3]:
    st.link_button("⚽ La Liga ↗", "https://llg-uv-prediction.streamlit.app/", use_container_width=True)
with nav_cols[4]:
    st.link_button("🏒 NHL ↗", "https://nhl-uv-prediction.streamlit.app/", use_container_width=True)
with nav_cols[5]:
    st.link_button("🏈 NFL ↗", "https://nfl-uv-prediction.streamlit.app/", use_container_width=True)
with nav_cols[6]:
    st.link_button("⚽ MLS ↗", "https://mls-uv-prediction.streamlit.app/", use_container_width=True)

st.divider()

# Title
st.title("⚾ MLB AI Match Predictor (by WUV predictor)")

# -----------------------------------------------------------------------------
# Logic: Accuracy Calculation & Numbering
# -----------------------------------------------------------------------------
df['total_no'] = None
valid_mask = df['actual_winner'] != 'Postponed'
df.loc[valid_mask, 'total_no'] = range(1, len(df[valid_mask]) + 1)
df['total_no'] = df['total_no'].fillna('Cancelled')

stats_df = df[
    (df['actual_winner'] != 'Postponed') & 
    (df['actual_winner'].notna()) & 
    (df['actual_winner'] != '')
].copy()

# -----------------------------------------------------------------------------
# 1. Cumulative Prediction Scorecard & 100-Game Tracking
# -----------------------------------------------------------------------------
st.header("📊 Cumulative Prediction Scorecard")
total_stats = len(stats_df)
correct_total = stats_df['is_correct'].sum() if total_stats > 0 else 0

col_acc, col_track = st.columns([2, 1])

if total_stats > 0:
    total_acc = (correct_total / total_stats) * 100
    status_suffix = " (⚡ God-tier, Market Distortion)" if total_acc >= 60 else ""
    
    with col_acc:
        st.subheader(f"Overall Accuracy: `{total_acc:.2f}%`{status_suffix}")
        st.markdown(f"**Correct Predictions:** {int(correct_total)} / **Total Games:** {total_stats}")
    
    with col_track:
        remaining = 100 - total_stats
        if remaining > 0:
            st.metric("100-Game System Verification", f"{remaining} games remaining")
        else:
            st.metric("System Verification Status", "Verification Complete (God-tier)")
else:
    with col_acc:
        st.subheader(f"Total Predicted Games: `{len(df)} Games`")
        st.markdown(f"**Completed Predictions:** {len(df)} Games (Live accuracy calculated after game completion)")
    with col_track:
        st.metric("System Status", "Live Prediction in Progress")

st.markdown("---")

# -----------------------------------------------------------------------------
# 2. Daily Accuracy Scorecard (Past 7 Days)
# -----------------------------------------------------------------------------
st.header("📈 Daily Accuracy Scorecard (Past 7 Days)")

if not stats_df.empty:
    daily_stats = stats_df.groupby('date').agg(
        total_games=('home_team', 'count'), 
        correct_games=('is_correct', 'sum') 
    ).reset_index()

    daily_stats['accuracy'] = (daily_stats['correct_games'] / daily_stats['total_games']) * 100
    
    def get_bar_color(acc):
        if acc >= 60: return '#A020F0'
        elif acc >= 55: return '#FF0000'
        elif acc >= 52.4: return '#FFA500'
        elif acc >= 45: return '#1E90FF'
        elif acc >= 35: return '#008000'
        else: return '#808080'

    daily_stats['bar_color'] = daily_stats['accuracy'].apply(get_bar_color)
    daily_stats['label_text'] = daily_stats.apply(
        lambda x: f"{int(x['correct_games'])}/{int(x['total_games'])}", 
        axis=1
    )

    daily_stats_7d = daily_stats.sort_values('date', ascending=True).tail(7)

    base = alt.Chart(daily_stats_7d).encode(x=alt.X('date', title='Date (US Local)'))
    bars = base.mark_bar().encode(
        y=alt.Y('accuracy', title='Accuracy (%)', scale=alt.Scale(domain=[0, 110])),
        color=alt.Color('bar_color', scale=None),
        tooltip=['date', 'accuracy', 'total_games']
    )
    text = base.mark_text(align='center', baseline='bottom', dy=-5, fontSize=14, fontWeight='bold').encode(
        y='accuracy', text='label_text'
    )
    st.altair_chart((bars + text).properties(height=350), width="stretch")
else:
    st.info("💡 Scheduled game predictions complete! (Live accuracy will be aggregated as games complete.)")

st.markdown("""
<div style="text-align: center; padding: 12px; background-color: #f0f2f6; border-radius: 10px; line-height: 1.6;">
    <span style="color: #A020F0;">●</span> <b>God-tier</b> (60%↑) &nbsp;&nbsp;
    <span style="color: #FF0000;">●</span> <b>Master/AI</b> (55%~60%) &nbsp;&nbsp;
    <span style="color: #FFA500;">●</span> <b>Pro/Expert</b> (52.4%~55%) &nbsp;&nbsp;
    <span style="color: #1E90FF;">●</span> <b>Advanced</b> (45%~52.4%) &nbsp;&nbsp;
    <span style="color: #008000;">●</span> <b>Standard</b> (35%~45%) &nbsp;&nbsp;
    <span style="color: #808080;">●</span> <b>No Bet</b> (35%↓)
    <br><small>* 52.4% represents the statistical breakeven threshold.</small>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# -----------------------------------------------------------------------------
# 3. Daily Detailed Prediction Report
# -----------------------------------------------------------------------------
st.header("📋 Daily Detailed Prediction Report")

df['date_dt'] = pd.to_datetime(df['date']).dt.date
unique_dates = sorted(df['date_dt'].unique(), reverse=True)

default_date_target = datetime.strptime("2026-09-02", "%Y-%m-%d").date()
default_val = default_date_target if default_date_target in unique_dates else unique_dates[0]

selected_date = st.date_input("Select Date to Inspect:", value=default_val)
filtered_df = df[df['date_dt'] == selected_date].copy().reset_index(drop=True)

TEAM_ABBR = {
    'Arizona Diamondbacks': 'ARI', 'Atlanta Braves': 'ATL', 'Baltimore Orioles': 'BAL',
    'Boston Red Sox': 'BOS', 'Chicago Cubs': 'CHC', 'Chicago White Sox': 'CWS',
    'Cincinnati Reds': 'CIN', 'Cleveland Guardians': 'CLE', 'Colorado Rockies': 'COL',
    'Detroit Tigers': 'DET', 'Houston Astros': 'HOU', 'Kansas City Royals': 'KC',
    'Los Angeles Angels': 'LAA', 'Los Angeles Dodgers': 'LAD', 'Miami Marlins': 'MIA',
    'Milwaukee Brewers': 'MIL', 'Minnesota Twins': 'MIN', 'New York Mets': 'NYM',
    'New York Yankees': 'NYY', 'Athletics': 'ATH', 'Oakland Athletics': 'ATH',
    'Philadelphia Phillies': 'PHI', 'Pittsburgh Pirates': 'PIT', 'San Diego Padres': 'SD',
    'San Francisco Giants': 'SF', 'Seattle Mariners': 'SEA', 'St. Louis Cardinals': 'STL',
    'Tampa Bay Rays': 'TB', 'Texas Rangers': 'TEX', 'Toronto Blue Jays': 'TOR',
    'Washington Nationals': 'WAS'
}

def to_abbr(name):
    if not name or name in ['Postponed', 'Cancelled', '취소됨', '⏳ Pending', '⏳ 대기 중', '']:
        return name
    return TEAM_ABBR.get(name, name)

if not filtered_df.empty:
    filtered_df['day_no'] = None
    day_valid_mask = filtered_df['actual_winner'] != 'Postponed'
    filtered_df.loc[day_valid_mask, 'day_no'] = range(1, len(filtered_df[day_valid_mask]) + 1)
    filtered_df['day_no'] = filtered_df['day_no'].fillna('Cancelled')

    day_stats_mask = (filtered_df['actual_winner'] != 'Postponed') & (filtered_df['actual_winner'].notna()) & (filtered_df['actual_winner'] != '')
    finished_games = filtered_df[day_stats_mask]
    finished_count = len(finished_games)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Games Today", f"{len(filtered_df)} Games")
    col2.metric("Finished Games", f"{finished_count} Games")
    if finished_count > 0:
        acc = (finished_games['is_correct'].sum() / finished_count) * 100
        col3.metric("Daily Accuracy", f"{acc:.1f}%")
    else:
        col3.metric("Daily Accuracy", "Prediction Complete (Pending)")

    # Doubleheader detection
    match_counts = {}
    for _, row in filtered_df.iterrows():
        key = (row['home_team'], row['visit_team'])
        match_counts[key] = match_counts.get(key, 0) + 1

    match_seen = {}
    rows_formatted = []
    for _, row in filtered_df.iterrows():
        key = (row['home_team'], row['visit_team'])
        match_seen[key] = match_seen.get(key, 0) + 1
        
        suffix = f" (G{match_seen[key]})" if match_counts[key] > 1 else ""
        
        h_uv = row.get('home_uv', 0.0)
        v_uv = row.get('visit_uv', 0.0)
        
        h_abbr = f"{to_abbr(row['home_team'])}{suffix} ({h_uv:.2f})"
        v_abbr = f"{to_abbr(row['visit_team'])}{suffix} ({v_uv:.2f})"
        
        p_name = row['predicted_winner']
        p_abbr = to_abbr(p_name) + (suffix if p_name in key else "")
        
        a_name = row['actual_winner']
        if a_name == 'Postponed':
            a_abbr = "Cancelled"
        elif pd.isna(a_name) or a_name == '':
            a_abbr = "⏳ Pending"
        else:
            a_abbr = to_abbr(a_name) + (suffix if a_name in key else "")
            
        if a_name == 'Postponed':
            ox_mark = "🆖 Cancelled"
        elif pd.isna(row['is_correct']) or a_name == '':
            ox_mark = "⏳ Pending"
        else:
            ox_mark = "✅ Correct" if row['is_correct'] == 1 else "❌ Incorrect"
            
        rows_formatted.append({
            'No.(Day)': row['day_no'],
            'No.(Total)': row['total_no'],
            'Home Team (WUV)': h_abbr,
            'Away Team (WUV)': v_abbr,
            'Predicted Winner': p_abbr,
            'Expected Gap (uv)': f"{row['predicted_gap']:.2f}",
            'Actual Winner': a_abbr,
            'Prediction Status': ox_mark
        })
        
    display_df = pd.DataFrame(rows_formatted)
    table_height = max(400, (len(display_df) + 1) * 37 + 15)
    st.dataframe(display_df, hide_index=True, width="stretch", height=table_height)

# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #888888; padding-top: 20px;">
        <p>ⓒ DROPSHOT (Business Reg No: 578-81-03214)</p>
        <p>Contact us: liskhan@gmail.com</p>
    </div>
    """,
    unsafe_allow_html=True
)
