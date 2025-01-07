from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, MultipleFileField, SubmitField
from wtforms.validators import DataRequired

class IncidentForm(FlaskForm):
    """
    Форма для создания инцидента.
    """
    title = StringField('Название', validators=[DataRequired()])
    description = TextAreaField('Описание', validators=[DataRequired()])
    screenshots = MultipleFileField('Скриншоты')  # Поле для загрузки нескольких файлов
    submit = SubmitField('Создать инцидент')
