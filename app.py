import streamlit as st
import sqlite3
import hashlib
import extra_streamlit_components as stx
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="Quantum Interface", layout="wide", page_icon="⚛️")

# ========== FUTURISTIC CSS ==========
st.markdown("""
<style>
 .stApp {
        background: linear-gradient(135deg, #050510 0%, #120A2E 100%);
        color: #E0E0FF;
    }
 .glass-card {
        background: rgba(255, 255, 255, 0.04);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(0, 240, 255, 0.2);
        border-radius: 20px;
        padding: 25px;
        margin-bottom: 20px;
        box-shadow: 0 0 30px rgba(0, 240, 255, 0.1);
    }
 .glow-text {
        background: linear-gradient(90deg, #00F0FF 0%, #A855F7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 38px;
        font-weight: 800;
        text-align: center;
    }
 .post-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(168, 85, 247, 0.3);
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 15px;
    }
 .stButton>button {
        background: linear-gradient(90deg, #A855F7 0%, #00F0FF 100%);
        color: white; border: none; border-radius: 10px;
        padding: 12px 25px; font-weight: 700;
        width: 100%; transition: 0.3s;
    }
 .stButton>button:hover {transform: scale(1.02); box-shadow: 0 0 20px rgba(0, 240, 255, 0.6);}
 .stTextInput>div>div>input,.stTextArea>div>div>textarea {
        background: rgba(255,255,255,0.05); border: 1px solid #00F0FF; color: white; border-radius: 8px;}
 .sidebar.glass-card {padding: 15px;}
</style>
""", unsafe_allow_html=True)

# ========== DATABASE ==========
conn = sqlite3.connect('quantum.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, api_key TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, content TEXT, timestamp TEXT)''')
conn.commit()

cookie_manager = stx.CookieManager()

def hash_pw(password): return hashlib.sha256(password.encode()).hexdigest()

def check_login_cookie():
    cookie = cookie_manager.get(cookie="quantum_user")
    if cookie:
        c.execute("SELECT username FROM users WHERE username=?", (cookie,))
        if c.fetchone():
            st.session_state['logged_in'] = True
            st.session_state['username'] = cookie

def set_login_cookie(username):
    cookie_manager.set(cookie="quantum_user", val=username, expires_at=datetime.now() + timedelta(days=30))

# ========== AUTH FUNCTIONS ==========
def register_user(username, password):
    try:
        c.execute("INSERT INTO users VALUES (?,?,?)", (username, hash_pw(password), ""))
        conn.commit(); return True
    except: return False

def login_user(username, password):
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hash_pw(password)))
    return c.fetchone()

def save_api_key(username, key):
    c.execute("UPDATE users SET api_key=? WHERE username=?", (key, username))
    conn.commit()

def get_api_key(username):
    c.execute("SELECT api_key FROM users WHERE username=?", (username,))
    res = c.fetchone(); return res[0] if res else ""

# ========== FEED FUNCTIONS ==========
def add_post(username, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO posts (username, content, timestamp) VALUES (?,?,?)", (username, content, timestamp))
    conn.commit()

def get_posts():
    c.execute("SELECT * FROM posts ORDER BY id DESC LIMIT 50")
    return c.fetchall()

# ========== APP STATE ==========
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
check_login_cookie()

# ========== LOGIN / REGISTER SCREEN ==========
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown('<h1 class="glow-text">QUANTUM</h1>', unsafe_allow_html=True)
        st.caption("Next Generation Neural Interface")
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["LOGIN", "REGISTER"])
        with tab1:
            user = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            if st.button("ACCESS QUANTUM"):
                if login_user(user, pw):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = user
                    set_login_cookie(user)
                    st.rerun()
                else: st.error("Invalid Credentials")
        
        with tab2:
            new_user = st.text_input("Create Username")
            new_pw = st.text_input("Create Password", type="password")
            if st.button("INITIALIZE ACCOUNT"):
                if register_user(new_user, new_pw): st.success("Account Created! Login now")
                else: st.error("Username Taken")
        st.markdown('</div>', unsafe_allow_html=True)

# ========== MAIN APP: FACEBOOK STYLE FEED ==========
else:
    st.markdown('<h1 class="glow-text">QUANTUM</h1>', unsafe_allow_html=True)
    
    # SIDEBAR: API + PROFILE
    with st.sidebar:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.write(f"### User: {st.session_state['username']}")
        st.write("Status: Online")
        
        st.markdown("---")
        st.write("### API CONFIGURATION")
        api_key = st.text_input("Your API Key", value=get_api_key(st.session_state['username']), type="password")
        if st.button("SAVE API KEY"):
            save_api_key(st.session_state['username'], api_key)
            st.success("API Key Saved!")
        st.caption("Used for connecting to external AI/LLM APIs")
        
        st.markdown("---")
        if st.button("LOGOUT"):
            st.session_state['logged_in'] = False
            cookie_manager.delete("quantum_user")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # MAIN FEED
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        # CREATE POST BOX
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.write("### Create Post")
        new_post = st.text_area("What's on your mind?", height=100, label_visibility="collapsed")
        if st.button("POST"):
            if new_post:
                add_post(st.session_state['username'], new_post)
                st.success("Posted!")
                time.sleep(0.5); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # SCROLLING FEED
        st.write("### Quantum Feed")
        posts = get_posts()
        if not posts:
            st.info("No posts yet. Be the first!")
        
        for post in posts:
            st.markdown('<div class="post-card">', unsafe_allow_html=True)
            st.write(f"**{post[1]}** `· {post[3]}`")
            st.write(post[2])
            colA, colB = st.columns(2)
            with colA: st.button("Like", key=f"like{post[0]}")
            with colB: st.button("Comment", key=f"comment{post[0]}")
            st.markdown('</div>', unsafe_allow_html=True)