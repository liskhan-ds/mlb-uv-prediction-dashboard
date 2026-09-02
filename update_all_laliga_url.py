import os, re, subprocess

base_dir = '/Users/kimwoongsub/My_Projects/Unit Value'
projects = ['NBA', 'MLB', 'EPL', 'LLG', 'NHL', 'NFL', 'MLS']

def get_nav_code_col(cur):
    items = [
        ('NBA', '🏀 NBA', 'https://nba-uv-prediction.streamlit.app/'),
        ('MLB', '⚾ MLB', 'https://mlb-uv-prediction.streamlit.app/'),
        ('EPL', '⚽ EPL', 'https://epl-uv-prediction.streamlit.app/'),
        ('LLG', '⚽ La Liga', 'https://llg-uv-prediction.streamlit.app/'),
        ('NHL', '🏒 NHL', 'https://nhl-uv-prediction.streamlit.app/'),
        ('NFL', '🏈 NFL', 'https://nfl-uv-prediction.streamlit.app/'),
        ('MLS', '⚽ MLS', 'https://mls-uv-prediction.streamlit.app/'),
    ]
    lines = ['# Top Navigation Bar (7 Leagues)']
    lines.append('nav_cols = st.columns(7)')
    for idx, (code, label, url) in enumerate(items):
        lines.append(f'with nav_cols[{idx}]:')
        if code == cur:
            lines.append(f'    st.button("{label} (Current)", disabled=True, use_container_width=True)')
        else:
            lines.append(f'    st.link_button("{label} ↗", "{url}", use_container_width=True)')
    return '\n'.join(lines)

for p in projects:
    p_dir = os.path.join(base_dir, p)
    for fname in ['app.py', 'dashboard.py']:
        app_path = os.path.join(p_dir, fname)
        if not os.path.exists(app_path): continue
        if p == 'MLB' and fname == 'app.py': continue # already updated
        
        with open(app_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        nav_replacement = get_nav_code_col(p)
        
        pattern = r'(?:nav_col1, nav_col2|nav_cols = st\.columns).*?\nst\.divider\(\)'
        if re.search(pattern, content, flags=re.DOTALL):
            updated = re.sub(pattern, nav_replacement + '\n\nst.divider()', content, flags=re.DOTALL)
            with open(app_path, 'w', encoding='utf-8') as f:
                f.write(updated)
            print(f'✅ {p:5s}/{fname} La Liga URL updated!')
        else:
            print(f'⚠️ {p:5s}/{fname} pattern NOT matched!')

print('\n=== Verifying Python Syntax ===')
for p in projects:
    p_dir = os.path.join(base_dir, p)
    res = subprocess.run(['python3', '-m', 'py_compile', 'app.py'], cwd=p_dir, capture_output=True, text=True)
    if res.returncode == 0:
        print(f'✅ {p:5s} app.py py_compile SUCCESS')
    else:
        print(f'❌ {p:5s} app.py py_compile FAILED: {res.stderr}')

print('\n=== Git Commit & Push Across All 7 Repositories ===')
for p in projects:
    p_dir = os.path.join(base_dir, p)
    subprocess.run(['git', 'add', '-A'], cwd=p_dir)
    res_commit = subprocess.run(['git', 'commit', '-m', 'Update La Liga URL to llg-uv-prediction and label to La Liga'], cwd=p_dir, capture_output=True, text=True)
    res_push = subprocess.run(['git', 'push', 'origin', 'main'], cwd=p_dir, capture_output=True, text=True)
    print(f'{p:5s} -> Commit: {res_commit.returncode}, Push: {res_push.returncode}')
