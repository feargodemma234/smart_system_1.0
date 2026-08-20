import streamlit as st
import sqlite3
import hashlib
import extra_streamlit_components as stx
from datetime import datetime, timedelta
import time, os
import requests

st.set_page_config(page_title="Quantum Interface", layout="wide", page_icon="⚛️")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ========== CSS - FLOATING AI CHAT ==========
st.markdown("""
<style>
.stApp {background: linear-gradient(135deg, #050510 0%, #120A2E 100%); color: #E0E0FF;}
.glass-card {background: rgba(255, 255, 255, 0.04); backdrop-filter: blur(20px); border: 1px solid rgba(0, 240, 255, 0.2); border-radius: 20px; padding: 25px; margin-bottom: 20px;}
.glow-text {background: linear-gradient(90deg, #00F0FF 0%, #A855F7 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 38px; font-weight: 800; text-align: center;}
.post-card,.chat-bubble {background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(15px); border: 1px solid rgba(168, 85, 247, 0.3); border-radius: 15px; padding: 15px; margin-bottom: 10px;}
.ai-bubble {border: 1px solid #00F0FF; background: rgba(0, 240, 255, 0.1);}
.me {background: linear-gradient(90deg, #A855F7 0%, #00F0FF 100%); border: none; margin-left: 20%;}
.them {margin-right: 20%;}
.stButton>button {background: linear-gradient(90deg, #A855F7 0%, #00F0FF 100%); color: white; border: none; border-radius: 10px; font-weight: 700; width: 100%;}

/* FLOATING AI BUTTON */
.ai-float-btn {
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 9999;
    background: linear-gradient(90deg, #A855F7 0%, #00F0FF 100%);
    color: white;
    border: none;
    border-radius: 50%;
    width: 60px;
    height: 60px;
    font-size: 28px;
    cursor: pointer;
    box-shadow: 0 0 20px rgba(0, 240, 255, 0.5);
}
/* FLOATING AI WINDOW */
.ai-float-window {
    position: fixed;
    bottom: 90px;
    right: 20px;
    width: 350px;
    height: 500px;
    z-index: 9998;
    background: rgba(18, 10, 46, 0.95);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(0, 240, 255, 0.3);
    border-radius: 20px;
    padding: 15px;
    display: flex;
    flex-direction: column;
}
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

# ========== AI FUNCTIONS ==========
def save_ai_message(username, role, message):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO ai_chats (username, role, message, timestamp) VALUES (?,?,?,?)", (username, role, message, ts))
    conn.commit()

def get_ai_chat_history(username):
    c.execute("SELECT role, message FROM ai_chats WHERE username=? ORDER BY id ASC LIMIT 20", (username,))
    return c.fetchall()

def call_groq_api(api_key, messages):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "openai/gpt-oss-120b", "messages": messages, "temperature": 0.7}
    try:
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=40)
        return res.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"⚠️ Error: {e}"

# ========== OTHER FUNCTIONS ==========
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
if 'ai_open' not in st.session_state: st.session_state['ai_open'] = False # NEW
check_login_cookie()

# ========== LOGIN SCREEN ==========
if not st.session_state['logged_in']:
    #... same login code...
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
        st.write(f"### User: {st.session_state['username']}")
        
        # GROQ API KEY IN SIDEBAR
        api_key = st.text_input("Groq API Key", value=get_api_key(st.session_state['username']), type="password")
        if st.button("SAVE KEY"): save_api_key(st.session_state['username'], api_key); st.success("Saved")
        
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

    # MAIN AREA: FEED OR DM
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.session_state['chat_with']:
            # DM CODE
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.write(f"### Chat with {st.session_state['chat_with']}")
            if st.button("← Back to Feed"): st.session_state['chat_with'] = None; st.rerun()
            chat_container = st.container(height=400)
            with chat_container:
                for msg in get_messages(st.session_state['username'], st.session_state['chat_with']):
                    sender = msg[1]
                    bubble_class = "me" if sender == st.session_state['username'] else "them"
                    st.markdown(f'<div class="chat-bubble {bubble_class}"><b>{sender}</b><br>{msg[3]}<br><small>{msg[4]}</small></div>', unsafe_allow_html=True)
            new_msg = st.text_input("Type message...", key="msg_input")
            if st.button("SEND") and new_msg: send_message(st.session_state['username'], st.session_state['chat_with'], new_msg); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            # FEED CODE
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.write("### Create Post")
            new_post = st.text_area("What's on your mind?", height=80, label_visibility="collapsed")
            uploaded_file = st.file_uploader("Upload Photo or Video", type=['png','jpg','jpeg','mp4','mov'])
            if st.button("POST"):
                if new_post or uploaded_file:
                    media_path, media_type = save_uploaded_file(uploaded_file)
                    add_post(st.session_state['username'], new_post, media_path, media_type)
                    st.success("Posted!"); time.sleep(0.5); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            st.write("### Quantum Feed")
            for post in get_posts():
                post_id, username, content, media_path, media_type, timestamp = post + (None,None) if len(post)==4 else post
                st.markdown(f'<div class="post-card">', unsafe_allow_html=True)
                st.write(f"**{username}** <small>· {timestamp}</small>")
                if content: st.write(content)
                if media_path:
                    if media_type == "image": st.image(media_path)
                    elif media_type == "video": st.video(media_path)
                st.markdown('</div>', unsafe_allow_html=True)

    # ========== FLOATING AI CHAT BOTTOM RIGHT ==========
    # BUTTON TO TOGGLE
    if st.button("🤖", key="ai_toggle_btn"):
        st.session_state['ai_open'] = not st.session_state['ai_open']
        st.rerun()
    
    # AI WINDOW
    if st.session_state['ai_open']:
        with st.container():
            st.markdown('<div class="ai-float-window">', unsafe_allow_html=True)
            st.write("### QUANTUM AI")
            
            ai_chat = st.container(height=350)
            with ai_chat:
                history = get_ai_chat_history(st.session_state['username'])
                for role, msg in history:
                    bubble = "ai-bubble" if role=="assistant" else "me"
                    label = "AI" if role=="assistant" else "You"
                    st.markdown(f'<div class="chat-bubble {bubble}"><b>{label}</b><br>{msg}</div>', unsafe_allow_html=True)
            
            ai_input = st.text_input("Ask AI...", key="ai_input", label_visibility="collapsed")
            colA, colB = st.columns([3,1])
            with colA:
                if st.button("SEND", key="ai_send"):
                    if api_key:
                        save_ai_message(st.session_state['username'], "user", ai_input)
                        messages = [{"role": "system", "content": "You are Quantum AI, helpful assistant."}]
                        messages += [{"role": r, "content": m} for r, m in history]
                        messages.append({"role": "user", "content": ai_input})
                        ai_response = call_groq_api(api_key, messages)
                        save_ai_message(st.session_state['username'], "assistant", ai_response)
                        st.rerun()
                    else: st.warning("Add Groq API key in sidebar")
            with colB:
                if st.button("X", key="ai_close"): st.session_state['ai_open'] = False; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)