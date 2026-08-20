import streamlit as st
import sqlite3
import hashlib
import extra_streamlit_components as stx
from datetime import datetime, timedelta
import time, os

st.set_page_config(page_title="Quantum Interface", layout="wide", page_icon="⚛️")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ========== CSS ==========
st.markdown("""
<style>
.stApp {background: linear-gradient(135deg, #050510 0%, #120A2E 100%); color: #E0E0FF;}
.glass-card {background: rgba(255, 255, 255, 0.04); backdrop-filter: blur(20px); border: 1px solid rgba(0, 240, 255, 0.2); border-radius: 20px; padding: 25px; margin-bottom: 20px;}
.glow-text {background: linear-gradient(90deg, #00F0FF 0%, #A855F7 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 38px; font-weight: 800; text-align: center;}
.post-card,.chat-bubble {background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(15px); border: 1px solid rgba(168, 85, 247, 0.3); border-radius: 15px; padding: 15px; margin-bottom: 10px;}
.me {background: linear-gradient(90deg, #A855F7 0%, #00F0FF 100%); border: none; margin-left: 20%;}
.them {margin-right: 20%;}
.stButton>button {background: linear-gradient(90deg, #A855F7 0%, #00F0FF 100%); color: white; border: none; border-radius: 10px; font-weight: 700; width: 100%;}
</style>
""", unsafe_allow_html=True)

# ========== DATABASE ==========
conn = sqlite3.connect('quantum.db', check_same_thread=False)
c = conn.cursor()

# MIGRATION: Add columns if they don't exist
c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, api_key TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, content TEXT, timestamp TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, message TEXT, timestamp TEXT)''')
try:
    c.execute("ALTER TABLE posts ADD COLUMN media_path TEXT")
    c.execute("ALTER TABLE posts ADD COLUMN media_type TEXT")
except: pass # columns already exist
conn.commit()

cookie_manager = stx.CookieManager()
def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()
def check_login_cookie():
    cookie = cookie_manager.get(cookie="quantum_user")
    if cookie:
        c.execute("SELECT username FROM users WHERE username=?", (cookie,))
        if c.fetchone(): st.session_state['logged_in'] = True; st.session_state['username'] = cookie
def set_login_cookie(u): cookie_manager.set(cookie="quantum_user", val=u, expires_at=datetime.now() + timedelta(days=30))

def register_user(u,p):
    try: c.execute("INSERT INTO users VALUES (?,?,?)", (u, hash_pw(p), "")); conn.commit(); return True
    except: return False
def login_user(u,p): c.execute("SELECT * FROM users WHERE username=? AND password=?", (u, hash_pw(p))); return c.fetchone()
def get_all_users(search=""): 
    c.execute("SELECT username FROM users WHERE username LIKE?", (f"%{search}%",))
    return [row[0] for row in c.fetchall()]

def send_message(sender, receiver, msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO messages (sender, receiver, message, timestamp) VALUES (?,?,?,?)", (sender, receiver, msg, ts))
    conn.commit()
def get_messages(user1, user2):
    c.execute("SELECT * FROM messages WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id ASC", (user1,user2,user2,user1))
    return c.fetchall()

def save_uploaded_file(uploaded_file):
    if uploaded_file is None: return None, None
    file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)
    with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
    media_type = "video" if uploaded_file.type.startswith("video") else "image"
    return file_path, media_type

def add_post(u,content,media_path,media_type): 
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO posts (username, content, media_path, media_type, timestamp) VALUES (?,?,?,?,?)", 
              (u,content,media_path,media_type,ts)); conn.commit()
def get_posts(): 
    c.execute("SELECT * FROM posts ORDER BY id DESC LIMIT 50"); return c.fetchall()

# ========== APP STATE ==========
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'chat_with' not in st.session_state: st.session_state['chat_with'] = None
check_login_cookie()

# ========== LOGIN SCREEN ==========
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown('<h1 class="glow-text">QUANTUM</h1>', unsafe_allow_html=True)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["LOGIN", "REGISTER"])
        with tab1:
            user = st.text_input("Username/Email")
            pw = st.text_input("Password", type="password")
            if st.button("ACCESS QUANTUM"):
                if login_user(user, pw): st.session_state['logged_in'] = True; st.session_state['username'] = user; set_login_cookie(user); st.rerun()
                else: st.error("Invalid Credentials")
        with tab2:
            new_user = st.text_input("Create Username/Email")
            new_pw = st.text_input("Create Password", type="password")
            if st.button("INITIALIZE ACCOUNT"):
                if register_user(new_user, new_pw): st.success("Account Created! Login now")
                else: st.error("Username Taken")
        st.markdown('</div>', unsafe_allow_html=True)

# ========== MAIN APP ==========
else:
    st.markdown('<h1 class="glow-text">QUANTUM</h1>', unsafe_allow_html=True)

    with st.sidebar:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.write(f"### User: {st.session_state['username']}")
        tab1, tab2 = st.tabs(["Feed", "Messages"])

        with tab2:
            st.write("### Your Contacts")
            search_query = st.text_input("🔍 Search users...", key="search")
            users = get_all_users(search_query)
            for u in users:
                if u!= st.session_state['username']:
                    if st.button(f"💬 {u}", key=f"chatbtn{u}", use_container_width=True):
                        st.session_state['chat_with'] = u
                        st.rerun()

        if st.button("LOGOUT"):
            st.session_state['logged_in'] = False; cookie_manager.delete("quantum_user"); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:

        if st.session_state['chat_with']:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.write(f"### Chat with {st.session_state['chat_with']}")
            if st.button("← Back to Feed"): st.session_state['chat_with'] = None; st.rerun()

            chat_container = st.container(height=400)
            with chat_container:
                messages = get_messages(st.session_state['username'], st.session_state['chat_with'])
                for msg in messages:
                    sender = msg[1]
                    bubble_class = "me" if sender == st.session_state['username'] else "them"
                    st.markdown(f'<div class="chat-bubble {bubble_class}"><b>{sender}</b><br>{msg[3]}<br><small>{msg[4]}</small></div>', unsafe_allow_html=True)

            new_msg = st.text_input("Type message...", key="msg_input")
            if st.button("SEND") and new_msg:
                send_message(st.session_state['username'], st.session_state['chat_with'], new_msg)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        else:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.write("### Create Post")
            new_post = st.text_area("What's on your mind?", height=80, label_visibility="collapsed")
            uploaded_file = st.file_uploader("Upload Photo or Video", type=['png','jpg','jpeg','mp4','mov'])
            
            if st.button("POST"):
                if new_post or uploaded_file:
                    media_path, media_type = save_uploaded_file(uploaded_file)
                    add_post(st.session_state['username'], new_post, media_path, media_type)
                    st.success("Posted!")
                    time.sleep(0.5); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

            st.write("### Quantum Feed")
            for post in get_posts():
                # FIX: Handle old posts that don't have media columns
                post_id, username, content, *rest = post
                timestamp = rest[-1]
                media_path = rest[0] if len(rest) >= 3 else None
                media_type = rest[1] if len(rest) >= 3 else None
                
                st.markdown(f'<div class="post-card">', unsafe_allow_html=True)
                st.write(f"**{username}** <small>· {timestamp}</small>")
                if content: st.write(content)
                
                if media_path:
                    if media_type == "image":
                        st.image(media_path)
                    elif media_type == "video":
                        st.video(media_path)
                st.markdown('</div>', unsafe_allow_html=True)