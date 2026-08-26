#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MLB 1경기 단일 예측 프로토타입 스크립트 (test_mlb_single.py)
[농구 5.0처럼 야구 9.0 UV 기준 정규화 (수비 4.5 UV + 공격 4.5 UV = 총 9.0 UV)]

1. 수비 지분 (4.50 UV 기준):
   - 투수 지분: 투수 종합 UV(5.0 기준) * 0.5 -> 2.50 UV 기준
   - 포수 지분: 포수 UV(1.0 기준) * 0.5 -> 0.50 UV 기준
   - 야수 지분: 야수 7인 UV(3.0 기준) * 0.5 -> 1.50 UV 기준
   - 수비 지분 총합 = 투수 지분 + 포수 지분 + 야수 지분 (4.50 UV 기준)

2. 공격 지분 (4.50 UV 기준):
   - 1~9번 타자 지분: 기존 타선 공격 UV(9.0 기준) * 0.5 -> 4.50 UV 기준

3. 최종 팀 UV (9.00 UV 기준):
   - 최종 팀 UV = 수비 지분(4.50 기준) + 공격 지분(4.50 기준) (총 9.00 UV 기준)

4. 9이닝 시뮬레이션 및 정규화 리포트 출력
"""

import sys
import requests
from datetime import datetime, timedelta

# ==============================================================================
# 상수 및 기준치 정의 (9.0 UV Normalization Framework)
# ==============================================================================
BASE_URL = "https://statsapi.mlb.com/api/v1"

# Raw baseline values (Original 9.0 Def + 9.0 Off = 18.0)
PITCHER_RAW_BASELINE_UV = 5.00
SP_RAW_BASELINE_UV = 5.00
BULLPEN_RAW_BASELINE_UV = 5.00
CATCHER_RAW_BASELINE_UV = 1.00
FIELDERS_RAW_BASELINE_UV = 3.00
DEFENSE_RAW_BASELINE_UV = 9.00
BATTER_RAW_BASELINE_UV = 1.00
OFFENSE_RAW_BASELINE_UV = 9.00

# Normalized baseline values (4.5 Def + 4.5 Off = 9.0 Total UV)
DEFENSE_NORM_BASELINE_UV = 4.50
OFFENSE_NORM_BASELINE_UV = 4.50
TOTAL_TEAM_NORM_BASELINE_UV = 9.00

# Scale Factor (0.5 to convert 18.0 scale -> 9.0 scale)
SCALE_FACTOR = 0.50

# 리그 평균 지표
MLB_AVG_ERA = 4.10
MLB_AVG_FIP = 4.10
MLB_AVG_OPS = 0.720
MLB_AVG_WOBA = 0.315
MLB_AVG_FLD_PCT = 0.985
MLB_AVG_CS_PCT = 0.240
MLB_AVG_SP_IP = 5.1

# 이닝별 기준 득점
BASE_INNING_RUNS = 0.48


# ==============================================================================
# 1. MLB Stats API 데이터 수집 함수
# ==============================================================================
def parse_ip(ip_str):
    """
    이닝 문자열(예: '144.1' -> 144 + 1/3)을 float 형태로 파싱합니다.
    """
    try:
        ip_s = str(ip_str)
        if "." in ip_s:
            inn, outs = ip_s.split(".")
            return float(inn) + float(outs) / 3.0
        return float(ip_s)
    except (ValueError, TypeError):
        return 0.0


def fetch_game_data(target_date="2024-05-20"):
    """
    특정 날짜의 첫 번째 경기 데이터를 수집합니다.
    """
    session = requests.Session()
    dates_to_try = [target_date]
    
    today = datetime.now()
    for i in range(10):
        dates_to_try.append((today - timedelta(days=i)).strftime("%Y-%m-%d"))

    for date_str in dates_to_try:
        url = f"{BASE_URL}/schedule?sportId=1&date={date_str}"
        try:
            res = session.get(url, timeout=5).json()
            dates = res.get("dates", [])
            if dates and dates[0].get("games"):
                games = dates[0]["games"]
                for game in games:
                    game_pk = game["gamePk"]
                    box_url = f"{BASE_URL}/game/{game_pk}/boxscore"
                    box_res = session.get(box_url, timeout=5).json()
                    if "teams" in box_res:
                        return game, box_res, session
        except Exception:
            continue

    return None, None, session


def fetch_all_player_stats_batch(session, person_ids):
    """
    선수 ID들의 스탯을 일괄 배치 조회합니다.
    """
    if not person_ids:
        return {}
    
    unique_ids = list(set(pid for pid in person_ids if pid))
    pid_str = ",".join(str(p) for p in unique_ids)
    url = f"{BASE_URL}/people?personIds={pid_str}&hydrate=stats(group=[pitching,hitting,fielding],type=[season])"
    
    try:
        res = session.get(url, timeout=5).json()
        stats_db = {}
        for person in res.get("people", []):
            pid = person["id"]
            name = person.get("fullName", f"Player {pid}")
            entry = {"name": name, "pitching": {}, "hitting": {}, "fielding": {}}
            if person.get("stats"):
                for g in person["stats"]:
                    gname = g.get("group", {}).get("displayName")
                    if g.get("splits") and gname in entry:
                        entry[gname] = g["splits"][0].get("stat", {})
            stats_db[pid] = entry
        return stats_db
    except Exception:
        return {}


# ==============================================================================
# 2. 지표 계산 함수 (FIP, wOBA)
# ==============================================================================
def calculate_fip(stat):
    if not stat:
        return MLB_AVG_FIP
    try:
        ip = parse_ip(stat.get("inningsPitched", 0))
        if ip <= 0:
            return MLB_AVG_FIP
        hr = float(stat.get("homeRuns", 0))
        bb = float(stat.get("baseOnBalls", 0))
        hbp = float(stat.get("hitByPitch", 0))
        so = float(stat.get("strikeOuts", 0))
        fip = (13.0 * hr + 3.0 * (bb + hbp) - 2.0 * so) / ip + 3.10
        return max(1.50, min(7.00, fip))
    except (ValueError, TypeError):
        return MLB_AVG_FIP


def calculate_woba(stat):
    if not stat:
        return MLB_AVG_WOBA
    try:
        ab = float(stat.get("atBats", 0))
        bb = float(stat.get("baseOnBalls", 0))
        hbp = float(stat.get("hitByPitch", 0))
        sf = float(stat.get("sacFlies", 0))
        h = float(stat.get("hits", 0))
        d = float(stat.get("doubles", 0))
        t = float(stat.get("triples", 0))
        hr = float(stat.get("homeRuns", 0))
        
        singles = h - d - t - hr
        denom = ab + bb + sf + hbp
        if denom <= 0:
            return MLB_AVG_WOBA
        
        woba = (0.69 * bb + 0.72 * hbp + 0.89 * singles + 1.27 * d + 1.62 * t + 2.10 * hr) / denom
        return max(0.150, min(0.500, woba))
    except (ValueError, TypeError):
        return MLB_AVG_WOBA


# ==============================================================================
# 3. 투수 기대 이닝 및 투수 종합 UV 계산 (5.0 기준)
# ==============================================================================
def calculate_pitcher_overall_uv(pitching_stat):
    if not pitching_stat:
        sp_uv = SP_RAW_BASELINE_UV
        exp_ip = MLB_AVG_SP_IP
    else:
        era = float(pitching_stat.get("era", MLB_AVG_ERA))
        fip = calculate_fip(pitching_stat)
        sp_uv = round(SP_RAW_BASELINE_UV + (MLB_AVG_ERA - era) * 0.35 + (MLB_AVG_FIP - fip) * 0.35, 2)
        sp_uv = max(3.00, min(7.00, sp_uv))

        ip = parse_ip(pitching_stat.get("inningsPitched", 0))
        gs = float(pitching_stat.get("gamesStarted", 0))

        if gs >= 3:
            avg_ip = ip / gs
            exp_ip = round(max(3.5, min(7.0, avg_ip)), 1)
        else:
            exp_ip = MLB_AVG_SP_IP

    bullpen_ip = round(9.0 - exp_ip, 1)
    bp_uv = BULLPEN_RAW_BASELINE_UV

    # 투수 종합 UV (5.00 기준)
    pitcher_overall_uv = round((sp_uv * (exp_ip / 9.0)) + (bp_uv * (bullpen_ip / 9.0)), 2)

    return {
        "sp_uv": sp_uv,
        "exp_ip": exp_ip,
        "bp_uv": bp_uv,
        "bullpen_ip": bullpen_ip,
        "pitcher_overall_uv": pitcher_overall_uv
    }


# ==============================================================================
# 4. 수비 / 공격 RAW & NORMALIZED UV 산출
# ==============================================================================
def calculate_catcher_uv(fielding_stat):
    if not fielding_stat:
        return CATCHER_RAW_BASELINE_UV
    try:
        cs_pct = float(fielding_stat.get("caughtStealingPercentage", MLB_AVG_CS_PCT))
        if cs_pct < 0 or cs_pct > 1:
            cs_pct = MLB_AVG_CS_PCT
        fld_pct = float(fielding_stat.get("fielding", MLB_AVG_FLD_PCT))
        if fld_pct <= 0:
            fld_pct = MLB_AVG_FLD_PCT
    except (ValueError, TypeError):
        return CATCHER_RAW_BASELINE_UV

    cs_adj = (cs_pct - MLB_AVG_CS_PCT) * 0.80
    fld_adj = (fld_pct - MLB_AVG_FLD_PCT) * 3.00
    
    uv = CATCHER_RAW_BASELINE_UV + cs_adj + fld_adj
    return round(max(0.70, min(1.30, uv)), 2)


def calculate_fielders_uv(fielding_stats_list):
    if not fielding_stats_list:
        return FIELDERS_RAW_BASELINE_UV

    valid_fld_pcts = []
    for stat in fielding_stats_list:
        if stat:
            try:
                fld = float(stat.get("fielding", MLB_AVG_FLD_PCT))
                if fld > 0:
                    valid_fld_pcts.append(fld)
            except (ValueError, TypeError):
                continue
    
    avg_fld = (sum(valid_fld_pcts) / len(valid_fld_pcts)) if valid_fld_pcts else MLB_AVG_FLD_PCT
    fld_adj = (avg_fld - MLB_AVG_FLD_PCT) * 8.00
    
    uv = FIELDERS_RAW_BASELINE_UV + fld_adj
    return round(max(2.40, min(3.60, uv)), 2)


def calculate_batter_uv(hitting_stat):
    if not hitting_stat:
        return BATTER_RAW_BASELINE_UV
    try:
        ops = float(hitting_stat.get("ops", MLB_AVG_OPS))
        woba = calculate_woba(hitting_stat)
    except (ValueError, TypeError):
        return BATTER_RAW_BASELINE_UV

    woba_adj = (woba - MLB_AVG_WOBA) * 3.00
    ops_adj = (ops - MLB_AVG_OPS) * 1.50
    
    uv = BATTER_RAW_BASELINE_UV + woba_adj + ops_adj
    return round(max(0.50, min(1.80, uv)), 2)


def extract_team_uv_components(team_box, stats_db):
    """
    팀 박스스코어로부터 원본 UV 및 9.0 스케일 정규화(Normalized) 지분을 산출합니다.
    """
    players = team_box.get("players", {})
    
    pitchers = team_box.get("pitchers", [])
    sp_id = pitchers[0] if pitchers else None
    sp_name = "선발 미정"
    p_stat = {}

    if sp_id and sp_id in stats_db:
        sp_name = stats_db[sp_id]["name"]
        p_stat = stats_db[sp_id]["pitching"]

    p_info = calculate_pitcher_overall_uv(p_stat)

    starters = []
    for pid, pdata in players.items():
        bo = pdata.get("battingOrder")
        if bo and int(bo) % 100 == 0:
            order_num = int(bo) // 100
            pos = pdata.get("position", {}).get("abbreviation", "")
            starters.append((order_num, pdata["person"]["id"], pos))
    
    starters.sort(key=lambda x: x[0])
    if len(starters) < 9:
        batter_ids = team_box.get("batters", [])[:9]
        starters = [(i + 1, bid, "") for i, bid in enumerate(batter_ids)]

    lineup_uvs = []
    catcher_stat = {}
    fielders_stats = []

    for order, bid, pos in starters[:9]:
        if bid and bid in stats_db:
            p_entry = stats_db[bid]
            b_uv = calculate_batter_uv(p_entry["hitting"])
            fld_stat = p_entry["fielding"]
            
            if pos == "C" and not catcher_stat:
                catcher_stat = fld_stat
            elif pos in ["1B", "2B", "3B", "SS", "LF", "CF", "RF"]:
                fielders_stats.append(fld_stat)
        else:
            b_uv = BATTER_RAW_BASELINE_UV
        lineup_uvs.append(b_uv)

    # 1. Raw UV (9.0 Def + 9.0 Off = 18.0)
    c_uv = calculate_catcher_uv(catcher_stat)
    fld_uv = calculate_fielders_uv(fielders_stats)
    raw_def_uv = round(p_info["pitcher_overall_uv"] + c_uv + fld_uv, 2)
    raw_off_uv = round(sum(lineup_uvs), 2)

    # 2. Normalized UV (4.5 Def + 4.5 Off = 9.0)
    pitcher_share = round(p_info["pitcher_overall_uv"] * SCALE_FACTOR, 2)
    c_share = round(c_uv * SCALE_FACTOR, 2)
    fld_share = round(fld_uv * SCALE_FACTOR, 2)
    
    def_share = round(pitcher_share + c_share + fld_share, 2)
    off_share = round(raw_off_uv * SCALE_FACTOR, 2)
    
    # 최종 팀 UV (9.0 기준)
    norm_team_uv = round(def_share + off_share, 2)

    return {
        "sp_name": sp_name,
        "sp_uv": p_info["sp_uv"],
        "exp_ip": p_info["exp_ip"],
        "bp_uv": p_info["bp_uv"],
        "bullpen_ip": p_info["bullpen_ip"],
        "pitcher_overall_uv": p_info["pitcher_overall_uv"],
        "pitcher_share": pitcher_share,
        "c_share": c_share,
        "fld_share": fld_share,
        "def_share": def_share,
        "off_share": off_share,
        "norm_team_uv": norm_team_uv,
        "raw_def_uv": raw_def_uv,
        "raw_off_uv": raw_off_uv,
        "lineup_uvs": lineup_uvs
    }


# ==============================================================================
# 5. 9이닝 공수 교대 시뮬레이션
# ==============================================================================
def simulate_9_innings(offense_lineup_uvs, opponent_info):
    """
    9이닝 득점 시뮬레이션 (상대 팀 수비력 반영)
    """
    cumulative_runs = 0.0
    batter_idx = 0
    
    sp_ip_limit = int(round(opponent_info["exp_ip"]))
    sp_uv = opponent_info["sp_uv"]
    bp_uv = opponent_info["bp_uv"]
    
    # Raw c_uv and fld_uv
    c_uv = opponent_info["c_share"] / SCALE_FACTOR
    fld_uv = opponent_info["fld_share"] / SCALE_FACTOR

    for inning in range(1, 10):
        inning_batters = [
            offense_lineup_uvs[(batter_idx + i) % 9] for i in range(3)
        ]
        batter_idx = (batter_idx + 3) % 9
        avg_batter_uv = sum(inning_batters) / 3.0

        p_uv = sp_uv if inning <= sp_ip_limit else bp_uv
        inning_def_strength = p_uv + c_uv + fld_uv
        def_factor = DEFENSE_RAW_BASELINE_UV / max(inning_def_strength, 0.1)

        inning_expected_runs = BASE_INNING_RUNS * avg_batter_uv * def_factor
        cumulative_runs += inning_expected_runs

    return round(cumulative_runs, 1)


# ==============================================================================
# 6. 메인 실행 및 결과 출력
# ==============================================================================
def run_mlb_single_predictor():
    game, box, session = fetch_game_data("2024-05-20")
    
    if not game or not box:
        away_team_name = "San Diego Padres"
        home_team_name = "Atlanta Braves"
        away_info = {
            "sp_name": "Dylan Cease", "sp_uv": 6.20, "exp_ip": 6.0, "bp_uv": 5.00, "bullpen_ip": 3.0,
            "pitcher_overall_uv": 5.80, "pitcher_share": 2.90, "c_share": 0.52, "fld_share": 1.48,
            "def_share": 4.90, "off_share": 4.41, "norm_team_uv": 9.31,
            "lineup_uvs": [1.19, 1.25, 1.05, 0.85, 0.95, 0.90, 1.05, 0.70, 0.81]
        }
        home_info = {
            "sp_name": "Reynaldo López", "sp_uv": 5.04, "exp_ip": 5.2, "bp_uv": 4.20, "bullpen_ip": 3.1,
            "pitcher_overall_uv": 4.70, "pitcher_share": 2.35, "c_share": 0.50, "fld_share": 1.50,
            "def_share": 4.35, "off_share": 3.97, "norm_team_uv": 8.32,
            "lineup_uvs": [1.10, 1.15, 0.95, 0.85, 0.90, 0.85, 0.80, 0.70, 0.64]
        }
    else:
        away_team_name = game["teams"]["away"]["team"]["name"]
        home_team_name = game["teams"]["home"]["team"]["name"]

        away_box = box["teams"]["away"]
        home_box = box["teams"]["home"]

        away_pids = away_box.get("pitchers", []) + away_box.get("batters", [])
        home_pids = home_box.get("pitchers", []) + home_box.get("batters", [])

        stats_db = fetch_all_player_stats_batch(session, away_pids + home_pids)

        away_info = extract_team_uv_components(away_box, stats_db)
        home_info = extract_team_uv_components(home_box, stats_db)

    # 9이닝 시뮬레이션
    away_expected_score = simulate_9_innings(away_info["lineup_uvs"], home_info)
    home_expected_score = simulate_9_innings(home_info["lineup_uvs"], away_info)

    # 9.0 기준 최종 팀 UV 및 격차 계산
    away_team_uv = away_info["norm_team_uv"]
    home_team_uv = home_info["norm_team_uv"]
    gap = round(abs(home_team_uv - away_team_uv), 2)

    # 예측 및 우세 팀 지정
    if home_team_uv > away_team_uv:
        leading_team = home_team_name
    else:
        leading_team = away_team_name

    if home_expected_score > away_expected_score:
        winner_team = home_team_name
    elif away_expected_score > home_expected_score:
        winner_team = away_team_name
    else:
        winner_team = leading_team

    # 정규화 리포트 출력 포맷 (9.0 UV 기준)
    report = f"""==================================================
⚾ MLB WUV Predictor (9.0 UV 기준)
--------------------------------------------------
[원정팀] {away_team_name}
 • 투수 세부: {away_info['sp_name']}({away_info['sp_uv']:.2f} UV, {away_info['exp_ip']:.1f}이닝) + 불펜({away_info['bp_uv']:.2f} UV, {away_info['bullpen_ip']:.1f}이닝) -> 투수 {away_info['pitcher_overall_uv']:.2f} UV
 • 수비 지분: {away_info['def_share']:.2f} / 4.50 UV (투수 {away_info['pitcher_share']:.2f} | 포수 {away_info['c_share']:.2f} | 야수 {away_info['fld_share']:.2f})
 • 공격 지분: {away_info['off_share']:.2f} / 4.50 UV (1~9번 타선)
 --------------------------------------------------
 • 최종 팀 UV: {away_team_uv:.2f} / 9.00 UV

[홈팀] {home_team_name}
 • 투수 세부: {home_info['sp_name']}({home_info['sp_uv']:.2f} UV, {home_info['exp_ip']:.1f}이닝) + 불펜({home_info['bp_uv']:.2f} UV, {home_info['bullpen_ip']:.1f}이닝) -> 투수 {home_info['pitcher_overall_uv']:.2f} UV
 • 수비 지분: {home_info['def_share']:.2f} / 4.50 UV (투수 {home_info['pitcher_share']:.2f} | 포수 {home_info['c_share']:.2f} | 야수 {home_info['fld_share']:.2f})
 • 공격 지분: {home_info['off_share']:.2f} / 4.50 UV (1~9번 타선)
 --------------------------------------------------
 • 최종 팀 UV: {home_team_uv:.2f} / 9.00 UV
--------------------------------------------------
[예상 스코어] 원정 {away_expected_score:.1f}점 vs 홈 {home_expected_score:.1f}점
[예상 격차] +{gap:.2f} UV ({leading_team} 우세)
[예측 승리팀] {winner_team}
=================================================="""

    print(report)


if __name__ == "__main__":
    run_mlb_single_predictor()
