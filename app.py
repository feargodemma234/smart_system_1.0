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
.stApp {background: linear-gradient(135deg, #050510 0%, #120A2E 100%); color: #E0E0FF; padding-bottom: 40px;}
.glass-card {background: rgba(255, 255, 255, 0.04); backdrop-filter: blur(20px); border: 1px solid rgba(0, 240, 255, 0.2); border-radius: 20px; padding: 20px; margin-bottom: 15px;}
.glow-text {background: linear-gradient(90deg, #00F0FF 0%, #A855F7 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 38px; font-weight: 800; text-align: center;}
.post-card,.chat-bubble {background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(15px); border: 1px solid rgba(168, 85, 247, 0.3); border-radius: 15px; padding: 12px; margin-bottom: 8px; font-size: 14px; word-wrap: break-word;}
.me {background: linear-gradient(90deg, #A855F7 0%, #00F0FF 100%); border: none; margin-left: 20%; color: white;}
.them {margin-right: 20%;}
.stButton>button {background: linear-gradient(90deg, #A855F7 0%, #00F0FF 100%); color: white; border: none; border-radius: 10px; font-weight: 700; width: 100%;}
.small-btn button {background: rgba(255,255,255,0.1)!important; font-size: 13px!important; padding: 5px 10px!important; width: auto!important; margin-right: 8px;}
.delete-btn button {background: #ff4b4b!important; font-size: 12px!important; padding: 2px 8px!important; width: auto!important;}
.comment-box {background: rgba(0,0,0,0.2); border-radius: 10px; padding: 8px; margin-top: 5px; font-size: 13px;}
[data-testid="stSidebar"] {background: linear-gradient(180deg, #050510 0%, #120A2E 100%);}
#MainMenu, footer, header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ========== DATABASE ==========
conn = sqlite3.connect('quantum.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, content TEXT, media_path TEXT, media_type TEXT, timestamp TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, message TEXT, timestamp TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS likes (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, username TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS comments (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, username TEXT, comment TEXT, timestamp TEXT)''')
conn.commit()

cookie_manager = stx.CookieManager()
def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()
def check_login_cookie():
    cookie = cookie_manager.get(cookie="quantum_user")
    if cookie:
        c.execute("SELECT username FROM users WHERE username=?", (cookie,))
        if c.fetchone(): st.session_state['logged_in'] = True; st.session_state['username'] = cookie
def set_login_cookie(u): cookie_manager.set(cookie="quantum_user", val=u, expires_at=datetime.now() + timedelta(days=30))

def get_all_users(search=""):
    c.execute("SELECT username FROM users WHERE username LIKE?", (f"%{search}%",))
    return [row[0] for row in c.fetchall()]

# ========== FUNCTIONS ==========
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
def delete_post(post_id, username):
    c.execute("DELETE FROM posts WHERE id=? AND username=?", (post_id, username)); conn.commit()
def toggle_like(post_id, username):
    c.execute("SELECT * FROM likes WHERE post_id=? AND username=?", (post_id, username))
    if c.fetchone(): c.execute("DELETE FROM likes WHERE post_id=? AND username=?", (post_id, username))
    else: c.execute("INSERT INTO likes (post_id, username) VALUES (?,?)", (post_id, username))
    conn.commit()
def get_like_count(post_id):
    c.execute("SELECT COUNT(*) FROM likes WHERE post_id=?", (post_id,))
    return c.fetchone()[0]
def user_liked(post_id, username):
    c.execute("SELECT * FROM likes WHERE post_id=? AND username=?", (post_id, username))
    return c.fetchone() is not None
def add_comment(post_id, username, comment):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO comments (post_id, username, comment, timestamp) VALUES (?,?,?,?)", (post_id, username, comment, ts))
    conn.commit()
def get_comments(post_id):
    c.execute("SELECT * FROM comments WHERE post_id=? ORDER BY id ASC", (post_id,))
    return c.fetchall()

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
                if c.execute("SELECT * FROM users WHERE username=? AND password=?", (user, hash_pw(pw))).fetchone():
                    st.session_state['logged_in'] = True; st.session_state['username'] = user; set_login_cookie(user); st.rerun()
                else: st.error("Invalid Credentials")
        with tab2:
            new_user = st.text_input("Create Username/Email")
            new_pw = st.text_input("Create Password", type="password")
            if st.button("INITIALIZE ACCOUNT"):
                try: c.execute("INSERT INTO users VALUES (?,?)", (new_user, hash_pw(new_pw))); conn.commit(); st.success("Account Created!")
                except: st.error("Username Taken")
        st.markdown('</div>', unsafe_allow_html=True)

# ========== MAIN APP WITH SIDEBAR ==========
else:
    # SIDEBAR WITH PRIVATE CHAT
    with st.sidebar:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.write(f"### {st.session_state['username']}")
        st.write("---")

        # PRIVATE CHAT IN SIDEBAR
        st.write("### 💬 Private Chat")
        search_query = st.text_input("🔍 Search users", placeholder="Type name...")
        users = get_all_users(search_query)
        for u in users:
            if u!= st.session_state['username']:
                if st.button(f"{u}", key=f"chatbtn{u}", use_container_width=True):
                    st.session_state['chat_with'] = u
                    st.rerun()

        st.write("---")
        if st.button("LOGOUT"):
            st.session_state['logged_in'] = False; cookie_manager.delete("quantum_user"); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # MAIN AREA
    st.markdown('<h1 class="glow-text">QUANTUM</h1>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.session_state['chat_with']:
            # CHAT WINDOW IN MAIN AREA
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.write(f"### Chatting with {st.session_state['chat_with']}")
            if st.button("← Back to Feed"): st.session_state['chat_with'] = None; st.rerun()

            chat_container = st.container(height=400)
            with chat_container:
                messages = get_messages(st.session_state['username'], st.session_state['chat_with'])
                if not messages: st.caption("Start the conversation")
                for msg in messages:
                    sender = msg[1]
                    bubble_class = "me" if sender == st.session_state['username'] else "them"
                    st.markdown(f'<div class="chat-bubble {bubble_class}"><b>{sender}</b><br>{msg[3]}</div>', unsafe_allow_html=True)

            colI, colS = st.columns([4,1])
            with colI: new_msg = st.text_input("Type message...", key="msg_input", label_visibility="collapsed")
            with colS:
                if st.button("SEND", use_container_width=True) and new_msg:
                    send_message(st.session_state['username'], st.session_state['chat_with'], new_msg); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            # CREATE POST
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.write("### Create Post")
            new_post = st.text_area("", height=80, label_visibility="collapsed", placeholder="What's on your mind?")
            uploaded_file = st.file_uploader("Upload", type=['png','jpg','jpeg','mp4','mov'])
            st.caption("200MB per file • PNG, JPG, MP4, MOV")
            if st.button("POST"):
                if new_post or uploaded_file:
                    media_path, media_type = save_uploaded_file(uploaded_file)
                    add_post(st.session_state['username'], new_post, media_path, media_type)
                    st.success("Posted!"); time.sleep(0.3); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

            # FEED
            st.write("### Quantum Feed")
            posts = get_posts()
            if not posts: st.caption("No posts yet")
            for post in posts:
                post_id, username, content, media_path, media_type, timestamp = post
                st.markdown(f'<div class="post-card">', unsafe_allow_html=True)

                colp1, colp2 = st.columns([5,1])
                with colp1: st.write(f"**{username}** · <small>{timestamp}</small>", unsafe_allow_html=True)
                with colp2:
                    if username == st.session_state['username']:
                        if st.button("Delete", key=f"del{post_id}"):
                            delete_post(post_id, username); st.rerun()

                if content: st.write(content)
                if media_path:
                    if media_type == "image": st.image(media_path)
                    elif media_type == "video": st.video(media_path)

                # LIKE + COMMENT
                like_count = get_like_count(post_id)
                liked = user_liked(post_id, st.session_state['username'])
                like_text = f"❤️ {like_count}" if liked else f"🤍 {like_count}"

                colL, colC, colSpace = st.columns([1,1,3])
                with colL:
                    st.markdown('<div class="small-btn">', unsafe_allow_html=True)
                    if st.button(like_text, key=f"like{post_id}"):
                        toggle_like(post_id, st.session_state['username']); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with colC:
                    st.markdown('<div class="small-btn">', unsafe_allow_html=True)
                    st.button(f"💬 {len(get_comments(post_id))}", key=f"cbtn{post_id}", disabled=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                # COMMENTS
                for cm in get_comments(post_id):
                    st.markdown(f'<div class="comment-box"><b>{cm[2]}</b>: {cm[3]}</div>', unsafe_allow_html=True)

                new_comment = st.text_input("Write a comment...", key=f"comment{post_id}", label_visibility="collapsed")
                if st.button("Post Comment", key=f"postc{post_id}") and new_comment:
                    add_comment(post_id, st.session_state['username'], new_comment); st.rerun()

                st.markdown('</div>', unsafe_allow_html=True)