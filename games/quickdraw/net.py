import time
import json
import threading
import queue
from websocket_server import WebsocketServer

# Thread-safe queue for incoming messages
message_queue = queue.Queue()

# Mapping of client id to player name
clients_to_players = {}

def new_client(client, server):
    pass

def client_left(client, server):
    if client and 'id' in client:
        clients_to_players.pop(client['id'], None)

def message_received(client, server, message):
    server_receive_time = time.time()
    
    try:
        data = json.loads(message)
        player = data.get('player', 'Unknown')
        device_time = data.get('time', 'Unknown time')
        
        # Track the player name for this client
        if client and 'id' in client:
            clients_to_players[client['id']] = player
            
        # Push the parsed data onto the queue
        message_queue.put((player, device_time, server_receive_time))
    except json.JSONDecodeError:
        # For this diagnostic listener, we ignore non-JSON messages
        pass

def get_connected_players():
    """Returns the current set of identified player names."""
    return set(clients_to_players.values())

def _run_server(host, port):
    server = WebsocketServer(host=host, port=port)
    server.set_fn_new_client(new_client)
    server.set_fn_client_left(client_left)
    server.set_fn_message_received(message_received)
    server.run_forever()

def start_server(host='0.0.0.0', port=8000):
    """
    Starts the websocket server in a background daemon thread.
    Returns the message_queue.
    """
    server_thread = threading.Thread(target=_run_server, args=(host, port), daemon=True)
    server_thread.start()
    return message_queue

if __name__ == "__main__":
    print("Starting network listener standalone...")
    q = start_server()
    print("Listening on 0.0.0.0:8000. Waiting for messages...")
    
    try:
        while True:
            # This blocks until an item is available
            player, device_time, server_recv_time = q.get()
            
            print(f"[{player}] pressed at {device_time} (server received at {server_recv_time:.3f})")
            print(f"  -> Currently identified players: {get_connected_players()}")
            
    except KeyboardInterrupt:
        print("\nExiting standalone server...")
