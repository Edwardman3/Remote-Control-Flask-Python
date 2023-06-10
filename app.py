from flask import Flask, render_template, jsonify, request, flash, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_login import UserMixin, current_user, login_user, login_required, logout_user, LoginManager
from werkzeug.security import generate_password_hash, check_password_hash
import threading
from turbo_flask import Turbo
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-goes-here'
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql://root:kom20102021#@localhost/pwr_remote_access"
app.config["SQLALCHEMY_POOL_RECYCLE"] = 299
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

turbo = Turbo(app)
db = SQLAlchemy()
ma = Marshmallow()
db.init_app(app)

ACCESS_LEVEL = 0
CURRENT_DEVICE = None
TEST_VALUE = 10

class Users(UserMixin, db.Model):
    __table_name__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    access_level = db.Column(db.Integer)

    def __init__(self, email, password, name, access_level):
        self.email = email
        self.password = password
        self.name = name
        self.access_level = access_level


class Devices(db.Model):
    __table_name__ = "devices"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    location = db.Column(db.String(100))
    power_on = db.Column(db.Integer)
    is_power_on = db.Column(db.Integer)
    value = db.Column(db.Integer)
    safety_level = db.Column(db.Integer)

    def __init__(self, name, location, power_on, is_power_on, value, safety_level):
        self.name = name
        self.location = location
        self.power_on = power_on
        self.is_power_on = is_power_on
        self.value = value
        self.safety_level = safety_level


class DevicesSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'location', 'power_on', 'is_power_on', 'value', 'safety_level')


class DevicesBasicSchema(ma.Schema):
    class Meta:
        # fields = ('is_power_on', 'power_on', 'value')
        fields = ('power_on', 'value')


class UsersSchema(ma.Schema):
    class Meta:
        fields = ('id', 'email', 'password', 'name', 'access_level')


login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


def devices_to_print():
    devices_list = Devices.query.filter(Devices.safety_level <= ACCESS_LEVEL)
    return devices_list


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))


device_basic_schema = DevicesBasicSchema()
devices_basic_schema = DevicesBasicSchema(many=True)
device_schema = DevicesSchema()
devices_schema = DevicesSchema(many=True)
user_schema = UsersSchema()
users_schema = UsersSchema(many=True)


def devices():
    devices_list = Devices.query.filter(Devices.safety_level <= current_user.access_level)
    result = devices_schema.dump(devices_list)
    return jsonify(result)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/signup')
def signup():
    return render_template('signup.html')


@app.route('/signup', methods=['POST'])
def signup_post():
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')

    user = Users.query.filter_by(email=email).first()

    if user:
        flash('Email address already exists')
        return redirect(url_for('signup'))

    new_user = Users(email=email, name=name, password=generate_password_hash(password, method='sha256'), access_level=0)
    db.session.add(new_user)
    db.session.commit()

    return redirect((url_for('login')))


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    active_user = Users.query.filter_by(email=email).first()

    if not active_user or not check_password_hash(active_user.password, password):
        flash('Please check your login details and try again.')
        return redirect(url_for('login'))
    login_user(active_user, remember=remember)
    global ACCESS_LEVEL
    ACCESS_LEVEL = current_user.access_level
    return redirect(url_for('profile'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', item_list=devices_to_print())


@app.route("/kompresor/<id>", methods=["GET"])
def get_kompresor(id):
    kompresor = Devices.query.filter_by(id=id)
    result = devices_basic_schema.dump(kompresor)
    return jsonify(result)


@app.route("/kompresor/<id>", methods=["PUT"])  ###link do ustalenia, ale taki jest w arduino
def update_kompresor(id):
    kompresor = Devices.query.get(id)
    kompresor.power_on = request.json.get('power_on', kompresor.power_on)
    kompresor.location = request.json.get('location', kompresor.location)
    kompresor.name = request.json.get('name', kompresor.name)
    kompresor.is_power_on = request.json.get('is_power_on', kompresor.is_power_on)
    kompresor.safety_level = request.json.get('safety_level', kompresor.safety_level)
    kompresor.value = request.json.get('value', kompresor.value)
    db.session.commit()
    return device_basic_schema.jsonify(device_basic_schema.dump(kompresor))


@app.route("/device")
def device():
    return render_template('device.html')


@app.route("/change_mode/<id>")
@login_required
def change_mode(id):
    print(id)
    db.session.commit()
    now_device = Devices.query.get(id)
    if now_device.is_power_on == 1:
        now_device.power_on = 0
        db.session.commit()
        now_device.value = 0
        db.session.commit()
    else:
        now_device.power_on = 1
    db.session.commit()
    return redirect(url_for('device'))


@app.route("/change_value/<id>/<value>")
@login_required
def change_value(id, value):
    db.session.commit()
    now_device = Devices.query.get(id)
    now_device.value = value
    db.session.commit()
    return redirect(url_for('device'))


@app.route("/panel_mode/<id>")
@login_required
def panel_mode(id):
    global CURRENT_DEVICE
    CURRENT_DEVICE = id
    db.session.commit()
    return redirect(url_for('device'))


@app.context_processor
def get_chosen_device():
    global CURRENT_DEVICE
    if CURRENT_DEVICE is not None:
        db.session.commit()
        actual_device = db.session.get(Devices, CURRENT_DEVICE)
        return {'id': actual_device.id, 'name': actual_device.name, 'location': actual_device.location,
                'power_on': actual_device.power_on,
                'is_power_on': actual_device.is_power_on, 'value':  actual_device.value}
    else:
        return {'id': 0, 'name': "<test>", 'location': "<test>", 'power_on': "<test>",
                'is_power_on': "<test>", 'value':  0}


@app.before_first_request
def before_first_request():
    threading.Thread(target=update_load).start()


def update_load():
    with app.app_context():
        while True:
            time.sleep(1)
            turbo.push(turbo.replace(render_template('test.html'), 'load'))


app.run(debug=True, host='0.0.0.0', port=5000)
