from app import db, login_manager
from flask_login import UserMixin
from sqlalchemy.dialects.postgresql import JSON

class UserChallenge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenge.id'), nullable=False)
    solved = db.Column(db.Boolean, default=False)
    used_hint = db.Column(db.Boolean, default=False)  # Новое поле: использована ли подсказка
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    points_awarded = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"UserChallenge(User {self.user_id}, Challenge {self.challenge_id}, Solved {self.solved})"

class Challenge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    flag = db.Column(db.String(100), nullable=False)
    points = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    hint = db.Column(db.Text, nullable=True)  # Новое поле: подсказка
    hint_penalty = db.Column(db.Integer, default=10)  # Штраф за использование подсказки (например, 10% от points)

    def solved_by_user(self, user):
        # Проверяем, решил ли пользователь задачу
        return UserChallenge.query.filter_by(
            user_id=user.id,
            challenge_id=self.id,
            solved=True
        ).first() is not None

    def __repr__(self):
        return f"Challenge('{self.title}', '{self.category}', {self.points} points)"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    total_points = db.Column(db.Integer, default=0)

    # Связь с командой (без backref, так как он уже определен в Team)
    team = db.relationship('Team', foreign_keys=[team_id])

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

    # Метод для установки пароля
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Метод для проверки пароля
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    users = db.relationship('User', back_populates='team', lazy=True)  # Связь с пользователями

    def __repr__(self):
        return f"Team('{self.name}')"

class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, needs_revision
    points_awarded = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)

    # Новые поля
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    source_ip = db.Column(db.String(50), nullable=False)
    source_port = db.Column(db.Integer, nullable=True)
    destination_ip = db.Column(db.String(50), nullable=False)
    destination_port = db.Column(db.Integer, nullable=True)
    event_type = db.Column(db.String(50), nullable=False)
    related_fqdn = db.Column(db.Text, nullable=True)
    related_dns = db.Column(db.Text, nullable=True)
    ioc = db.Column(db.Text, nullable=True)
    hash_value = db.Column(db.Text, nullable=True)
    mitre_id = db.Column(db.String(50), nullable=True)
    siem_id = db.Column(db.String(50), nullable=True)
    siem_link = db.Column(db.Text, nullable=True)
    screenshots = db.Column(JSON, nullable=True)  # Для PostgreSQL

    # Отношения
    team = db.relationship('Team', foreign_keys=[team_id])
    user = db.relationship('User', foreign_keys=[user_id], backref='created_incidents')
    admin = db.relationship('User', foreign_keys=[admin_id], backref='reviewed_incidents')

    def __repr__(self):
        return f"Incident('{self.title}', Status: '{self.status}')"
class CriticalEventResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('critical_event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)  # Связь с командой
    response = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # Статус отчета
    points_awarded = db.Column(db.Integer, default=0)

    # Связь с командой
    team = db.relationship('Team', foreign_keys=[team_id])
    user = db.relationship('User', backref='critical_event_responses', foreign_keys=[user_id])

    def __repr__(self):
        return f"CriticalEventResponse(Event {self.event_id}, User {self.user_id}, Status {self.status})"


class CriticalEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    responses = db.relationship('CriticalEventResponse', backref='event', lazy=True)
    steps = db.relationship('CriticalEventStep', backref='event', lazy=True)  # Связь с шагами
    # Добавляем связь с пользователем
    created_by_user = db.relationship('User', backref='created_events', foreign_keys=[created_by])

    def __repr__(self):
        return f"CriticalEvent('{self.title}', Created by {self.created_by})"


class CriticalEventStep(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('critical_event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Обязательное поле
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)  # Связь с командой
    step_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    responsible = db.Column(db.String(100), nullable=True)
    deadline = db.Column(db.DateTime, nullable=True)
    resources = db.Column(db.Text, nullable=True)
    risks = db.Column(db.Text, nullable=True)
    actions = db.Column(db.Text, nullable=True)
    results = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=True)
    comments = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"CriticalEventStep('{self.step_name}', Event {self.event_id}, Team {self.team_id})"
