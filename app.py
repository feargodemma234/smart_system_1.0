import streamlit as st
import sqlite3
import hashlib
import extra_streamlit_components as stx
from datetime import datetime, timedelta
import time, os
import requests

st.set_page_config(page_title="Quantum Interface", layout="wide", page_icon="⚛️", initial_sidebar_state="collapsed")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ========== CSS - FIXED FOR MOBILE ==========
st.markdown("""
<style>
.stApp {background: linear-gradient(135deg, #050510 0%, #120A2E 100%); color: #E0E0FF; padding-bottom: 80px;}
.glass-card {background: rgba(255, 255, 255, 0.04); backdrop-filter: blur(20px); border: 1px solid rgba(0, 240, 255, 0.2); border-radius: 20px; padding: 20px; margin-bottom: 15px;}
.glow-text {background: linear-gradient(90deg, #00F0FF 0%, #A855F7 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 32px; font-weight: 800; text-align: center;}
.post-card,.chat-bubble {background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(15px); border: 1px solid rgba(168, 85, 247, 0.3); border-radius: 15px; padding: 12px; margin-bottom: 8px; font-size: 14px; word-wrap: break-word;}
.ai-bubble {border: 1px solid #00F0FF; background: rgba(0, 240, 255, 0.1);}
.me {background: linear-gradient(90deg, #A855F7 0%, #00F0FF 100%); border: none; margin-left: 15%; color: white;}
.them {margin-right: 15%;}

/* FLOATING AI BUTTON */
div.stButton > button[key="ai_toggle_btn"] {
    position: fixed!important;
    bottom: 15px!important;
    right: 15px!important;
    z-index: 9999!important;
    background: linear-gradient(90deg, #A855F7 0%, #00F0FF 100%)!important;
    color: white!important;
    border: none!important;
    border-radius: 50%!important;
    width: 50px!important;
    height: 50px!important;
    font-size: 22px!important;
    box-shadow: 0 0 15px rgba(0, 240, 255, 0.6)!important;
    padding: 0!important;
}

/* FLOATING AI WINDOW - SMALL */
.ai-float-window {
    position: fixed;
    bottom: 75px;
    right: 15px;
    width: 300px;
    max-width: 85vw;
    height: 400px;
    max-height: 65vh;
    z-index: 9998;
    background: rgba(10, 5, 30, 0.98);
    backdrop-filter: blur(25px);
    border: 1px solid rgba(0, 240, 255, 0.4);
    border-radius: 18px;
    padding: 10px;
    display: flex;
    flex-direction: column;
    box-shadow: 0 0 25px rgba(0, 240, 255, 0.3);
}
.ai-chat-history {
    flex: 1;
    overflow-y: auto;
    margin-bottom: 8px;
}
.ai-input-area {
    flex-shrink: 0;
}

#MainMenu, footer, header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ========== DATABASE ==========
conn = sqlite3.connect('quantum.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, api_key TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, content TEXT, media_path TEXT, media_type TEXT, timestamp TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, message TEXT, timestamp TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS ai_chats (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, message TEXT, timestamp TEXT)''')
try:
    c.execute("ALTER TABLE posts ADD COLUMN media_path TEXT")
    c.execute("ALTER TABLE posts ADD COLUMN media_type TEXT")
except: pass
conn.commit()

cookie_manager = stx.CookieManager()
def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()
def check_login_cookie():
    cookie = cookie_manager.get(cookie="quantum_user")
    if cookie:
        c.execute("SELECT username FROM users WHERE username=?", (cookie,))
        if c.fetchone(): st.session_state['logged_in'] = True; st.session_state['username'] = cookie
def set_login_cookie(u): cookie_manager.set(cookie="quantum_user", val=u, expires_at=datetime.now() + timedelta(days=30))
def get_api_key(u): c.execute("SELECT api_key FROM users WHERE username=?", (u,)); res=c.fetchone(); return res[0] if res else ""
def save_api_key(u,key): c.execute("UPDATE users SET api_key=? WHERE username=?", (key,u)); conn.commit()
def get_all_users(search=""): 
    c.execute("SELECT username FROM users WHERE username LIKE?", (f"%{search}%",))
    return [row[0] for row in c.fetchall()]

# ========== AI FUNCTIONS FOR GROQ ==========
def save_ai_message(username, role, message):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO ai_chats (username, role, message, timestamp) VALUES (?,?,?,?)", (username, role, message, ts))
    conn.commit()

def get_ai_chat_history(username):
    c.execute("SELECT role, message FROM ai_chats WHERE username=? ORDER BY id ASC LIMIT 15", (username,))
    return c.fetchall()

def clear_ai_chat(username):
    c.execute("DELETE FROM ai_chats WHERE username=?", (username,))
    conn.commit()

def call_groq_api(api_key, messages):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "openai/gpt-oss-120b", "messages": messages, "temperature": 0.7, "max_tokens": 512}
    try:
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        return res.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"⚠️ Error: Check Groq API key at console.groq.com"

# ========== POST + DM FUNCTIONS ==========
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
    c.execute("SELECT * FROM posts ORDER BY id DESC LIMIT 30"); return c.fetchall()

# ========== APP STATE ==========
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'chat_with' not in st.session_state: st.session_state['chat_with'] = None
if 'ai_open' not in st.session_state: st.session_state['ai_open'] = False
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
                if c.execute("SELECT * FROM users WHERE username=? AND password=?", (user, hash_pw(pw))).fetchone(): 
                    st.session_state['logged_in'] = True; st.session_state['username'] = user; set_login_cookie(user); st.rerun()
                else: st.error("Invalid Credentials")
        with tab2:
            new_user = st.text_input("Create Username/Email")
            new_pw = st.text_input("Create Password", type="password")
            if st.button("INITIALIZE ACCOUNT"):
                try: c.execute("INSERT INTO users VALUES (?,?,?)", (new_user, hash_pw(new_pw), "")); conn.commit(); st.success("Account Created!")
                except: st.error("Username Taken")
        st.markdown('</div>', unsafe_allow_html=True)

# ========== MAIN APP ==========
else:
    st.markdown('<h1 class="glow-text">QUANTUM</h1>', unsafe_allow_html=True)

    # SIDEBAR
    with st.sidebar:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.write(f"### {st.session_state['username']}")
        api_key = st.text_input("Groq API Key", value=get_api_key(st.session_state['username']), type="password")
        if st.button("SAVE KEY"): save_api_key(st.session_state['username'], api_key); st.success("Saved")
        st.caption("Get free key: console.groq.com")
        st.write("---")
        st.write("### Messages")
        search_query = st.text_input("🔍 Search", key="search")
        users = get_all_users(search_query)
        for u in users:
            if u!= st.session_state['username']:
                if st.button(f"💬 {u}", key=f"chatbtn{u}", use_container_width=True):
                    st.session_state['chat_with'] = u
                    st.rerun()
        if st.button("LOGOUT"):
            st.session_state['logged_in'] = False; cookie_manager.delete("quantum_user"); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # MAIN AREA
    if st.session_state['chat_with']:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.write(f"### Chat with {st.session_state['chat_with']}")
        if st.button("← Back"): st.session_state['chat_with'] = None; st.rerun()
        chat_container = st.container(height=350)
        with chat_container:
            for msg in get_messages(st.session_state['username'], st.session_state['chat_with']):
                sender = msg[1]
                bubble_class = "me" if sender == st.session_state['username'] else "them"
                st.markdown(f'<div class="chat-bubble {bubble_class}"><b>{sender}</b><br>{msg[3]}</div>', unsafe_allow_html=True)
        new_msg = st.text_input("Type...", key="msg_input")
        if st.button("SEND") and new_msg: send_message(st.session_state['username'], st.session_state['chat_with'], new_msg); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.write("### Create Post")
        new_post = st.text_area("", height=70, label_visibility="collapsed", placeholder="What's on your mind?")
        uploaded_file = st.file_uploader("", type=['png','jpg','jpeg','mp4','mov'])
        if st.button("POST"):
            if new_post or uploaded_file:
                media_path, media_type = save_uploaded_file(uploaded_file)
                add_post(st.session_state['username'], new_post, media_path, media_type)
                st.success("Posted!"); time.sleep(0.3); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.write("### Feed")
        for post in get_posts():
            post_id, username, content, media_path, media_type, timestamp = post + (None,None) if len(post)==4 else post
            st.markdown(f'<div class="post-card">', unsafe_allow_html=True)
            st.write(f"**{username}** · <small>{timestamp}</small>", unsafe_allow_html=True)
            if content: st.write(content)
            if media_path:
                if media_type == "image": st.image(media_path)
                elif media_type == "video": st.video(media_path)
            st.markdown('</div>', unsafe_allow_html=True)

    # ========== FLOATING AI BOTTOM RIGHT ==========
    if st.button("🤖", key="ai_toggle_btn"):
        st.session_state['ai_open'] = not st.session_state['ai_open']
        st.rerun()
    
    if st.session_state['ai_open']:
        st.markdown('<div class="ai-float-window">', unsafe_allow_html=True)
        
        # HEADER
        colh1, colh2 = st.columns([4,1])
        with colh1: st.write("#### QUANTUM AI")
        with colh2: 
            if st.button("X", key="ai_close"): 
                st.session_state['ai_open'] = False 
                st.rerun()
        
        # CHAT HISTORY
        st.markdown('<div class="ai-chat-history">', unsafe_allow_html=True)
        history = get_ai_chat_history(st.session_state['username'])
        if not history: st.caption("Ask me anything")
        for role, msg in history:
            bubble = "ai-bubble" if role=="assistant" else "me"
            label = "AI" if role=="assistant" else "You"
            st.markdown(f'<div class="chat-bubble {bubble}"><b>{label}</b><br>{msg}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # INPUT - ALWAYS VISIBLE
        st.markdown('<div class="ai-input-area">', unsafe_allow_html=True)
        ai_input = st.text_input("", key="ai_input", placeholder="Type to AI...", label_visibility="collapsed")
        colA, colB = st.columns([4,1])
        with colA:
            if st.button("Send", key="ai_send", use_container_width=True):
                if not api_key: st.warning("Add Groq API key in sidebar")
                elif ai_input:
                    save_ai_message(st.session_state['username'], "user", ai_input)
                    messages = [{"role": "system", "content": "You are Quantum AI, a helpful assistant."}]
                    messages += [{"role": r, "content": m} for r, m in history]
                    messages.append({"role": "user", "content": ai_input})
                    with st.spinner("..."):
                        ai_response = call_groq_api(api_key, messages)
                    save_ai_message(st.session_state['username'], "assistant", ai_response)
                    st.rerun()
        with colB:
            if st.button("🗑️", key="ai_clear"): 
                clear_ai_chat(st.session_state['username'])
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)