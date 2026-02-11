from datetime import datetime
from database import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    
    # 성장 스탯
    level = db.Column(db.Integer, default=1)
    exp = db.Column(db.Integer, default=0)
    popcorn = db.Column(db.Integer, default=0)
    
    # 상태
    main_flavor = db.Column(db.String(50), default="Sweet")
    stage = db.Column(db.String(20), default="Egg")
    
    # 시간 기록
    last_feeding_date = db.Column(db.String(20), nullable=True) # YYYY-MM-DD
    last_question_date = db.Column(db.String(20), nullable=True) # YYYY-MM-DD
    current_question_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 관계 설정
    flavor_stats = db.relationship('FlavorStat', backref='user', lazy=True)
    inventory = db.relationship('ThemeInventory', backref='user', lazy=True)
    history = db.relationship('QuestionHistory', backref='user', lazy=True)

class FlavorStat(db.Model):
    __tablename__ = 'flavor_stats'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    flavor_name = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer, default=0)

    # 유니크 제약조건: 한 유저는 같은 flavor를 중복해서 가질 수 없음
    __table_args__ = (db.UniqueConstraint('user_id', 'flavor_name', name='_user_flavor_uc'),)

class ThemeInventory(db.Model):
    __tablename__ = 'theme_inventory'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    theme_id = db.Column(db.String(50), nullable=False) # e.g., 'dark', 'pink'
    is_applied = db.Column(db.Boolean, default=False)
    acquired_at = db.Column(db.DateTime, default=datetime.utcnow)

class QuestionHistory(db.Model):
    __tablename__ = 'question_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    date = db.Column(db.String(20), nullable=False) # YYYY-MM-DD
    question = db.Column(db.String(200), nullable=False)
    answer = db.Column(db.Text, nullable=False)
