from flask_sqlalchemy import SQLAlchemy

# SQLAlchemy 인스턴스 생성
db = SQLAlchemy()

def init_db(app):
    """
    Flask 애플리케이션에 DB를 초기화하고 테이블을 생성합니다.
    """
    db.init_app(app)
    with app.app_context():
        db.create_all()
