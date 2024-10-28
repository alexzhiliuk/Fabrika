import os
from functools import wraps

from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit
from flask_migrate import Migrate
from config import Config
from models import db, User, UserRole, Brand, FittingRoom, Consultation

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

socketio = SocketIO(app)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
            flash("Отказано в доступе: Только для администратора.", "error")
            return redirect(url_for("index"))
        return f(*args, **kwargs)

    return decorated_function


def allowed_file(filename):
    """Проверка на допустимые расширения файла"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@login_manager.user_loader
def load_user(user_id):
    """Функция загрузки пользователя по ID для Flask-Login"""
    return User.query.get(int(user_id))


@app.route('/')
@login_required
def index():
    user = current_user
    if user.is_admin():
        fitting_rooms = FittingRoom.query.all()
        brands = Brand.query.all()
        consultants = User.query.filter_by(role=UserRole.CONSULTANT).all()
        return render_template('admin.html', fitting_rooms=fitting_rooms, brands=brands, consultants=consultants)

    consultations = Consultation.query.filter_by(closed=False).all()
    return render_template('index.html', consultations=consultations, consultant=user)


@app.route('/add_user/')
def add_user():
    return render_template('add_user.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует')
            return redirect(url_for('register'))

        new_user = User(username=username, role=UserRole.CONSULTANT)
        new_user.set_password(password)  # Устанавливаем хеш пароля

        db.session.add(new_user)
        db.session.commit()

        flash('Регистрация прошла успешно!')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash('Неверное имя пользователя или пароль', 'error')
            return redirect(url_for('login'))

        login_user(user)  # Вход пользователя через Flask-Login
        return redirect(url_for('index'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы')
    return redirect(url_for('login'))


@app.route('/brand/add/', methods=['GET', 'POST'])
@admin_required
def add_brand():
    if request.method == 'POST':
        brand_name = request.form['name']
        file = request.files['image']

        # Проверка на наличие бренда с таким же именем
        if Brand.query.filter_by(name=brand_name).first():
            flash('Бренд с таким названием уже существует', "error")
            return redirect(url_for('add_brand'))

        # Проверка файла
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Сохранение файла в папку static/uploads
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Добавление нового бренда в базу данных
            new_brand = Brand(name=brand_name, image=filename)
            db.session.add(new_brand)
            db.session.commit()

            flash('Бренд успешно добавлен!')
            return redirect(url_for('index'))
        else:
            flash('Неверный формат файла. Допустимые форматы: png, jpg.', "error")
            return redirect(url_for('add_brand'))

    return render_template('add_brand.html')


@app.route('/brand/edit/<int:brand_id>/', methods=['GET', 'POST'])
@admin_required
def edit_brand(brand_id):
    brand = Brand.query.get_or_404(brand_id)

    if request.method == 'POST':
        brand_name = request.form.get('name')
        file = request.files.get('image')

        # Проверка на наличие бренда с таким же именем
        if brand.name != brand_name and Brand.query.filter_by(name=brand_name).first():
            flash('Бренд с таким названием уже существует', "error")
            return redirect(url_for('edit_brand', brand_id=brand.id))

        brand.name = brand_name

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Сохранение файла в папку static/uploads
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            brand.image = filename

        db.session.commit()
        flash(f"Бренд {brand.name} успешно изменен")
        return redirect(url_for('index'))

    return render_template('edit_brand.html', brand=brand)


@app.route('/brand/delete/<int:brand_id>/', methods=['DELETE'])
@admin_required
def delete_brand(brand_id):
    brand = Brand.query.get_or_404(brand_id)

    db.session.delete(brand)
    db.session.commit()

    return jsonify({"message": "Бренд удален"}), 200


@app.route('/consultant/add/', methods=['GET', 'POST'])
@admin_required
def add_consultant():
    if request.method == 'POST':
        username = request.form['username']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        brand_name = request.form['brand']
        password = request.form['password']

        # Проверка на наличие бренда с таким же именем
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким юзернеймом уже существует', "error")
            return redirect(url_for('add_consultant'))

        brand = Brand.query.filter_by(name=brand_name).first()

        new_consultant = User(username=username, first_name=first_name, last_name=last_name, role=UserRole.CONSULTANT,
                              brand=brand)
        new_consultant.set_password(password)

        db.session.add(new_consultant)
        db.session.commit()

        flash('Консультант успешно добавлен!')
        return redirect(url_for('index'))

    brands = Brand.query.all()
    return render_template('add_consultant.html', brands=brands)


@app.route('/consultant/edit/<int:consultant_id>/', methods=['GET', 'POST'])
@admin_required
def edit_consultant(consultant_id):
    consultant = User.query.get_or_404(consultant_id)
    brands = Brand.query.all()

    if request.method == 'POST':
        username = request.form['username']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        brand_name = request.form['brand']
        password = request.form['password']

        if consultant.username != username and User.query.filter_by(username=username).first():
            flash('Консультант с таким юзернеймом уже существует', "error")
            return redirect(url_for('edit_consultant', consultant_id=consultant.id))

        brand = Brand.query.filter_by(name=brand_name).first()

        consultant.username = username
        consultant.first_name = first_name
        consultant.last_name = last_name
        consultant.brand = brand
        consultant.password = password

        db.session.commit()
        flash(f"Консультант {consultant.username} успешно изменен")
        return redirect(url_for('index'))

    return render_template('edit_consultant.html', consultant=consultant, brands=brands)


@app.route('/consultant/delete/<int:consultant_id>/', methods=['DELETE'])
@admin_required
def delete_consultant(consultant_id):
    consultant = User.query.get_or_404(consultant_id)

    db.session.delete(consultant)
    db.session.commit()

    return jsonify({"message": "Консультант удален"}), 200


@app.route('/fitting_room/add/', methods=['GET', 'POST'])
@admin_required
def add_fitting_room():
    if request.method == 'POST':
        number = request.form['number']

        if FittingRoom.query.filter_by(number=number).first():
            flash('Примерочная с таким номером уже существует', "error")
            return redirect(url_for('add_fitting_room'))

        new_fitting_room = FittingRoom(number=number)
        db.session.add(new_fitting_room)
        db.session.commit()

        flash('Примерочная успешно добавлена!')
        return redirect(url_for('index'))

    return render_template('add_fitting_room.html')


@app.route('/fitting_room/edit/<int:fitting_room_id>/', methods=['GET', 'POST'])
@admin_required
def edit_fitting_room(fitting_room_id):
    fitting_room = FittingRoom.query.get_or_404(fitting_room_id)

    if request.method == 'POST':
        number = request.form['number']

        if fitting_room.number != number and FittingRoom.query.filter_by(number=number).first():
            flash('Примерочная с таким номером уже существует', "error")
            return redirect(url_for('edit_fitting_room', fitting_room_id=fitting_room.id))

        fitting_room.number = number

        db.session.commit()
        flash(f"Примерочная {fitting_room.number} успешно изменена")
        return redirect(url_for('index'))

    return render_template('edit_fitting_room.html', fitting_room=fitting_room)


@app.route('/fitting_room/delete/<int:fitting_room_id>/', methods=['DELETE'])
@admin_required
def delete_fitting_room(fitting_room_id):
    fitting_room = FittingRoom.query.get_or_404(fitting_room_id)

    db.session.delete(fitting_room)
    db.session.commit()

    return jsonify({"message": "Примерочная удалена"}), 200


@app.route('/fitting_room/<int:room_id>/')
@admin_required
def fitting_room_show(room_id):
    fitting_room = FittingRoom.query.get_or_404(room_id)
    brands = Brand.query.all()
    return render_template('fitting_room.html', brands=brands, fitting_room=fitting_room)


@socketio.on('connect')
def handle_connect():
    print('Client connected')


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


@socketio.on('add_consultation')
def handle_add_consultation(data):
    new_consultation = Consultation(fitting_room_id=data['roomId'], brand_id=data['brandId'])
    db.session.add(new_consultation)
    db.session.commit()

    emit('update_consultations',
         {'roomId': new_consultation.fitting_room_id, "id": new_consultation.id},
         broadcast=True)


@socketio.on('close_consultation')
def handle_close_consultation(data):
    consultation = Consultation.query.filter_by(id=data['consultationId']).first()
    consultation.closed = True
    fitting_room_id = consultation.fitting_room_id
    db.session.delete(consultation)
    db.session.commit()

    if not consultation:
        return

    emit('fitting_room_notification', {'roomId': fitting_room_id}, broadcast=True)


@socketio.on('cancel_consultation')
def handle_cancel_consultation(data):
    consultation = Consultation.query.filter_by(id=data['consultationId']).first()
    consultation.closed = True
    db.session.delete(consultation)
    db.session.commit()

    if not consultation:
        return

    emit('cancel_consultation', {'id': data['consultationId']}, broadcast=True)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    socketio.run(app, debug=True)
