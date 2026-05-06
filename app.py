import streamlit as st
from streamlit_autorefresh import st_autorefresh
import time
import pandas as pd

# ==========================================
# 1. 동적 데이터 세팅 (Session State 로 풀 관리)
# ==========================================
if 'map_pool' not in st.session_state:
    st.session_state.map_pool = {
        "Control": ["Busan", "Lijiang Tower", "Oasis"],
        "Hybrid": ["Blizzard World", "Midtown", "Numbani"],
        "Push / Flashpoint": ["Esperanca", "Runasapi", "Aatlis", "Suravasa"],
        "Escort": ["Havana", "Rialto", "Watchpoint: Gibraltar"]
    }

if 'hero_pool' not in st.session_state:
    st.session_state.hero_pool = {
        "DPS": ["Anran", "Ashe", "Bastion", "Cassidy", "Echo", "Emre", "Freja", 
                "Genji", "Hanzo", "Junkrat", "Mei", "Pharah", "Reaper", "Sierra", 
                "Sojourn", "Soldier: 76", "Sombra", "Symmetra", "Torbjörn", "Tracer", "Vendetta", "Venture", "Widowmaker"],
        "Tank": ["D.Va", "Domina", "Doomfist", "Hazard", "Junker Queen", "Mauga", "Orisa", 
                 "Ramattra", "Reinhardt", "Roadhog", "Sigma", "Winston", "Wrecking Ball", "Zarya"],
        "SUP": ["Ana", "Baptiste", "Brigitte", "Illari", "Jetpack Cat", "Juno", "Kiriko", 
                "Lifeweaver", "Lúcio", "Mercy", "Mizuki", "Moira", "Wuyang", "Zenyatta"]
    }

if 'presets' not in st.session_state:
    st.session_state.presets = {
        "CB": ["Argon", "ZeSin", "FARMER", "SeungAn", "WoochaN", "Faith"],
        "CR": ["LIP", "HeeSang", "Stalk3r", "JunBin", "MAX", "CH0R0NG", "vigilante"],
        "NE": ["perr", "D0D0", "SoLA", "Yate", "MCD", "Secret"],
        "PF": ["M1NUT2", "D4RT", "FEARFUL", "Gur3um", "TenTen", "Sp1nel", "CARU"],
        "RONG": ["HAKSAL", "Kilo", "SP1NT", "Attack", "OPENER", "iRONY"],
        "T1": ["Proud", "ZEST", "DONGHAK", "Jasm1ne", "Bliss", "skewed"],
        "FLC": ["Sp9rk1e", "Checkmate", "Mer1t", "HanBin", "Someone", "ChiYo", "Fielder"],
        "ZAN": ["A1IEN", "Becky", "Heiser", "YangJun", "KIVIS", "Havira"],
        "ZETA": ["Proper", "Knife", "Bernar", "Mealgaru", "Shu", "Viol2t"]
    }

# ==========================================
# 2. 글로벌 상태 관리 (MatchState)
# ==========================================
@st.cache_resource
class MatchState:
    def __init__(self):
        self.tokens = {"Admin": "admin123", "Team A": "a_team", "Team B": "b_team"}
        self.tournament_name = "2026 OWCS KOREA Stage 1"
        self.match_title = "4/26 Match 1"
        self.team_names = {"Team A": "Team A", "Team B": "Team B"}
        self.full_rosters = {"Team A": [], "Team B": []}
        
        self.match_score = {"Team A": 0, "Team B": 0}
        self.current_set = 1
        self.phase = "SETUP" 
        self.active_team = None
        self.loser_team = None 
        self.history = [] 
        
        self.global_ban_history = {"Team A": [], "Team B": []}
        self.ban_log_display = {"Team A": [], "Team B": []} 
        self.ban_records = {} 
        self.map_log_display = []                           
        self.used_maps = []
        self.used_modes = []
        self.prev_rosters = {"Team A": [], "Team B": []}
        self.team_warnings = {"Team A": 0, "Team B": 0}
        
        self.timer_running = False
        self.interaction_enabled = False 
        self.start_time = 0
        self.warning_processed = False
        self.timing_logs = [] 
        
        self.init_set_vars()

    def init_set_vars(self):
        self.selected_mode = ""
        self.selected_map = ""
        self.side_blue = ""
        self.side_red = ""
        self.current_rosters = {"Team A": [], "Team B": []}
        self.subs_in = {"Team A": [], "Team B": []}
        self.subs_out = {"Team A": [], "Team B": []}
        self.subs_revealed = False 
        self.ban_order = [] 
        self.initial_ban = ""
        self.follow_up_ban = ""
        self.locked_role = None 
        self.timer_running = False
        self.interaction_enabled = False
        self.warning_processed = False

    # [업데이트] 자리 이동도 교체로 인식하도록 인덱스 단위로 비교
    def calc_subs(self, team_key, new_roster):
        if self.current_set == 1: return [], []
        prev = self.prev_rosters[team_key]
        curr = new_roster
        
        if not prev or len(prev) != len(curr): 
            return [], []
            
        ins = []
        outs = []
        for p, c in zip(prev, curr):
            if p != c:
                outs.append(p)
                ins.append(c)
        return ins, outs

    def start_timer(self):
        self.timer_running = True
        self.interaction_enabled = True 
        self.start_time = time.time()
        self.warning_processed = False

    def stop_timer(self):
        self.timer_running = False
        self.interaction_enabled = False 

    def add_timing_log(self, step_name, team_key):
        elapsed = time.time() - self.start_time
        t_name = self.team_names.get(team_key, team_key)
        self.timing_logs.append(f"[{step_name}] {t_name}: {elapsed:.1f}s")

    def add_warning(self, team):
        self.team_warnings[team] += 1
        return self.team_warnings[team]

state = MatchState()

if 'temp_mode' not in st.session_state: st.session_state.temp_mode = ""
if 'temp_map' not in st.session_state: st.session_state.temp_map = ""
if 'temp_hero' not in st.session_state: st.session_state.temp_hero = ""
if 'temp_selected_role' not in st.session_state: st.session_state.temp_selected_role = ""

# ==========================================
# 3. 권한 인증
# ==========================================
raw_token = "observer"
if hasattr(st, "query_params"):
    if "token" in st.query_params: raw_token = st.query_params["token"]
elif hasattr(st, "experimental_get_query_params"):
    q_params = st.experimental_get_query_params()
    if "token" in q_params: raw_token = q_params["token"]

if isinstance(raw_token, list): user_token = str(raw_token[0])
else: user_token = str(raw_token)

my_role = "Observer"
for role, tk in state.tokens.items():
    if user_token.strip() == tk.strip() and tk.strip() != "":
        my_role = role

st.set_page_config(layout="wide", page_title="OWCS Pro Dashboard")
st_autorefresh(interval=1000, key="data_refresh")

# ==========================================
# 4. 타이머 컴포넌트
# ==========================================
def render_timer(default_time, overtime=30, active_team=None):
    if not state.timer_running or not active_team:
        if my_role in ["Team A", "Team B"]:
            st.markdown(f"<div style='text-align:center; padding:10px; font-size:24px; font-weight:bold; color:#2E86C1; border-bottom:3px solid #ccc;'>⏳ Waiting ({default_time}s)</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='text-align:center; padding:10px; font-size:24px; font-weight:bold; color:#2E86C1; border-bottom:3px solid #ccc;'>⏳ 대기 중 ({default_time}s)</div>", unsafe_allow_html=True)
        return

    elapsed = time.time() - state.start_time
    
    if elapsed > default_time and not state.warning_processed:
        state.warning_processed = True
        cnt = state.add_warning(active_team)
        if cnt >= 3:
            st.error(f"🛑 {state.team_names[active_team]} Warning 3/3! Restarting set.")
            state.loser_team = "Team B" if active_team == "Team A" else "Team A"
            state.active_team = state.loser_team
            state.init_set_vars()
            state.phase = "MAP_PICK"
            st.rerun()

    if elapsed > (default_time + overtime):
        state.add_warning(active_team)
        state.add_timing_log("TimeOut Forced", active_team)
        if state.phase in ["BAN_1", "BAN_2"]:
            if state.phase == "BAN_1": state.initial_ban = "No Ban"
            else: state.follow_up_ban = "No Ban"
            state.stop_timer()
            state.phase = "BAN_2" if state.phase == "BAN_1" else "COMPLETED"
        else:
            state.stop_timer()
            st.error("Time Out! Admin action required.")
        st.rerun()

    if elapsed > default_time:
        rem = int((default_time + overtime) - elapsed)
        label = "Overtime" if my_role in ["Team A", "Team B"] else "추가 시간"
        st.markdown(f"<div style='text-align:center; padding:10px; font-size:24px; font-weight:bold; color:#d9534f; border-bottom:3px solid #d9534f; animation: blink 1s infinite;'>🚨 {label}: {rem}s</div>", unsafe_allow_html=True)
    else:
        rem = int(default_time - elapsed)
        label = "Time Left" if my_role in ["Team A", "Team B"] else "남은 시간"
        st.markdown(f"<div style='text-align:center; padding:10px; font-size:24px; font-weight:bold; color:#2E86C1; border-bottom:3px solid #2E86C1;'>⏱️ {label}: {rem}s</div>", unsafe_allow_html=True)

# ==========================================
# 선수용 상단 정보 노트
# ==========================================
def render_player_header(team_key):
    st.markdown(f"### 🎮 {state.team_names[team_key]} Dashboard (Set {state.current_set})")
    
    opp_key = "Team B" if team_key == "Team A" else "Team A"
    
    maps_to_show = list(state.map_log_display)
    if state.selected_map:
        maps_to_show.append(f"<span style='color:#0078D7;'>Set {state.current_set} {state.selected_map} (Current)</span>")
    map_str = '<br>'.join(maps_to_show) if maps_to_show else 'None'
    
    my_bans_list = list(state.ban_log_display[team_key])
    opp_bans_list = list(state.ban_log_display[opp_key])
    
    if state.phase in ["BAN_2", "COMPLETED"]:
        first_banner = state.ban_order[0]
        if first_banner == team_key and state.initial_ban:
            my_bans_list.append(f"<span style='color:#0078D7;'>Set {state.current_set} {state.initial_ban} (Current)</span>")
        elif first_banner == opp_key and state.initial_ban:
            opp_bans_list.append(f"<span style='color:#0078D7;'>Set {state.current_set} {state.initial_ban} (Current)</span>")

    if state.phase == "COMPLETED":
        second_banner = state.ban_order[1]
        if second_banner == team_key and state.follow_up_ban:
            my_bans_list.append(f"<span style='color:#0078D7;'>Set {state.current_set} {state.follow_up_ban} (Current)</span>")
        elif second_banner == opp_key and state.follow_up_ban:
            opp_bans_list.append(f"<span style='color:#0078D7;'>Set {state.current_set} {state.follow_up_ban} (Current)</span>")

    my_bans_str = '<br>'.join(my_bans_list) if my_bans_list else 'None'
    opp_bans_str = '<br>'.join(opp_bans_list) if opp_bans_list else 'None'
    
    st.markdown(f"""
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid #0078D7; margin-bottom: 10px;">
        <h4 style="margin-top:0;">📋 Current Match Status</h4>
        <table style="width:100%; border-collapse: collapse; font-size:14px;">
            <tr style="border-bottom:1px solid #ddd; background-color: #f1f3f5;">
                <th style="width:33%; padding:8px; text-align:center;">🗺️ Used Maps</th>
                <th style="width:33%; padding:8px; text-align:center;">Our Team's Bans</th>
                <th style="width:33%; padding:8px; text-align:center;">Opponent's Bans</th>
            </tr>
            <tr>
                <td style="padding:10px; vertical-align:top; text-align:center; font-weight:bold;">{map_str}</td>
                <td style="padding:10px; vertical-align:top; text-align:center; color:#d9534f; font-weight:bold;">{my_bans_str}</td>
                <td style="padding:10px; vertical-align:top; text-align:center; color:#d9534f; font-weight:bold;">{opp_bans_str}</td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

    if state.subs_revealed:
        def get_roster_text(t_key):
            current = state.current_rosters[t_key]
            if not current: return "Waiting for selection..."
            roster_str = f"<div style='margin-bottom:8px; font-size:15px;'><b>Roster:</b> {', '.join(current)}</div>"
            if state.current_set > 1:
                ins = state.subs_in[t_key]
                outs = state.subs_out[t_key]
                if not ins and not outs:
                    roster_str += "<span style='color:#d9534f; font-weight:bold;'>No Subs</span>"
                else:
                    roster_str += f"<span style='color:#d9534f;'><b>OUT:</b> {', '.join(outs)}</span> &nbsp;➡️&nbsp; <span style='color:#0078D7;'><b>IN:</b> {', '.join(ins)}</span>"
            return roster_str
            
        st.markdown(f"""
        <div style="background-color: #e8f4f8; padding: 15px; border-radius: 8px; border-left: 5px solid #28a745; margin-bottom: 20px;">
            <h4 style="margin-top:0; color:#155724;">🔄 Both Teams' Rosters & Sub Info</h4>
            <table style="width:100%; border-collapse: collapse; font-size:14px; text-align:center;">
                <tr>
                    <td style="width:50%; border-right:1px solid #ccc; padding:15px; vertical-align:top;"><b>{state.team_names['Team A']}</b><br><br>{get_roster_text('Team A')}</td>
                    <td style="width:50%; padding:15px; vertical-align:top;"><b>{state.team_names['Team B']}</b><br><br>{get_roster_text('Team B')}</td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

    if not state.interaction_enabled and my_role == state.active_team:
        st.warning("⏳ Clicks are locked until the Admin starts the timer.")

# ==========================================
# 5. 무대 배치도(좌석 지정) 렌더링 함수
# ==========================================
def render_stage_roster_selection(team_key):
    st.markdown("**👥 2. Roster Setup (Stage Layout)**")
    
    st.markdown("""
        <div style='text-align:center; background:#1A5276; color:white; padding:12px; margin-bottom:10px; border-radius:5px; font-weight:bold; font-size:18px; letter-spacing: 2px;'>
            SCREEN
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
        <div style='text-align:center; background:#2980B9; color:white; padding:8px; margin-bottom:20px; border-radius:5px; font-weight:bold; font-size:16px;'>
            {state.team_names[team_key]} SEATS
        </div>
    """, unsafe_allow_html=True)

    if f"picks_{team_key}" not in st.session_state or len(st.session_state[f"picks_{team_key}"]) != 5:
        if state.current_set == 1:
            st.session_state[f"picks_{team_key}"] = ["(Empty)", "(Empty)", "(Empty)", "(Empty)", "(Empty)"]
        else:
            prev = list(state.prev_rosters[team_key])
            st.session_state[f"picks_{team_key}"] = prev + ["(Empty)"] * (5 - len(prev))

    roster_opts = ["(Empty)"] + state.full_rosters[team_key]
    seat_labels = ["⚔️ DPS 1", "⚔️ DPS 2", "🛡️ TANK", "💉 SUP 1", "💉 SUP 2"]
    
    cols = st.columns(5)
    current_picks = []
    
    for i in range(5):
        with cols[i]:
            val = st.session_state[f"picks_{team_key}"][i]
            idx = roster_opts.index(val) if val in roster_opts else 0
            
            selected = st.selectbox(
                seat_labels[i], 
                roster_opts, 
                index=idx, 
                key=f"slot_{i}_{state.phase}", 
                disabled=(not state.interaction_enabled)
            )
            current_picks.append(selected)
            st.session_state[f"picks_{team_key}"][i] = selected
            
    return current_picks

# ==========================================
# 6. 어드민 사이드바
# ==========================================
if my_role == "Admin":
    with st.sidebar:
        st.header("🎛️ OWCS Admin Panel")
        st.caption("접속 권한: Admin")
        
        with st.expander("🔗 1. 토큰 설정 및 링크 공유"):
            c_t1, c_t2, c_t3 = st.columns(3)
            new_tk_admin = c_t1.text_input("Admin 토큰", state.tokens["Admin"])
            new_tk_a = c_t2.text_input("A팀 토큰", state.tokens["Team A"])
            new_tk_b = c_t3.text_input("B팀 토큰", state.tokens["Team B"])
            if st.button("💾 토큰 업데이트"):
                state.tokens["Admin"] = new_tk_admin.strip()
                state.tokens["Team A"] = new_tk_a.strip()
                state.tokens["Team B"] = new_tk_b.strip()
                st.rerun()
                
            # [업데이트] 주소 뒤에 / 가 생기지 않도록 깔끔하게 처리
            base_url = st.text_input("기본 주소", "https://owcskoo3.streamlit.app").rstrip('/')
            
            team_a_label = state.team_names['Team A'] if state.team_names['Team A'] != "Team A" else "A팀"
            team_b_label = state.team_names['Team B'] if state.team_names['Team B'] != "Team B" else "B팀"
            
            st.code(f"Admin: {base_url}?token={state.tokens['Admin']}")
            st.code(f"{team_a_label}: {base_url}?token={state.tokens['Team A']}")
            st.code(f"{team_b_label}: {base_url}?token={state.tokens['Team B']}")

        with st.expander("🛠️ 2. 팀 프리셋(Roster) 관리"):
            preset_action = st.selectbox("기존 팀 관리", ["새 팀 추가"] + list(st.session_state.presets.keys()))
            new_t_name = st.text_input("팀명", preset_action if preset_action != "새 팀 추가" else "")
            new_t_roster = st.text_area("로스터 (쉼표)", ", ".join(st.session_state.presets[preset_action]) if preset_action != "새 팀 추가" else "")
            
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("💾 프리셋 저장"):
                    if new_t_name:
                        st.session_state.presets[new_t_name] = [x.strip() for x in new_t_roster.split(",") if x.strip()]
                        st.success(f"[{new_t_name}] 저장 완료!")
                        st.rerun()
            with c_btn2:
                if preset_action != "새 팀 추가" and st.button("❌ 삭제"):
                    del st.session_state.presets[preset_action]
                    st.success(f"[{preset_action}] 삭제 완료!")
                    st.rerun()

        with st.expander("🛠️ 3. 맵 및 영웅 풀(Pool) 관리"):
            st.markdown("전장 및 영웅 목록을 쉼표(,)로 구분하여 추가/수정/삭제할 수 있습니다.")
            st.markdown("#### 🗺️ 맵 풀 (Map Pool)")
            new_maps = {}
            for mode, maps in st.session_state.map_pool.items():
                new_maps[mode] = st.text_area(f"{mode} Maps", ", ".join(maps), key=f"mp_{mode}")
            
            st.markdown("#### 🦸 영웅 풀 (Hero Pool)")
            new_heroes = {}
            for role, heroes in st.session_state.hero_pool.items():
                new_heroes[role] = st.text_area(f"{role} Heroes", ", ".join(heroes), key=f"hp_{role}")
                
            if st.button("💾 맵/영웅 풀 전체 업데이트", type="primary"):
                for mode in new_maps:
                    st.session_state.map_pool[mode] = [m.strip() for m in new_maps[mode].split(",") if m.strip()]
                for role in new_heroes:
                    st.session_state.hero_pool[role] = [h.strip() for h in new_heroes[role].split(",") if h.strip()]
                st.success("맵과 영웅 목록이 업데이트되었습니다!")
                st.rerun()

        with st.expander("⚙️ 4. 경기 초기 세팅", expanded=(state.phase=="SETUP")):
            tourney = st.text_input("대회명", state.tournament_name)
            preset_opts = ["직접 입력"] + list(st.session_state.presets.keys())
            c_p1, c_p2 = st.columns(2)
            preset_a = c_p1.selectbox("Team A 프리셋", preset_opts)
            preset_b = c_p2.selectbox("Team B 프리셋", preset_opts)
            title = st.text_input("매치명", state.match_title)
            name_a = st.text_input("Team A 이름", preset_a if preset_a != "직접 입력" else state.team_names["Team A"])
            name_b = st.text_input("Team B 이름", preset_b if preset_b != "직접 입력" else state.team_names["Team B"])
            rost_a = st.text_area(f"{name_a} 로스터", ", ".join(st.session_state.presets[preset_a]) if preset_a != "직접 입력" else "")
            rost_b = st.text_area(f"{name_b} 로스터", ", ".join(st.session_state.presets[preset_b]) if preset_b != "직접 입력" else "")
            
            if st.button("✅ 경기 시작", type="primary"):
                state.tournament_name = tourney
                state.match_title = title
                state.team_names = {"Team A": name_a, "Team B": name_b}
                state.full_rosters["Team A"] = [x.strip() for x in rost_a.split(",") if x.strip()]
                state.full_rosters["Team B"] = [x.strip() for x in rost_b.split(",") if x.strip()]
                
                state.prev_rosters = {"Team A": [], "Team B": []}
                state.history = []
                state.global_ban_history = {"Team A": [], "Team B": []}
                state.ban_log_display = {"Team A": [], "Team B": []}
                state.ban_records = {} 
                state.map_log_display = []
                state.used_maps = []
                state.used_modes = []
                state.current_set = 1
                
                state.loser_team = "Team B" 
                state.active_team = "Team B"
                state.phase = "MAP_PICK"
                st.rerun()
        
        if state.phase != "SETUP":
            if not state.timer_running and st.button("▶️ 타이머 시작 및 화면 잠금 해제", type="primary"):
                state.start_timer()
                st.rerun()
            if st.button("🚨 경기 강제 종료"): state.phase = "MATCH_SUMMARY"; st.rerun()

# ==========================================
# 7. 대시보드 렌더링 (어드민/관전자용)
# ==========================================
CSS_BLOCK = """
<style>
    .owcs-board { width: 100%; border-collapse: collapse; text-align: center; font-family: 'Segoe UI', Arial; font-size: 14px; background: white; color: black; border: 2px solid #000; margin-bottom: 20px; }
    .owcs-board th, .owcs-board td { border: 1px solid #000; padding: 4px; vertical-align: middle; }
    .bg-title { background-color: #FFF2CC; font-weight: bold; }
    .bg-green { background-color: #E2EFDA; font-weight: bold; }
    .bg-pink { background-color: #EED7E8; font-weight: bold; }
    .bg-blue { background-color: #BDD7EE; }
    .bg-red { background-color: #F8CBAD; }
</style>
"""

def render_dashboard():
    display_map = state.selected_map if state.selected_map else st.session_state.temp_map
    m_mode = state.selected_mode if state.selected_mode else (st.session_state.temp_mode if st.session_state.temp_mode else "-")
    m_blue = state.team_names.get(state.side_blue, "-")
    m_red = state.team_names.get(state.side_red, "-")
    picker_name = state.team_names.get(state.loser_team, "-")
    ban1 = state.initial_ban if state.initial_ban else "-"
    ban2 = state.follow_up_ban if state.follow_up_ban else "-"

    def mc(map_name, colspan=1):
        cs = f" colspan='{colspan}'" if colspan > 1 else ""
        if map_name == display_map: return f"<td{cs} style='background-color: yellow; font-weight: bold;'>{map_name}</td>"
        elif map_name in state.used_maps: return f"<td{cs} style='background-color: #D3D3D3; color: #888; text-decoration: line-through;'>{map_name}</td>"
        return f"<td{cs}>{map_name}</td>"

    def get_map_cells(mode):
        maps = st.session_state.map_pool.get(mode, [])
        cells = ""
        if not maps: return "<td colspan='4'></td>"
        for i, m in enumerate(maps):
            if i == len(maps) - 1: cells += mc(m, max(1, 4 - i))
            else: cells += mc(m, 1)
        return cells

    def mode_cell(mode_name):
        bg = "background-color: #D3D3D3; color: #888; text-decoration: line-through;" if mode_name in state.used_modes else ""
        return f"<td class='bg-green' style='{bg}'>{mode_name}</td>"

    def build_sub_rows(team_key):
        if not state.subs_revealed and state.phase in ["MAP_PICK", "SUB_PICK_A", "WAIT_REVEAL"]:
            return "<tr><td colspan='2' style='color:#7F8C8D; font-weight:bold; padding:4px;'>🔒 비공개 (진행 중)</td></tr>"
        
        if state.current_set == 1:
            roster = state.current_rosters.get(team_key, [])
            if roster: return f"<tr><td colspan='2' style='font-weight:bold; padding:4px; color:#0078D7;'>출전: {', '.join(roster)}</td></tr>"
            else: return "<tr><td colspan='2' style='color:#7F8C8D; padding:4px;'>선택 대기 중</td></tr>"
                
        ins, outs = state.subs_in[team_key], state.subs_out[team_key]
        if not ins and not outs: 
            return "<tr><td colspan='2' style='color:#d9534f; font-weight:bold; padding:4px;'>교체 없음 (No Subs)</td></tr>"
            
        rows = ""
        for i in range(max(len(ins), len(outs))):
            rows += f"<tr><td style='width:50%;'>{outs[i] if i<len(outs) else ''}</td><td style='width:50%;'>{ins[i] if i<len(ins) else ''}</td></tr>"
        return rows

    t1 = state.team_names.get(state.ban_order[0], "") if state.ban_order else ""
    t2 = state.team_names.get(state.ban_order[1], "") if len(state.ban_order)>1 else ""
    
    html = f"""
    <table class="owcs-board">
        <tr><th colspan="7" class="bg-title" style="font-size: 1.3em; padding:8px;">{state.tournament_name}</th></tr>
        <tr><th colspan="3" class="bg-title">{state.match_title}</th><th colspan="2" class="bg-title">{state.team_names['Team A']}</th><th colspan="2" class="bg-title">{state.team_names['Team B']}</th></tr>
        <tr>
            <td rowspan="4" class="bg-green">Losing Team<br><br><b>{picker_name}</b></td>
            <td class="bg-green">mode</td> {mode_cell('Control')} {get_map_cells('Control')}
        </tr>
        <tr><td rowspan="3" class="bg-green">map</td> {mode_cell('Hybrid')} {get_map_cells('Hybrid')}</tr>
        <tr>{mode_cell('Push / Flashpoint')} {get_map_cells('Push / Flashpoint')}</tr>
        <tr>{mode_cell('Escort')} {get_map_cells('Escort')}</tr>
        <tr><td colspan="2" class="bg-green">side</td><td class="bg-green">side</td><td colspan="2" class="bg-blue">DEF / BLUE<br><b>{m_blue}</b></td><td colspan="2" class="bg-red">ATK / RED<br><b>{m_red}</b></td></tr>
        <tr><td colspan="7" style="border:none; height:10px; background:#f0f2f6;"></td></tr>
        <tr><td rowspan="2" class="bg-pink">Roster</td><td class="bg-pink">{state.team_names['Team A']}</td><td class="bg-pink">Sub</td><td colspan="4" style="padding:0;"><table style="width:100%; border-collapse:collapse;"><tr><th style="width:50%;">OUT</th><th>IN</th></tr>{build_sub_rows('Team A')}</table></td></tr>
        <tr><td class="bg-pink">{state.team_names['Team B']}</td><td class="bg-pink">Sub</td><td colspan="4" style="padding:0;"><table style="width:100%; border-collapse:collapse;"><tr><th style="width:50%;">OUT</th><th>IN</th></tr>{build_sub_rows('Team B')}</table></td></tr>
        <tr><td colspan="7" style="border:none; height:10px; background:#f0f2f6;"></td></tr>
        <tr><td colspan="2" class="bg-green">Losing Team : {picker_name}</td><td colspan="2" class="bg-green">Hero bans</td><td colspan="2" style="background:#f2f2f2;">Initial Ban ({t1})<br><b style='color:red;'>{ban1}</b></td><td style="background:#f2f2f2;">Follow-up Ban ({t2})<br><b style='color:red;'>{ban2}</b></td></tr>
    </table>
    """
    
    def build_hero_grid(role, heroes_list, cols=7):
        banned_current = []
        if state.initial_ban:
            t1_name = state.team_names.get(state.ban_order[0], "") if state.ban_order else ""
            banned_current.append((state.initial_ban, t1_name))
        if state.follow_up_ban:
            t2_name = state.team_names.get(state.ban_order[1], "") if len(state.ban_order)>1 else ""
            banned_current.append((state.follow_up_ban, t2_name))

        h_html = f"<tr><th colspan='{cols}' style='background:#EAEAEA; border:2px solid #000;'>{role}</th></tr>"
        for i in range(0, len(heroes_list), cols):
            h_html += "<tr>"
            for j in range(cols):
                if i + j < len(heroes_list):
                    h = heroes_list[i+j]
                    
                    labels = list(state.ban_records.get(h, []))
                    is_current_ban = False
                    
                    for curr_b, curr_t in banned_current:
                        if h == curr_b:
                            is_current_ban = True
                            labels.append(f"{state.current_set}세트 {curr_t} 밴")
                    
                    if is_current_ban:
                        label_str = "<br>".join([f"<span style='font-size:0.75em;'>({l})</span>" for l in labels])
                        h_html += f"<td style='border:1px solid #000; width:{100/cols}%; background-color:#ffe6e6; color:#d9534f; font-weight:bold;'>{h}<br>{label_str}</td>"
                    elif labels:
                        label_str = "<br>".join([f"<span style='font-size:0.75em;'>({l})</span>" for l in labels])
                        h_html += f"<td style='border:1px solid #000; width:{100/cols}%; background-color:#EAEAEA; color:#555; font-weight:bold;'>{h}<br>{label_str}</td>"
                    else:
                        h_html += f"<td style='border:1px solid #000; width:{100/cols}%; font-weight:500; color:black;'>{h}</td>"
                else: h_html += "<td style='border:1px solid #000;'></td>"
            h_html += "</tr>"
        return h_html

    hero_html = build_hero_grid("DPS", st.session_state.hero_pool.get("DPS", [])) + \
                build_hero_grid("Tank", st.session_state.hero_pool.get("Tank", [])) + \
                build_hero_grid("SUP", st.session_state.hero_pool.get("SUP", []))
    
    st.markdown(CSS_BLOCK + " ".join(html.split()), unsafe_allow_html=True)
    st.markdown(f"<table class='owcs-board'>{hero_html}</table>", unsafe_allow_html=True)

if state.phase != "SETUP" and my_role in ["Admin", "Observer"]:
    render_dashboard()

# ==========================================
# 8. 단계별 로직
# ==========================================
st.markdown("<style>.stButton>button { width: 100%; font-weight: bold; }</style>", unsafe_allow_html=True)

def submit_roster_logic(team_key, picks, is_map_pick=False):
    state.current_rosters[team_key] = list(picks)
    ins, outs = state.calc_subs(team_key, picks)
    state.subs_in[team_key] = ins
    state.subs_out[team_key] = outs
    
    if is_map_pick:
        state.selected_mode = st.session_state.temp_mode
        state.selected_map = st.session_state.temp_map
        st.session_state.temp_map = ""
        state.active_team = "Team B" if team_key == "Team A" else "Team A"
        state.phase = "SUB_PICK_A"
    else:
        state.phase = "WAIT_REVEAL"
    
    state.stop_timer()
    st.rerun()

if state.phase == "MAP_PICK":
    render_timer(90, active_team=state.active_team)
    if my_role == state.active_team:
        render_player_header(my_role)
        st.subheader("📍 1. Map & Side Selection")
        
        for mode, maps in st.session_state.map_pool.items():
            if mode in state.used_modes: continue
            map_chunks = [maps[i:i+4] for i in range(0, max(len(maps), 1), 4)]
            for chunk_idx, chunk in enumerate(map_chunks):
                cols = st.columns([2, 2, 2, 2, 2])
                if chunk_idx == 0:
                    cols[0].markdown(f"<div style='background:#eee; height:100%; display:flex; align-items:center; justify-content:center; border:1px solid #ccc; font-weight:bold;'>{mode}</div>", unsafe_allow_html=True)
                else:
                    cols[0].write("")
                    
                for i in range(4):
                    with cols[i+1]:
                        if i < len(chunk):
                            m_name = chunk[i]
                            if m_name in state.used_maps: 
                                st.button(f"🚫 {m_name}", disabled=True, key=f"m_{m_name}")
                            else:
                                btn_type = "primary" if st.session_state.temp_map == m_name else "secondary"
                                if st.button(f"✅ {m_name}" if btn_type=="primary" else m_name, type=btn_type, disabled=(not state.interaction_enabled), key=f"m_{m_name}"):
                                    st.session_state.temp_mode, st.session_state.temp_map = mode, m_name
                                    st.rerun()
                        else: st.markdown("<div style='border:1px solid #ccc; height:100%;'></div>", unsafe_allow_html=True)
                        
        col_s, col_r = st.columns([1, 3])
        with col_s:
            side = st.radio("Select Side", ["BLUE (Defend First)", "RED (Attack First)"], disabled=(not state.interaction_enabled))
        with col_r:
            p_list = render_stage_roster_selection(my_role)

        st.divider()
        if st.button("🚀 Final Submit", type="primary", disabled=(not state.interaction_enabled)):
            valid_picks = [p for p in p_list if p != "(Empty)"]
            
            if not st.session_state.temp_map: 
                st.error("Please select a map first.")
            elif len(valid_picks) != 5: 
                st.error("Please fill all 5 seats.")
            elif len(set(valid_picks)) != 5:
                st.error("Duplicate players found! A player can only take one seat.")
            else:
                state.selected_mode, state.selected_map = st.session_state.temp_mode, st.session_state.temp_map
                if "BLUE" in side: state.side_blue, state.side_red = my_role, ("Team B" if my_role=="Team A" else "Team A")
                else: state.side_red, state.side_blue = my_role, ("Team B" if my_role=="Team A" else "Team A")
                state.add_timing_log("Map/Side Selection", my_role)
                submit_roster_logic(my_role, valid_picks, is_map_pick=True)
                
    elif my_role in ["Team A", "Team B"]:
        render_player_header(my_role); st.info("The opponent is selecting the map and roster... (Sub info hidden)")

elif state.phase == "SUB_PICK_A":
    render_timer(60, active_team=state.active_team)
    if my_role == state.active_team:
        render_player_header(my_role)
        my_side = "BLUE (Defend)" if state.side_blue == my_role else "RED (Attack)"
        st.markdown(f"""
        <div style="background-color: #FFF2CC; padding: 20px; border: 2px solid #F99E1A; border-radius: 10px; text-align: center; margin-bottom: 20px;">
            <h2 style="margin:0; color:#856404;">📍 Opponent's Selection Info</h2>
            <p style="font-size: 24px; margin: 10px 0;">Map: <b>{state.selected_map}</b> ({state.selected_mode})</p>
            <p style="font-size: 20px; color: #155724;">Our Side: <b>{my_side}</b></p>
        </div>
        """, unsafe_allow_html=True)
        
        p_list = render_stage_roster_selection(my_role)
        
        st.divider()
        if st.button("🚀 Submit Roster", type="primary", disabled=(not state.interaction_enabled)):
            valid_picks = [p for p in p_list if p != "(Empty)"]
            
            if len(valid_picks) != 5: 
                st.error("Please fill all 5 seats.")
            elif len(set(valid_picks)) != 5:
                st.error("Duplicate players found! A player can only take one seat.")
            else:
                state.add_timing_log("Roster Selection", my_role)
                submit_roster_logic(my_role, valid_picks, is_map_pick=False)
    elif my_role in ["Team A", "Team B"]:
        render_player_header(my_role); st.info("The opponent is deciding their roster...")

elif state.phase == "WAIT_REVEAL":
    if my_role in ["Team A", "Team B"]: render_player_header(my_role); st.info("Waiting for Admin to reveal... ⏳")
    if my_role == "Admin":
        if st.button("📢 양 팀 정보 전체 공개", type="primary"):
            state.subs_revealed = True
            state.phase = "BAN_ORDER"
            state.active_team = state.loser_team
            st.rerun()

elif state.phase == "BAN_ORDER":
    render_timer(30, active_team=state.active_team)
    if my_role == state.active_team:
        render_player_header(my_role); st.subheader("⚖️ Decide Ban Order")
        c1, c2 = st.columns(2)
        other = "Team B" if my_role=="Team A" else "Team A"
        if c1.button("👉 We Ban First", disabled=(not state.interaction_enabled)): 
            state.add_timing_log("Ban Order (First)", my_role); state.ban_order = [my_role, other]; state.phase = "BAN_1"; state.stop_timer(); st.rerun()
        if c2.button("👉 We Ban Second", disabled=(not state.interaction_enabled)): 
            state.add_timing_log("Ban Order (Second)", my_role); state.ban_order = [other, my_role]; state.phase = "BAN_1"; state.stop_timer(); st.rerun()
    elif my_role in ["Team A", "Team B"]: render_player_header(my_role); st.info("Opponent is deciding the ban order...")

elif state.phase in ["BAN_1", "BAN_2"]:
    cur = state.ban_order[0] if state.phase == "BAN_1" else state.ban_order[1]
    render_timer(60, active_team=cur)
    if my_role == cur:
        render_player_header(my_role)
        
        if state.phase == "BAN_2":
            opp = state.ban_order[0]
            st.error(f"🚨 **Opponent ({state.team_names[opp]}) banned [ {state.initial_ban} ]!** (Locked Role: {state.locked_role} cannot be selected)")
            
        def render_heroes(role, h_list):
            st.markdown(f"**{role}**")
            cols = st.columns(7)
            for i, h in enumerate(h_list):
                with cols[i%7]:
                    is_u = h in state.global_ban_history[my_role]
                    is_l = (state.phase=="BAN_2" and role==state.locked_role)
                    if st.button(f"🚫 {h}" if is_u else (f"✅ {h}" if st.session_state.temp_hero==h else h), disabled=(is_u or is_l or not state.interaction_enabled), key=f"bh_{h}"):
                        st.session_state.temp_hero, st.session_state.temp_selected_role = h, role; st.rerun()
                        
        render_heroes("DPS", st.session_state.hero_pool.get("DPS", []))
        render_heroes("Tank", st.session_state.hero_pool.get("Tank", []))
        render_heroes("SUP", st.session_state.hero_pool.get("SUP", []))
        
        if st.session_state.temp_hero and st.button(f"🚀 Confirm {st.session_state.temp_hero} Ban", type="primary", disabled=(not state.interaction_enabled)):
            state.add_timing_log("Hero Ban", cur)
            if state.phase == "BAN_1": state.initial_ban, state.locked_role, state.phase = st.session_state.temp_hero, st.session_state.temp_selected_role, "BAN_2"
            else: state.follow_up_ban, state.phase = st.session_state.temp_hero, "COMPLETED"
            st.session_state.temp_hero = ""; state.stop_timer(); st.rerun()
    elif my_role in ["Team A", "Team B"]: render_player_header(my_role); st.info("The opponent is banning a hero...")

elif state.phase == "COMPLETED":
    if my_role in ["Team A", "Team B"]: render_player_header(my_role); st.success("🏁 All Ban/Picks completed! Good luck.")
    if my_role == "Admin":
        with st.form("res"):
            st.info(f"결과: {state.selected_map} | 선밴: {state.initial_ban} | 후밴: {state.follow_up_ban}")
            c1, c2 = st.columns(2); sa = c1.number_input(f"{state.team_names['Team A']} 점수", 0); sb = c2.number_input(f"{state.team_names['Team B']} 점수", 0)
            
            if st.form_submit_button("다음 세트로 진행 (승자 저장)"):
                t1_name = state.team_names.get(state.ban_order[0], "") if state.ban_order else ""
                t2_name = state.team_names.get(state.ban_order[1], "") if len(state.ban_order) > 1 else ""
                
                hist_entry = {
                    "Set": state.current_set,
                    "Map Picker": state.team_names.get(state.loser_team, ""),
                    "Mode": state.selected_mode,
                    "Map": state.selected_map,
                    "Blue (DEF)": state.team_names.get(state.side_blue, ""),
                    "Red (ATK)": state.team_names.get(state.side_red, ""),
                    "First Ban": f"{state.initial_ban} ({t1_name})" if state.initial_ban else "None",
                    "Second Ban": f"{state.follow_up_ban} ({t2_name})" if state.follow_up_ban else "None",
                    f"{state.team_names['Team A']} Roster": ", ".join(state.current_rosters.get("Team A", [])),
                    f"{state.team_names['Team B']} Roster": ", ".join(state.current_rosters.get("Team B", [])),
                    "제출 소요 시간(Log)": " / ".join(state.timing_logs),
                    "Score": f"{sa} : {sb}"
                }
                state.history.append(hist_entry)
                
                win = "Team A" if sa > sb else "Team B"
                state.match_score[win] += 1
                
                state.used_maps.append(state.selected_map)
                state.map_log_display.append(f"Set {state.current_set} {state.selected_map}")
                state.used_modes.append(state.selected_mode)
                
                if len(state.used_modes)>=4: state.used_modes=[]
                
                if state.initial_ban and state.initial_ban != "No Ban": 
                    state.global_ban_history[state.ban_order[0]].append(state.initial_ban)
                    state.ban_log_display[state.ban_order[0]].append(f"Set {state.current_set} {state.initial_ban}")
                    if state.initial_ban not in state.ban_records: state.ban_records[state.initial_ban] = []
                    state.ban_records[state.initial_ban].append(f"{state.current_set}세트 {t1_name} 밴")
                    
                if state.follow_up_ban and state.follow_up_ban != "No Ban": 
                    state.global_ban_history[state.ban_order[1]].append(state.follow_up_ban)
                    state.ban_log_display[state.ban_order[1]].append(f"Set {state.current_set} {state.follow_up_ban}")
                    if state.follow_up_ban not in state.ban_records: state.ban_records[state.follow_up_ban] = []
                    state.ban_records[state.follow_up_ban].append(f"{state.current_set}세트 {t2_name} 밴")
                    
                state.prev_rosters["Team A"], state.prev_rosters["Team B"] = list(state.current_rosters["Team A"]), list(state.current_rosters["Team B"])
                state.current_set += 1; state.loser_team = "Team B" if sa > sb else "Team A"
                state.active_team = state.loser_team; state.init_set_vars(); state.phase = "MAP_PICK"; st.rerun()

elif state.phase == "MATCH_SUMMARY":
    if my_role in ["Team A", "Team B"]:
        st.title("📊 Match Summary")
    else:
        st.title("📊 최종 기록")
    
    if state.history:
        df = pd.DataFrame(state.history)
        if my_role != "Admin" and "제출 소요 시간(Log)" in df.columns:
            df = df.drop(columns=["제출 소요 시간(Log)"])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        if my_role in ["Team A", "Team B"]:
            st.info("No match history saved yet.")
        else:
            st.info("아직 저장된 세트 기록이 없습니다.")
        
    if my_role == "Admin" and st.button("새 매치 시작", type="primary"): 
        state.__init__()
        st.rerun()
