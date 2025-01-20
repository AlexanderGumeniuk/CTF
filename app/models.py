from app import db, login_manager
from flask_login import UserMixin
from sqlalchemy.dialects.postgresql import JSON
from werkzeug.security import generate_password_hash, check_password_hash

import os
import uuid
team_competition = db.Table(
    'team_competition',
    db.Column('team_id', db.Integer, db.ForeignKey('team.id'), primary_key=True),
    db.Column('competition_id', db.Integer, db.ForeignKey('competition.id'), primary_key=True)
)

class UserChallenge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
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
    competition_id = db.Column(db.Integer, db.ForeignKey('competition.id'), nullable=True)
    max_attempts = db.Column(db.Integer, default=3)  # Максимальное число попыток (по умолчанию 3)

    user_challenges = db.relationship('UserChallenge', backref='challenge', cascade='all, delete-orphan')
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


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    total_points = db.Column(db.Integer, default=0)
    avatar = db.Column(db.String(255), nullable=True)  # Поле для хранения пути к аватару

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

    # Метод для генерации уникального имени файла аватара
    @staticmethod
    def generate_avatar_filename(filename):
        ext = os.path.splitext(filename)[1]  # Получаем расширение файла
        unique_name = f"{uuid.uuid4().hex}{ext}"  # Генерируем уникальное имя
        return unique_name

    # Метод для обновления аватара
    def update_avatar(self, file):
        if file:
            # Генерируем уникальное имя файла
            filename = self.generate_avatar_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)  # Сохраняем файл на сервере
            self.avatar = filename  # Сохраняем имя файла в базе данных
            db.session.commit()


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    users = db.relationship('User', back_populates='team', lazy=True)  # Связь с пользователями
    competition_id = db.Column(db.Integer, db.ForeignKey('competition.id'), nullable=True)

    competitions = db.relationship(
        'Competition',
        secondary=team_competition,
        back_populates='teams'
    )

    def __repr__(self):
        return f"Team('{self.name}')"

class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, needs_revision
    points_awarded = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id', ondelete='CASCADE'), nullable=True)
    competition_id = db.Column(db.Integer, db.ForeignKey('competition.id'), nullable=True)
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
    event_id = db.Column(db.Integer, db.ForeignKey('critical_event.id' , ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id', ondelete='CASCADE'), nullable=True)
    response = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # Статус отчета
    points_awarded = db.Column(db.Integer, default=0)
    competition_id = db.Column(db.Integer, db.ForeignKey('competition.id'), nullable=True)
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
    responses = db.relationship('CriticalEventResponse', backref='event', cascade='all, delete-orphan')
    steps = db.relationship('CriticalEventStep', backref='response', cascade='all, delete-orphan')  # Связь с шагами
    # Добавляем связь с пользователем
    created_by_user = db.relationship('User', backref='created_events', foreign_keys=[created_by])
    competition_id = db.Column(db.Integer, db.ForeignKey('competition.id'), nullable=True)
    def __repr__(self):
        return f"CriticalEvent('{self.title}', Created by {self.created_by})"


class CriticalEventStep(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('critical_event.id', ondelete='CASCADE'), nullable=False)
    response_id = db.Column(db.Integer, db.ForeignKey('critical_event_response.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    step_name = db.Column(db.String(100), nullable=False)  # Название шага
    description = db.Column(db.Text, nullable=True)  # Описание шага

    # Поля, аналогичные модели Incident
    start_time = db.Column(db.DateTime, nullable=False)  # Время начала
    end_time = db.Column(db.DateTime, nullable=False)  # Время окончания
    source_ip = db.Column(db.String(50), nullable=False)  # Исходный IP
    source_port = db.Column(db.Integer, nullable=True)  # Исходный порт
    destination_ip = db.Column(db.String(50), nullable=False)  # Целевой IP
    destination_port = db.Column(db.Integer, nullable=True)  # Целевой порт
    event_type = db.Column(db.String(50), nullable=False)  # Тип события
    related_fqdn = db.Column(db.Text, nullable=True)  # Связанный FQDN
    related_dns = db.Column(db.Text, nullable=True)  # Связанный DNS
    ioc = db.Column(db.Text, nullable=True)  # Индикаторы компрометации (IOC)
    hash_value = db.Column(db.Text, nullable=True)  # Хэш-значение
    mitre_id = db.Column(db.String(50), nullable=True)  # MITRE ID
    siem_id = db.Column(db.String(50), nullable=True)  # SIEM ID
    siem_link = db.Column(db.Text, nullable=True)  # Ссылка на SIEM
    screenshots = db.Column(JSON, nullable=True)  # Скриншоты (для PostgreSQL)

    # Дополнительные поля для шагов
    responsible = db.Column(db.String(100), nullable=True)  # Ответственный
    deadline = db.Column(db.DateTime, nullable=True)  # Срок выполнения
    status = db.Column(db.String(50), nullable=True)  # Статус шага
    comments = db.Column(db.Text, nullable=True)  # Комментарии

    def __repr__(self):
        return f"CriticalEventStep('{self.step_name}', Event {self.event_id}, Team {self.team_id})"




class Infrastructure(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    topology = db.Column(JSON, nullable=True)  # Топология (узлы)
    links = db.Column(JSON, nullable=True)  # Связи между узлами
    elements = db.Column(JSON, nullable=True)  # Прямоугольники и надписи
    organization_description = db.Column(db.Text, nullable=False)
    files = db.Column(JSON, nullable=True)
    competition_id = db.Column(db.Integer, db.ForeignKey('competition.id'), nullable=True)
    competition = db.relationship('Competition', backref='infrastructures')
    def __repr__(self):
        return f"Infrastructure('{self.title}')"


from datetime import datetime
from app import db

class PointsHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Уникальный идентификатор записи
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    points = db.Column(db.Integer, nullable=False)  # Количество начисленных баллов
    note = db.Column(db.Text, nullable=True)  # Примечание (например, за что начислены баллы)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Дата и время начисления баллов

    # Связь с пользователем
    user = db.relationship('User', backref='points_history')

    def __repr__(self):
        return f"PointsHistory(User {self.user_id}, Points {self.points}, Note: {self.note})"


from datetime import datetime
from app import db

class Competition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)  # Название соревнования
    description = db.Column(db.Text, nullable=True)    # Описание соревнования
    start_date = db.Column(db.DateTime, nullable=False)  # Дата начала
    end_date = db.Column(db.DateTime, nullable=False)    # Дата окончания
    status = db.Column(db.String(20), default='planned')  # Статус: planned, active, finished
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Дата создания

    teams = db.relationship(
        'Team',
        secondary=team_competition,
        back_populates='competitions'
    )

    # Связи с другими моделями
    challenges = db.relationship('Challenge', backref='competition', lazy=True)  # Список флагов (задач)
    incidents = db.relationship('Incident', backref='competition', lazy=True)    # Список инцидентов
    critical_events = db.relationship('CriticalEvent', backref='competition', lazy=True)  # Список КС

    def __repr__(self):
        return f"Competition('{self.title}', Status: '{self.status}')"
# Ассоциативная таблица для связи Team и Competition
class FlagResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Уникальный идентификатор ответа
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Связь с пользователем
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)  # Связь с командой (если есть)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenge.id'), nullable=False)  # Связь с задачей (флагом)
    response = db.Column(db.String(255), nullable=False)  # Содержание ответа (введенный флаг)
    flag = db.Column(db.String(255), nullable=False)  # Ожидаемый флаг
    is_correct = db.Column(db.Boolean, default=False)  # Правильный ли ответ
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # Время отправки ответа

    # Связи с другими моделями
    user = db.relationship('User', backref='flag_responses')  # Связь с пользователем
    team = db.relationship('Team', backref='flag_responses')  # Связь с командой
    challenge = db.relationship('Challenge', backref='flag_responses')  # Связь с задачей

    def __repr__(self):
        return f"FlagResponse(User {self.user_id}, Challenge {self.challenge_id}, Correct: {self.is_correct})"
