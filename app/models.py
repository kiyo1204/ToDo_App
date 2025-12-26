from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    deadline = db.Column(db.DateTime, nullable=False)
    is_shared = db.Column(db.Boolean, nullable=False, default=False)
    my_favorite = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=False)
    email=db.Column(db.String(255),nullable=True)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.String(255), primary_key=True)
    password_hash = db.Column(db.String(162), nullable=False)
    lastname = db.Column(db.String(255), nullable=False)
    firstname = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    tasks = db.relationship("Task", backref="user", lazy=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    timing_hours=db.Column(db.Integer,nullable=False,default=0)
    timing_minutes=db.Column(db.Integer,nullable=False,default=30)

    @property
    def password(self):
        raise AttributeError("パスワードは読めません")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
