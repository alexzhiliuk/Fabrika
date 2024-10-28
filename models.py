from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import enum

db = SQLAlchemy()


class UserRole(enum.Enum):
    CONSULTANT = "consultant"
    ADMIN = "admin"


class Brand(db.Model):
    __tablename__ = 'brands'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(255), nullable=True)  # Ссылка на изображение

    def __repr__(self):
        return f'<Brand {self.name}>'


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    first_name = db.Column(db.String(80), nullable=True)
    last_name = db.Column(db.String(80), nullable=True)
    password_hash = db.Column(db.String(128), nullable=False)
    password = db.Column(db.String(128), nullable=True)

    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.CONSULTANT)

    # Поле для связи с брендом
    brand_id = db.Column(db.Integer, db.ForeignKey('brands.id'), nullable=True)
    brand = db.relationship('Brand', backref='users')

    def set_password(self, password):
        """Создание хеша пароля"""
        print(self.role, self.role == UserRole.CONSULTANT)
        if self.role == UserRole.CONSULTANT:
            self.password = password

        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Проверка введённого пароля"""
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == UserRole.ADMIN

    @property
    def fio(self):
        return f"{self.first_name or ''} {self.last_name or ''}"

    def __repr__(self):
        return f'<User {self.username}>'


class FittingRoom(db.Model):
    __tablename__ = 'fitting_rooms'
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False, unique=True)

    def __repr__(self):
        return f'<FittingRoom {self.number}>'


class Consultation(db.Model):
    __tablename__ = 'consultations'

    id = db.Column(db.Integer, primary_key=True)
    fitting_room_id = db.Column(db.Integer, db.ForeignKey('fitting_rooms.id'), nullable=False)
    fitting_room = db.relationship('FittingRoom', backref='сonsultations')
    brand_id = db.Column(db.Integer, db.ForeignKey('brands.id'), nullable=False)
    brand = db.relationship('Brand', backref='сonsultations')

    closed = db.Column(db.Boolean, default=False)

