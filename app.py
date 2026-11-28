from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime
import json
import os
import secrets
import time
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import UniqueConstraint

app = Flask(__name__)

# secret_key：优先读环境变量，否则生成随机密钥并持久化到 .secret_key（不再硬编码）
SECRET_KEY_FILE = '.secret_key'

def _load_or_create_secret_key():
    env_key = os.environ.get('SECRET_KEY')
    if env_key:
        return env_key
    if os.path.exists(SECRET_KEY_FILE):
        with open(SECRET_KEY_FILE, 'r', encoding='utf-8') as f:
            key = f.read().strip()
            if key:
                return key
    key = secrets.token_hex(32)
    tmp = SECRET_KEY_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(key)
    os.replace(tmp, SECRET_KEY_FILE)
    return key

app.secret_key = _load_or_create_secret_key()

# ==================== 数据库配置 ====================
# 数据库连接串从环境变量 DATABASE_URL 读取，不再把凭据写死在源码里
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'mysql+pymysql://chat_user:CHANGE_ME@localhost/chat_db?charset=utf8mb4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 上传上限 100MB，防止超大文件拖垮服务

# ==================== 上传配置 ====================
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'mov', 'ogg', 'm4v'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 颜文字面板（点按钮弹出后供选择）
KAOMOJI = ['=ᗜωᗜ=', '=^･ω･^=', '(=^･ｪ･^=)', '(ΦωΦ)', '(=◕‿◕=)', '(๑•̀ㅂ•́)و✧',
           '(｡•̀ᴗ-)✧', '(≧▽≦)', '(◕ᴗ◕✿)', '(づ｡◕‿‿◕｡)づ', '(￣▽￣*)ゞ',
           '(⁄ ⁄•⁄ω⁄•⁄ ⁄)', '(◍•ᴗ•◍)', '(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧', '(；一_一)',
           '(╯°□°)╯︵┻━┻', '(；￣Д￣)', '(＃￣ω￣)', '(>ω<)', '(´｡• ᵕ •｡`)',
           '(￣ω￣)', '(つ≧▽≦)つ', '₍˄·͈༝·͈˄₎ฅ˒˒', '(o^^o)', '(¬‿¬)',
           'ʕ•ᴥ•ʔ', '★~(◠‿◕✿)', '(=￣ω￣=)', '(／▽＼)', '(*^▽^*)']

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_video(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

def save_uploaded_images(files):
    """保存上传的图片，返回文件名列表"""
    image_filenames = []
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = f"{int(time.time())}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            image_filenames.append(filename)
    return image_filenames

def save_uploaded_video(file):
    """保存单个视频文件，返回文件名；无效或为空返回 None"""
    if file and file.filename and allowed_video(file.filename):
        filename = secure_filename(file.filename)
        filename = f"{int(time.time())}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return filename
    return None

def save_avatar(file):
    """保存头像文件，返回文件名；无效或为空返回 None"""
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filename = f"avatar_{int(time.time())}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return filename
    return None

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ==================== 数据模型 ====================

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    nickname = db.Column(db.String(80))
    avatar = db.Column(db.String(200))  # 头像文件名（存 static/uploads）
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    posts = db.relationship('Post', backref='author', lazy=True)
    replies = db.relationship('Reply', backref='author', lazy=True)
    moments = db.relationship('Moment', backref='author', lazy=True)
    moment_comments = db.relationship('MomentComment', backref='author', lazy=True)

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    images = db.Column(db.Text)  # 图片文件名，逗号分隔
    video = db.Column(db.String(200))  # 视频文件名
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    replies = db.relationship('Reply', backref='post', lazy=True, cascade='all, delete-orphan')

class Reply(db.Model):
    __tablename__ = 'replies'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    images = db.Column(db.Text)  # 图片文件名，逗号分隔
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)

class Moment(db.Model):
    """用户动态：文字 + 图片 + 视频"""
    __tablename__ = 'moments'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    images = db.Column(db.Text)  # 图片文件名，逗号分隔
    video = db.Column(db.String(200))  # 视频文件名
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    comments = db.relationship('MomentComment', backref='moment', lazy=True,
                               cascade='all, delete-orphan',
                               order_by='MomentComment.created_at')

class MomentComment(db.Model):
    """动态评论"""
    __tablename__ = 'moment_comments'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    moment_id = db.Column(db.Integer, db.ForeignKey('moments.id'), nullable=False)

class Follow(db.Model):
    """关注关系：follower 关注 followed"""
    __tablename__ = 'follows'
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint('follower_id', 'followed_id', name='uq_follow_pair'),)

class Notification(db.Model):
    """站内通知"""
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # 接收者
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # 触发者
    type = db.Column(db.String(20), nullable=False)  # post / moment / follow
    target_id = db.Column(db.Integer)  # 帖子或动态的 id
    text = db.Column(db.String(200), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ==================== JSON 文件存储（聊天消息） ====================

DATA_FILE = 'messages.json'

def hash_password(password):
    """生成带盐的密码哈希（PBKDF2，比无盐 SHA256 安全）"""
    return generate_password_hash(password)

def load_messages():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_messages(messages):
    temp_file = DATA_FILE + '.tmp'
    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, DATA_FILE)
    except Exception as e:
        print(f"保存失败: {e}")

def get_user_by_ip(ip):
    return f"访客_{ip.replace('.', '_')[-6:]}"

# ==================== 辅助函数 ====================

def current_user_obj():
    """返回当前登录的 User 对象，未登录返回 None"""
    if 'username' in session:
        return User.query.filter_by(username=session['username']).first()
    return None

def notify_followers(actor, ntype, target_id, text):
    """向 actor 的所有关注者发送一条通知"""
    followers = Follow.query.filter_by(followed_id=actor.id).all()
    for f in followers:
        db.session.add(Notification(
            user_id=f.follower_id,
            actor_id=actor.id,
            type=ntype,
            target_id=target_id,
            text=text,
        ))
    db.session.commit()

def count_unread_notifications(user):
    return Notification.query.filter_by(user_id=user.id, is_read=False).count()

@app.context_processor
def inject_globals():
    """向所有模板注入登录用户、未读通知数、表情列表"""
    me = current_user_obj()
    return {
        'me': me,
        'unread_count': count_unread_notifications(me) if me else 0,
        'emojis': KAOMOJI,
    }

# ==================== 路由 ====================

@app.route('/', methods=['GET'])
def chat():
    """大厅：只显示帖子列表，其他什么都不显示"""
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('chat.html', posts=posts)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        nickname = request.form.get('nickname', '').strip() or username
        if not username or not password:
            return '用户名和密码不能为空', 400
        if User.query.filter_by(username=username).first():
            return '用户名已存在', 400
        user = User(
            username=username,
            password=hash_password(password),
            nickname=nickname,
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['username'] = username
            return redirect(url_for('chat'))
        return '用户名或密码错误', 401
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('chat'))

@app.route('/export')
def export():
    messages = load_messages()
    return app.response_class(
        response=json.dumps(messages, ensure_ascii=False, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': 'attachment;filename=chat_backup.json'}
    )

# ==================== 帖子相关路由 ====================

@app.route('/post/new', methods=['GET', 'POST'])
def new_post():
    user = current_user_obj()
    if not user:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        files = request.files.getlist('images')
        video_file = request.files.get('video')

        if not title or not content:
            return '标题和内容不能为空', 400

        image_filenames = save_uploaded_images(files)
        video_filename = save_uploaded_video(video_file)

        post = Post(
            title=title,
            content=content,
            user_id=user.id,
            images=','.join(image_filenames) if image_filenames else None,
            video=video_filename,
        )
        db.session.add(post)
        db.session.commit()
        notify_followers(user, 'post', post.id, f"{user.nickname or user.username} 发布了新帖子《{post.title}》")
        return redirect(url_for('post_detail', post_id=post.id))

    return render_template('new_post.html')

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post_detail.html', post=post)

@app.route('/post/<int:post_id>/reply', methods=['POST'])
def add_reply(post_id):
    user = current_user_obj()
    if not user:
        return redirect(url_for('login'))

    content = request.form.get('content', '').strip()
    files = request.files.getlist('images')

    if not content and not any(f and f.filename for f in files):
        return '回复内容不能为空', 400

    image_filenames = save_uploaded_images(files)

    reply = Reply(
        content=content,
        user_id=user.id,
        post_id=post_id,
        images=','.join(image_filenames) if image_filenames else None
    )
    db.session.add(reply)
    db.session.commit()
    return redirect(url_for('post_detail', post_id=post_id))

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    results = []
    if query:
        results = Post.query.filter(
            Post.title.contains(query) | Post.content.contains(query)
        ).order_by(Post.created_at.desc()).all()
    return render_template('search.html', results=results, query=query)

# ==================== 动态相关路由 ====================

@app.route('/moments')
def moments():
    """动态已移到个人主页，重定向到自己的主页"""
    me = current_user_obj()
    if me:
        return redirect(url_for('user_profile', user_id=me.id))
    return redirect(url_for('login'))

@app.route('/moment/new', methods=['GET', 'POST'])
def new_moment():
    user = current_user_obj()
    if not user:
        return redirect(url_for('login'))

    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        files = request.files.getlist('images')
        video_file = request.files.get('video')

        if not content and not any(f and f.filename for f in files) and not (video_file and video_file.filename):
            return '动态内容不能为空', 400

        image_filenames = save_uploaded_images(files)
        video_filename = save_uploaded_video(video_file)

        moment = Moment(
            content=content,
            user_id=user.id,
            images=','.join(image_filenames) if image_filenames else None,
            video=video_filename,
        )
        db.session.add(moment)
        db.session.commit()
        notify_followers(user, 'moment', moment.id, f"{user.nickname or user.username} 发布了新动态")
        return redirect(url_for('user_profile', user_id=user.id))

    return render_template('new_moment.html')

# ==================== 用户主页 / 关注 ====================

@app.route('/user/<int:user_id>')
def user_profile(user_id):
    target = User.query.get_or_404(user_id)
    viewer = current_user_obj()
    is_self = viewer is not None and viewer.id == target.id
    is_following = False
    if viewer and not is_self:
        is_following = Follow.query.filter_by(follower_id=viewer.id, followed_id=user_id).first() is not None
    follower_count = Follow.query.filter_by(followed_id=user_id).count()
    following_count = Follow.query.filter_by(follower_id=user_id).count()
    # 隐私：只有本人或关注了 target 的人才能看到 target 的动态
    can_view_moments = is_self or is_following
    moments = []
    if can_view_moments:
        moments = Moment.query.filter_by(user_id=user_id).order_by(Moment.created_at.desc()).all()
    user_posts = Post.query.filter_by(user_id=user_id).order_by(Post.created_at.desc()).all()
    return render_template('user_profile.html',
                           target=target,
                           viewer=viewer,
                           is_self=is_self,
                           moments=moments,
                           can_view_moments=can_view_moments,
                           posts=user_posts,
                           is_following=is_following,
                           follower_count=follower_count,
                           following_count=following_count)

@app.route('/user/<int:user_id>/follow', methods=['POST'])
def follow(user_id):
    viewer = current_user_obj()
    if not viewer:
        return redirect(url_for('login'))
    target = User.query.get_or_404(user_id)
    if target.id == viewer.id:
        return '不能关注自己', 400
    if not Follow.query.filter_by(follower_id=viewer.id, followed_id=user_id).first():
        db.session.add(Follow(follower_id=viewer.id, followed_id=user_id))
        db.session.add(Notification(
            user_id=user_id,
            actor_id=viewer.id,
            type='follow',
            target_id=viewer.id,
            text=f"{viewer.nickname or viewer.username} 关注了你",
        ))
        db.session.commit()
    return redirect(url_for('user_profile', user_id=user_id))

@app.route('/user/<int:user_id>/unfollow', methods=['POST'])
def unfollow(user_id):
    viewer = current_user_obj()
    if not viewer:
        return redirect(url_for('login'))
    follow = Follow.query.filter_by(follower_id=viewer.id, followed_id=user_id).first()
    if follow:
        db.session.delete(follow)
        db.session.commit()
    return redirect(url_for('user_profile', user_id=user_id))

@app.route('/user/<int:user_id>/edit', methods=['GET', 'POST'])
def edit_profile(user_id):
    """编辑资料：昵称 + 头像（仅本人）"""
    viewer = current_user_obj()
    if not viewer or viewer.id != user_id:
        return redirect(url_for('login'))
    if request.method == 'POST':
        nickname = request.form.get('nickname', '').strip()
        avatar_file = request.files.get('avatar')
        if nickname:
            viewer.nickname = nickname
        avatar = save_avatar(avatar_file)
        if avatar:
            viewer.avatar = avatar
        db.session.commit()
        return redirect(url_for('user_profile', user_id=user_id))
    return render_template('edit_profile.html', target=viewer)

@app.route('/moment/<int:moment_id>/comment', methods=['POST'])
def add_moment_comment(moment_id):
    """给动态发评论：仅本人或关注了动态作者的人可评论"""
    viewer = current_user_obj()
    if not viewer:
        return redirect(url_for('login'))
    moment = Moment.query.get_or_404(moment_id)
    if moment.user_id != viewer.id:
        if not Follow.query.filter_by(follower_id=viewer.id, followed_id=moment.user_id).first():
            return '关注后才能评论', 403
    content = request.form.get('content', '').strip()
    if not content:
        return redirect(url_for('user_profile', user_id=moment.user_id))
    db.session.add(MomentComment(content=content, user_id=viewer.id, moment_id=moment_id))
    db.session.commit()
    return redirect(url_for('user_profile', user_id=moment.user_id))

# ==================== 通知 ====================

@app.route('/notifications')
def notifications():
    user = current_user_obj()
    if not user:
        return redirect(url_for('login'))
    items = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).all()
    for n in items:
        n.is_read = True
    db.session.commit()
    return render_template('notifications.html', items=items)

if __name__ == '__main__':
    # 生产环境请用 gunicorn/waitress 等；这里默认只监听本机、关闭 debug
    app.run(
        host=os.environ.get('HOST', '127.0.0.1'),
        port=int(os.environ.get('PORT', '5000')),
        debug=os.environ.get('FLASK_DEBUG', '0') == '1',
    )
