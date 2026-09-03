#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MLB Automatic Daily Pipeline Script (cron_mlb.py)
Mode:
  --mode predict : Fetch today/tonight's MLB schedule (US date), run 9.0 WUV model, save to mlb_data.db
  --mode score   : Fetch actual results for finished games, calculate accuracy, update mlb_data.db
"""

import sys
import argparse
import datetime
import sqlite3
import requests
import test_mlb_single as engine

BASE_URL = "https://statsapi.mlb.com/api/v1"

def get_us_date():
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    us_now = utc_now - datetime.timedelta(hours=4)
    return us_now.strftime("%Y-%m-%d")

def run_predict(date_str=None):
    if not date_str:
        date_str = get_us_date()
    print(f"=== [PREDICT MODE] Running 9.0 WUV prediction for US date: {date_str} ===")
    
    session = requests.Session()
    url = f"{BASE_URL}/schedule?sportId=1&date={date_str}&hydrate=probablePitcher,lineups,team"
    res = session.get(url, timeout=10).json()
    dates = res.get("dates", [])
    if not dates or not dates[0].get("games"):
        print("No scheduled games found for date:", date_str)
        return
        
    games = dates[0]["games"]
    all_pids = []
    game_details = []
    
    for g in games:
        g_pk = g['gamePk']
        away_team = g['teams']['away']['team']['name']
        home_team = g['teams']['home']['team']['name']
        away_sp = g['teams']['away'].get('probablePitcher', {})
        home_sp = g['teams']['home'].get('probablePitcher', {})
        
        away_sp_id = away_sp.get('id')
        away_sp_name = away_sp.get('fullName', '선발 미정')
        home_sp_id = home_sp.get('id')
        home_sp_name = home_sp.get('fullName', '선발 미정')
        
        box_url = f"{BASE_URL}/game/{g_pk}/boxscore"
        try:
            box = session.get(box_url, timeout=5).json()
        except Exception:
            box = {}
            
        away_box = box.get('teams', {}).get('away', {})
        home_box = box.get('teams', {}).get('home', {})
        
        away_pids = away_box.get('pitchers', []) + away_box.get('batters', [])
        home_pids = home_box.get('pitchers', []) + home_box.get('batters', [])
        if away_sp_id: away_pids.append(away_sp_id)
        if home_sp_id: home_pids.append(home_sp_id)
        all_pids.extend(away_pids + home_pids)
        
        game_details.append({
            'game_pk': g_pk,
            'away_team': away_team,
            'home_team': home_team,
            'away_sp_id': away_sp_id,
            'away_sp_name': away_sp_name,
            'home_sp_id': home_sp_id,
            'home_sp_name': home_sp_name,
            'away_box': away_box,
            'home_box': home_box,
            'status': g.get('status', {}).get('detailedState', ''),
            'away_score': g.get('teams', {}).get('away', {}).get('score', 0),
            'home_score': g.get('teams', {}).get('home', {}).get('score', 0)
        })
        
    stats_db = engine.fetch_all_player_stats_batch(session, all_pids)
    
    conn = sqlite3.connect("mlb_data.db")
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS predictions (
        date TEXT,
        home_team TEXT,
        visit_team TEXT,
        predicted_winner TEXT,
        predicted_gap REAL,
        home_uv REAL,
        visit_uv REAL,
        actual_winner TEXT,
        is_correct INTEGER
    )
    ''')
    c.execute("DELETE FROM predictions WHERE date = ?", (date_str,))
    
    for gd in game_details:
        away_info = engine.analyze_team_uv(gd['away_box'], gd['away_sp_id'], gd['away_sp_name'], stats_db)
        home_info = engine.analyze_team_uv(gd['home_box'], gd['home_sp_id'], gd['home_sp_name'], stats_db)
        
        away_expected_score = engine.simulate_9_innings(away_info['lineup_uvs'], home_info)
        home_expected_score = engine.simulate_9_innings(home_info['lineup_uvs'], away_info)
        
        away_uv = away_info['norm_team_uv']
        home_uv = home_info['norm_team_uv']
        gap = round(abs(home_uv - away_uv), 2)
        
        leading = gd['home_team'] if home_uv > away_uv else gd['away_team']
        if home_expected_score > away_expected_score:
            pred_winner = gd['home_team']
        elif away_expected_score > home_expected_score:
            pred_winner = gd['away_team']
        else:
            pred_winner = leading
            
        actual_winner = ''
        is_correct = None
        if gd['status'] in ['Final', 'Completed']:
            if gd['home_score'] > gd['away_score']:
                actual_winner = gd['home_team']
            elif gd['away_score'] > gd['home_score']:
                actual_winner = gd['away_team']
            is_correct = 1 if actual_winner == pred_winner else 0
        elif gd['status'] in ['Postponed', 'Cancelled']:
            actual_winner = 'Postponed'
            is_correct = None
            
        c.execute('''
        INSERT INTO predictions (date, home_team, visit_team, predicted_winner, predicted_gap, home_uv, visit_uv, actual_winner, is_correct)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (date_str, gd['home_team'], gd['away_team'], pred_winner, gap, home_uv, away_uv, actual_winner, is_correct))
        
    conn.commit()
    conn.close()
    print(f"Successfully populated {len(game_details)} predictions for {date_str} into mlb_data.db!")

def get_us_score_date():
    try:
        conn = sqlite3.connect("mlb_data.db")
        c = conn.cursor()
        c.execute("SELECT DISTINCT date FROM predictions WHERE actual_winner IS NULL OR actual_winner = '' OR actual_winner = '대기' ORDER BY date ASC")
        rows = c.fetchall()
        conn.close()
        if rows and rows[0][0]:
            return rows[0][0]
    except Exception:
        pass
        
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    us_yesterday = utc_now - datetime.timedelta(hours=24)
    return us_yesterday.strftime("%Y-%m-%d")

def run_score(date_str=None):
    if not date_str:
        date_str = get_us_score_date()
    print(f"=== [SCORE MODE] Scoring game results for US date: {date_str} ===")
    
    session = requests.Session()
    url = f"{BASE_URL}/schedule?sportId=1&date={date_str}&hydrate=team"
    res = session.get(url, timeout=10).json()
    dates = res.get("dates", [])
    if not dates or not dates[0].get("games"):
        print("No games found for date:", date_str)
        return
        
    actual_games = []
    for g in dates[0]["games"]:
        away = g['teams']['away']['team']['name']
        home = g['teams']['home']['team']['name']
        away_score = g['teams']['away'].get('score', 0)
        home_score = g['teams']['home'].get('score', 0)
        status = g.get('status', {}).get('detailedState', '')
        
        if status in ['Final', 'Completed', 'Game Over']:
            winner = home if home_score > away_score else away
            actual_games.append((away, home, winner))
        elif status in ['Postponed', 'Cancelled']:
            actual_games.append((away, home, 'Postponed'))

    conn = sqlite3.connect("mlb_data.db")
    c = conn.cursor()
    c.execute("SELECT rowid, visit_team, home_team, predicted_winner FROM predictions WHERE date = ? ORDER BY rowid ASC", (date_str,))
    rows = c.fetchall()
    
    correct_count = 0
    total_count = 0
    for idx, (rowid, visit_team, home_team, pred_winner) in enumerate(rows):
        if idx < len(actual_games):
            _, _, actual = actual_games[idx]
            if actual == 'Postponed':
                is_correct = None
            else:
                is_correct = 1 if pred_winner == actual else 0
                if is_correct: correct_count += 1
                total_count += 1
            
            c.execute('''
                UPDATE predictions 
                SET actual_winner = ?, is_correct = ? 
                WHERE rowid = ?
            ''', (actual, is_correct, rowid))

    conn.commit()
    conn.close()
    print(f"Scored {total_count} finished games for {date_str} (Accuracy: {correct_count}/{total_count}).")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MLB Cron Pipeline")
    parser.add_argument("--mode", choices=["predict", "score"], required=True, help="Mode: predict or score")
    parser.add_argument("--date", type=str, default=None, help="Target YYYY-MM-DD date")
    args = parser.parse_args()
    
    if args.mode == "predict":
        run_predict(args.date)
    elif args.mode == "score":
        run_score(args.date)
