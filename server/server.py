import socket
import threading
import json
import sqlite3
import hashlib

HOST = '0.0.0.0'
PORT = 5555

# Database Setup
def init_db():
    conn = sqlite3.connect('game_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS characters 
                 (username TEXT PRIMARY KEY, body INTEGER, hair INTEGER, shirt INTEGER, pants INTEGER, eyes INTEGER)''')
    conn.commit()
    conn.close()

init_db()

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

print(f"Server started on {HOST}:{PORT}")

clients = {} # {addr_str: {'conn': conn, 'pos': {'x': 0, 'y': 0}, 'username': None, 'appearance': {}}}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_character(username):
    db = sqlite3.connect('game_data.db')
    c = db.cursor()
    c.execute("SELECT body, hair, shirt, pants, eyes FROM characters WHERE username = ?", (username,))
    row = c.fetchone()
    db.close()
    if row:
        return {"body": row[0], "hair": row[1], "shirt": row[2], "pants": row[3], "eyes": row[4]}
    return None

def handle_login(data, conn, addr_str):
    username = data.get('username')
    password = data.get('password')
    
    db = sqlite3.connect('game_data.db')
    c = db.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    db.close()
    
    if row and row[0] == hash_password(password):
        clients[addr_str]['username'] = username
        
        # Check if character exists
        char_data = get_character(username)
        has_char = char_data is not None
        if has_char:
            clients[addr_str]['appearance'] = char_data
            
        conn.send(json.dumps({
            "type": "LOGIN_SUCCESS", 
            "username": username,
            "has_character": has_char,
            "appearance": char_data
        }).encode('utf-8'))
        return True
    else:
        conn.send(json.dumps({"type": "LOGIN_FAIL", "message": "Invalid credentials"}).encode('utf-8'))
        return False

def handle_create_character(data, conn, addr_str):
    username = clients[addr_str].get('username')
    if not username:
        return
    
    appearance = data.get('appearance') # {body: 0, hair: 1, ...}
    if not appearance:
        return

    db = sqlite3.connect('game_data.db')
    c = db.cursor()
    try:
        c.execute("INSERT OR REPLACE INTO characters (username, body, hair, shirt, pants, eyes) VALUES (?, ?, ?, ?, ?, ?)",
                  (username, appearance['body'], appearance['hair'], appearance['shirt'], appearance['pants'], appearance['eyes']))
        db.commit()
        
        clients[addr_str]['appearance'] = appearance
        conn.send(json.dumps({"type": "CREATE_CHAR_SUCCESS", "appearance": appearance}).encode('utf-8'))
    except Exception as e:
        print(f"Error creating char: {e}")
        conn.send(json.dumps({"type": "CREATE_CHAR_FAIL"}).encode('utf-8'))
    finally:
        db.close()

def handle_register(data, conn):
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        conn.send(json.dumps({"type": "REGISTER_FAIL", "message": "Missing info"}).encode('utf-8'))
        return

    db = sqlite3.connect('game_data.db')
    c = db.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash_password(password)))
        db.commit()
        conn.send(json.dumps({"type": "REGISTER_SUCCESS"}).encode('utf-8'))
    except sqlite3.IntegrityError:
        conn.send(json.dumps({"type": "REGISTER_FAIL", "message": "Username taken"}).encode('utf-8'))
    finally:
        db.close()

def broadcast_state(sender_addr):
    # Only send positions of logged-in users with characters
    state = {}
    for k, v in clients.items():
        if v.get('username') and v.get('appearance'):
            state[k] = {'pos': v['pos'], 'appearance': v['appearance'], 'username': v['username']}
            
    data = json.dumps({"type": "GAME_STATE", "data": state})
    
    for client_addr, client_data in clients.items():
        if client_data.get('username'): 
            try:
                client_data['conn'].send(data.encode('utf-8'))
            except:
                pass

def handle_client(conn, addr):
    print(f"New connection: {addr}")
    addr_str = str(addr)
    clients[addr_str] = {'conn': conn, 'pos': {'x': 400, 'y': 300}, 'username': None, 'appearance': None}
    
    try:
        while True:
            data_raw = conn.recv(4096).decode('utf-8')
            if not data_raw:
                break
            
            try:
                msg = json.loads(data_raw)
                msg_type = msg.get('type')
                
                if msg_type == 'LOGIN':
                    if handle_login(msg, conn, addr_str):
                        print(f"{clients[addr_str]['username']} logged in.")
                
                elif msg_type == 'REGISTER':
                    handle_register(msg, conn)
                
                elif msg_type == 'CREATE_CHARACTER':
                    handle_create_character(msg, conn, addr_str)
                
                elif msg_type == 'MOVE':
                    if clients[addr_str]['username']: 
                        clients[addr_str]['pos'] = msg.get('pos')
                        broadcast_state(addr_str)
                        
            except json.JSONDecodeError:
                pass
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print(f"Disconnected: {addr}")
        if addr_str in clients:
            del clients[addr_str]
        conn.close()

def main():
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

if __name__ == "__main__":
    main()
