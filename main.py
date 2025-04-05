import flask
import hashlib
import logging
import uuid
import time
import os
import json

data_path = os.path.realpath(os.path.expanduser(os.getenv("EGS_DATA_PATH", "./data")))
if not os.path.exists(data_path):
    os.mkdir(data_path)

logging.basicConfig(filename=os.path.join(data_path, "easy_game_server.log"), level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = flask.Flask(__name__)

hashed_passwords = {}

statuses = {}

session_keys = {}

friends = {}

def save_data():
    global friends, hashed_passwords
    with open(os.path.join(data_path, "credentials.json"), "wt") as cf:
        json.dump(hashed_passwords, cf)
    with open(os.path.join(data_path, "friends.json"), "wt") as ff:
        json.dump(friends, ff)

def load_data():
    global friends, hashed_passwords
    if os.path.exists(os.path.join(data_path, "credentials.json")):
        with open(os.path.join(data_path, "credentials.json"), "rb") as cf:
            hashed_passwords = json.load(cf)
    if os.path.exists(os.path.join(data_path, "friends.json")):
        with open(os.path.join(data_path, "friends.json"), "rb") as ff:
            friends = json.load(ff)

load_data()

@app.route("/api/authenticate")
def authenticate():
    global session_keys, hashed_passwords
    username = flask.request.args.get("username")
    password = flask.request.args.get("password")
    if username is None or password is None:
        return {"status": "error", "error": "a username and password must be provided"}
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    logger.debug(f"Someone is trying to login with username: {username} and hashed password: {hashed_password}")
    if username not in hashed_passwords:
        logger.warning(f"The user {username} is unknown")
        return {"status": "error", "error": "unkown user"}
    if hashed_passwords[username] != hashed_password:
        logger.warning(f"The password ({hashed_password}) provided by {username} is incorrect")
        return {"status": "error", "error": "invalid password"}
    session_key = str(uuid.uuid4())
    logger.debug(f"User {username} generated the session key {session_key}")
    session_keys[session_key] = {"username": username, "time_stamp": int(time.time())}
    return {"status": "success", "session_key": session_key, "username": username}

@app.route("/api/update-status")
def update_status():
    global session_keys, statuses
    session_key = flask.request.args.get("session_key")
    status = flask.request.args.get("status")
    if session_key is None or status is None:
        return {"status": "error", "error": "a session key and status must be provided"}
    if session_key not in session_keys:
        logger.warning(f"The session key {session_key} is invalid")
        return {"status": "error", "error": "invalid session key"}
    username = session_keys[session_key]["username"]
    if int(time.time()) - session_keys[session_key]["time_stamp"] > 43200:
        logger.warning(f"The session key {session_key} for user {username} expired")
        session_keys.pop(session_key)
        return {"status": "error", "error": "session key expired"}
    logger.debug(f"User {username} updated status to {status}")
    statuses[username] = {"text": status, "time_stamp": int(time.time())}
    return {"status": "success"}

@app.route("/api/get-friends")
def get_friends():
    global friends, statuses, session_keys
    session_key = flask.request.args.get("session_key")
    if session_key is None:
        return {"status": "error", "error": "a session key must be provided"}
    if session_key not in session_keys:
        logger.warning(f"The session key {session_key} is invalid")
        return {"status": "error", "error": "invalid session key"}
    username = session_keys[session_key]["username"]
    if int(time.time()) - session_keys[session_key]["time_stamp"] > 43200:
        logger.warning(f"The session key {session_key} for user {username} expired")
        session_keys.pop(session_key)
        return {"status": "error", "error": "session key expired"}
    if username not in friends:
        logger.warning(f"User {username} has no friends")
        return {"status": "success", "friends": {}}
    data = {}
    for friend in friends[username]:
        if friend not in friends or username not in friends[friend]:
            logger.warning(f"User {friend}, friend of {username} is not a friend of {username}")
            continue
        if friend not in statuses:
            logger.info(f"User {friend}, friend of {username} is offline")
            data[friend] = "Offline"
            continue
        if int(time.time()) - statuses[friend]["time_stamp"] > 90:
            logger.warning(f"User {friend}, friend of {username} is now offline")
            statuses.pop(friend)
            data[friend] = "Offline"
            continue
        data[friend] = statuses[friend]["text"]

    return {"status": "success", "friends": data}

@app.route("/api/add-friend")
def add_friend():
    global friends, session_keys
    session_key = flask.request.args.get("session_key")
    friend = flask.request.args.get("friend")
    if session_key is None or friend is None:
        return {"status": "error", "error": "a session key and friend must be provided"}
    if session_key not in session_keys:
        logger.warning(f"The session key {session_key} is invalid")
        return {"status": "error", "error": "invalid session key"}
    username = session_keys[session_key]["username"]
    if int(time.time()) - session_keys[session_key]["time_stamp"] > 43200:
        logger.warning(f"The session key {session_key} for user {username} expired")
        session_keys.pop(session_key)
        return {"status": "error", "error": "session key expired"}
    if friend not in hashed_passwords:
        logger.warning(f"User {username} wants to add the friend {friend} but it does not exist")
        return {"status": "error", "error": "friend not found"}
    if username not in friends:
        friends[username] = []
    friends[username].append(friend)
    save_data()
    return {"status": "success"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6500, debug=True)
