import streamlit as st
import sqlite3
import hashlib
import extra_streamlit_components as stx
from datetime import datetime, timedelta

st.set_page_config(page_title="Nexus Login", layout="centered", page_icon="⚡")

# ========== FUTURISTIC CSS ==========
st.markdown("""
<style>
  .stApp {
        background: linear-gradient(135deg, #0A0A1A 0%, #1A0A2E 100%);
        color: #E0E0FF;
    }
  .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(0, 240, 255, 0.3);
        border-radius: 25px;
        padding: 40px;
        box-shadow: 0 0 40px rgba(0, 240, 255, 0.2);
    }
  .glow-text {
        background: linear-gradient(90deg, #00F0FF 0%, #A855F7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 40px;
        font-weight: 800;
        text-align: center;
    }
  .stButton>button {
        background: linear-gradient(90deg, #A855F7 0%, #00F0FF 100%);
        color: white; border: none; border-radius: 12px;
        padding: 14px 30px; font-size: 16px; font-weight: 700;
        width: 100%; transition: 0.3s;
    }
  .stButton>button:hover {transform: scale(1.03); box-shadow: 0 0 25px rgba(0, 240, 255, 0.8);}
  .stTextInput>div>div>input {background: rgba(255,255,255,0.05); border: 1px solid #00F0FF; color: white; border-radius: 8px;}
</style>
""", unsafe_allow_html=True)

# ========== DATABASE + COOKIES ==========
conn = sqlite3.connect('users.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)''')
conn.commit()

cookie_manager = stx.CookieManager()

def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_login_cookie():
    cookie = cookie_manager.get(cookie="nexus_user")
    if cookie and cookie in [row[0] for row in c.execute("SELECT username FROM users").fetchall()]:
        st.session_state['logged_in'] = True
        st.session_state['username'] = cookie

def set_login_cookie(username):
    cookie_manager.set(cookie="nexus_user", val=username, expires_at=datetime.now() + timedelta(days=7))

# ========== AUTH FUNCTIONS ==========
def register_user(username, password):
    try:
        c.execute("INSERT INTO users VALUES (?,?)", (username, hash_pw(password)))
        conn.commit()
        return True
    except:
        return False

def login_user(username, password):
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hash_pw(password)))
    return c.fetchone()

# ========== APP LOGIC ==========
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

check_login_cookie() # This remembers you

if not st.session_state['logged_in']:
    st.markdown('<h1 class="glow-text">NEXUS</h1>', unsafe_allow_html=True)
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.button("LOGIN"):
            if login_user(user, pw):
                st.session_state['logged_in'] = True
                st.session_state['username'] = user
                set_login_cookie(user) # Remember for 7 days
                st.rerun()
            else:
                st.error("Invalid Username or Password")
    
    with tab2:
        new_user = st.text_input("New Username")
        new_pw = st.text_input("New Password", type="password")
        if st.button("CREATE ACCOUNT"):
            if register_user(new_user, new_pw):
                st.success("Account Created! Now Login")
            else:
                st.error("Username already exists")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
else:
    # DASHBOARD AFTER LOGIN
    st.markdown('<h1 class="glow-text">WELCOME BACK</h1>', unsafe_allow_html=True)
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.image("https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=2072&auto=format&fit=crop")
    st.write(f"### Hello, {st.session_state['username']}")
    st.write("Neural Link: Active")
    st.write("System Status: All Clear")
    
    if st.button("LOGOUT"):
        st.session_state['logged_in'] = False
        cookie_manager.delete("nexus_user")
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)