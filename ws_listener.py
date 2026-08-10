import datetime
import json
from websocket_server import WebsocketServer

# Mapping of client id to player name
clients_to_players = {}

def new_client(client, server):
    client_address = f"{client['address'][0]}:{client['address'][1]}"
    print(f"[{get_timestamp()}] Client connected: {client_address}")

def client_left(client, server):
    client_address = f"{client['address'][0]}:{client['address'][1]}"
    player_name = clients_to_players.pop(client['id'], None)
    
    if player_name:
        print(f"[{get_timestamp()}] Client disconnected: {client_address} (Player: {player_name})")
    else:
        print(f"[{get_timestamp()}] Client disconnected: {client_address}")

def message_received(client, server, message):
    client_address = f"{client['address'][0]}:{client['address'][1]}"
    
    try:
        data = json.loads(message)
        player = data.get('player', 'Unknown')
        client_time = data.get('time', 'Unknown time')
        
        # Store the player name for this client
        clients_to_players[client['id']] = player
            
        print(f"[{player}] pressed at {client_time} (server received at {get_timestamp()})")
    except json.JSONDecodeError:
        print(f"[{get_timestamp()}] Message from {client_address} (not JSON): {message}")

def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

if __name__ == "__main__":
    PORT = 8000
    HOST = '0.0.0.0'
    
    print(f"Starting WebSocket server on {HOST}:{PORT}...")
    server = WebsocketServer(host=HOST, port=PORT)
    server.set_fn_new_client(new_client)
    server.set_fn_client_left(client_left)
    server.set_fn_message_received(message_received)
    server.run_forever()
