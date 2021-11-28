import psycopg2
from werkzeug import exceptions
from flask.helpers import send_from_directory
from flask import Flask, request
from flask_cors import CORS, cross_origin
import hashlib
import json
import datetime


class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            host="ec2-52-208-145-55.eu-west-1.compute.amazonaws.com",
            database="d1ol7h4m4fa12e",
            user="tauerfmxyhknkp",
            password="b889ddcdadd24f94e7e0f3aceecd92da372334e5663bb7795598250fb860634b",
            sslmode='require')
        self.cur = self.conn.cursor()

    def send_request(self, sql, read=True):
        ret = None
        try:
            self.cur.execute(sql)
        except (Exception, psycopg2.DatabaseError) as error:
            ret = error
        except psycopg2.ProgrammingError:
            ret = f"Wrong SQL request: {sql}"
        except psycopg2.OperationalError:
            ret = "Cannot connect to database."
        else:
            if read:
                try:
                    ret = (True, self.cur.fetchall())
                except psycopg2.ProgrammingError:
                    ret = False
            else:
                ret = True
        finally:
            if not read:
                self.conn.commit()
            return ret


app = Flask(__name__, static_folder='build', static_url_path='')
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
data = Database()


@app.route('/loginUser', methods=['GET', 'POST'])
@cross_origin()
def login_user():
    if request.method == 'GET' or request.method == 'POST':
        username = request.args.get('username') if request.method == 'GET' else request.json['username']
        password = request.args.get('password') if request.method == 'GET' else request.json['password']
    else:
        username = password = None
    if None in (username, password):
        ret = {"result": "Failure"}
        return json.dumps(ret)
    database_data = data.send_request(f'''SELECT password,id from public."User" where username = '{username}' ''', True)
    if database_data[0]:
        data_pass = database_data[1][0][0]
        data_id = database_data[1][0][1]
        passwd_hash = (hashlib.md5(password.encode())).hexdigest()
        if data_pass == passwd_hash:
            ret = {"result": "Success", "id": data_id}
        else:
            ret = {"result": "Failure"}
    else:
        ret = {"result": "Failure"}
    return json.dumps(ret)


@app.route('/addUser', methods=['GET', 'POST'])
@cross_origin()
def register():
    if request.method == 'GET' or request.method == 'POST':
        username = request.args.get('username') if request.method == 'GET' else request.json['username']
        password = request.args.get('password') if request.method == 'GET' else request.json['password']
        name = request.args.get('name') if request.method == 'GET' else request.json['name']
        surname = request.args.get('surname') if request.method == 'GET' else request.json['surname']
        gender = request.args.get('gender') if request.method == 'GET' else request.json['gender']
    else:
        username = password = name = surname = gender = None
    if None in (username, password, name, surname, gender):
        ret = {"result": "Failure"}
        return json.dumps(ret)
    user_id = (data.send_request('''SELECT MAX(id) FROM public."User"''', True)[1][0][0]) + 1
    passwd_hash = (hashlib.md5(password.encode())).hexdigest()
    if data.send_request(f'''INSERT INTO public."User"(id, username, name, surname, gender, password)  VALUES
                     ('{user_id}', '{username}', '{name}', '{surname}', '{gender}', '{passwd_hash}' )''', False):
        ret = {"result": "Success", "id": user_id}
        return ret


@app.route('/addConference', methods=['GET', 'POST'])
@cross_origin()
def create_conference():
    if request.method == 'GET' or request.method == 'POST':
        organizer = request.args.get('organizer') if request.method == 'GET' else request.json['organizer']
        description = request.args.get('description') if request.method == 'GET' else request.json['description']
        genre = request.args.get('genre') if request.method == 'GET' else request.json['genre']
        address = request.args.get('address') if request.method == 'GET' else request.json['address']
        rooms = request.args.get('rooms') if request.method == 'GET' else request.json['rooms']
        capacity = request.args.get('capacity') if request.method == 'GET' else request.json['capacity']
        timeTo = request.args.get('timeTo') if request.method == 'GET' else request.json['timeTo']
        timeFrom = request.args.get('timeFrom') if request.method == 'GET' else request.json['timeFrom']
    else:
        organizer = description = genre = address = rooms = capacity = timeTo = timeFrom = None
    if None in (organizer, description, genre, address, rooms, capacity, timeTo, timeFrom):
        ret = {"result": "Failure"}
        return json.dumps(ret)
    conference_id = (data.send_request('''SELECT MAX(id) FROM public."Conference"''')[1][0][0]) + 1
    if data.send_request(f'''INSERT INTO public."Conference"(id, capacity, description, address, genre, organizer,
    rooms, begin_time, end_time) VALUES ('{conference_id}','{capacity}','{description}','{address}','{genre}',
    '{organizer}','{rooms}','{timeFrom}','{timeTo}') ''', False):
        ret = {"result": "Success", "id": conference_id}
        return ret


def parse_profile_data(temp_data, fields):
    user_data = {}
    if len(temp_data) > 5:
        temp_data = temp_data[:5]
    for n, i in enumerate(temp_data, 1):
        user_data[n] = []
        for j, k in zip(i, fields):
            if type(j) == datetime.time:
                j = datetime.time.strftime(j, "%H:%M")
            user_data[n].append(f'{k}: {j}')
    return user_data


@app.route('/profile', methods=['GET', 'POST'])
@cross_origin()
def profile():
    if request.method == 'GET' or request.method == 'POST':
        user_id = request.args.get('id') if request.method == 'GET' else request.json['id']
    else:
        user_id = None
    if user_id is None:
        ret = {"result": "Failure", "reason": "No user_id provided"}
        return json.dumps(ret)
    user_id = int(user_id)
    ticket_fields = ['id', 'price', 'conference', 'status']
    database_data = data.send_request(
        f'''SELECT T.id, price, description, status FROM public."Ticket" T natural join "Conference" C where T.conference = C.id and T."user" = {user_id} ORDER BY id DESC ''')
    if database_data[0]:
        user_tickets = parse_profile_data(database_data[1],ticket_fields)
    else:
        ret = {"result": "Failure", "reason": "Cannot get tickets"}
        return json.dumps(ret)
    conference_fields = ['id', 'capacity', 'description', 'address', 'participants', 'begin_time', 'end_time']
    database_data = data.send_request(
        f'''SELECT id,capacity,description,address,participants,begin_time,end_time FROM public."Conference" WHERE organizer = {user_id} ORDER BY id DESC ''')
    if database_data[0]:
        user_conferencies = parse_profile_data(database_data[1], conference_fields)
    else:
        ret = {"result": "Failure", "reason": "Cannot get conferencies"}
        return json.dumps(ret)
    prezentations_fields = ['id', 'name', 'conference_name', 'room_name', 'begin_time', 'end_time', 'confirmed']
    database_data = data.send_request(f'''
            SELECT P.id,P.name,C.description,R.name,P.begin_time,P.end_time,P.confirmed FROM public."Presentation" P, 
            "Conference" C, "Room" R where conference=C.id and room=R.id and lecturer={user_id} ORDER BY id DESC ''')
    if database_data[0]:
        user_prezentations = parse_profile_data(database_data[1], prezentations_fields)
    else:
        ret = {"result": "Failure", "reason": "Cannot get presentations"}
        return json.dumps(ret)
    ret = {"result": "Success", "tickets": user_tickets, "conferencies": user_conferencies,
           "prezentations": user_prezentations}
    return json.dumps(ret)


@app.errorhandler(exceptions.InternalServerError)
def handle_bad_request(e):
    print(e)
    return 'bad request! 500', 500, e


@app.errorhandler(exceptions.NotFound)
def handle_bad_request(e):
    print(e)
    return 'bad request! 404', 404


@app.route('/')
@app.route('/konference')
@app.route('/login')
@app.route('/user')
@app.route('/clicked_konf')
@app.route('/clicked_ticket')
@cross_origin()
def serve():
    return send_from_directory(app.static_folder, 'index.html')


if __name__ == '__main__':
    app.run(debug=True, port=8000)
