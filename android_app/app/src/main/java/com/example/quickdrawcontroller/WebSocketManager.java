package com.example.quickdrawcontroller;

import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import org.java_websocket.client.WebSocketClient;
import org.java_websocket.handshake.ServerHandshake;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.net.URI;
import java.util.ArrayList;
import java.util.List;

/**
 * Singleton WebSocket Manager
 * Maintains a persistent WebSocket connection across all Android Activities.
 */
public class WebSocketManager {
    private static final String TAG = "WebSocketManager";
    private static WebSocketManager instance;

    public interface ConnectionListener {
        void onConnected();
        void onDisconnected();
        void onError(Exception ex);
    }

    public interface MessageListener {
        void onMessage(JSONObject data);
    }

    private WebSocketClient client;
    private String serverIp = "10.217.76.160";
    private int serverPort = 8000;
    private String playerRole = "player1";
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private final List<MessageListener> messageListeners = new ArrayList<>();
    private final List<ConnectionListener> connectionListeners = new ArrayList<>();

    public static synchronized WebSocketManager getInstance() {
        if (instance == null) {
            instance = new WebSocketManager();
        }
        return instance;
    }

    private WebSocketManager() {}

    public void setServerIp(String ip) {
        this.serverIp = ip;
    }

    public String getServerIp() {
        return serverIp;
    }

    public void setPlayerRole(String role) {
        this.playerRole = role;
        sendRole();
    }

    public String getPlayerRole() {
        return playerRole;
    }

    public boolean isConnected() {
        return client != null && client.isOpen();
    }

    public void addMessageListener(MessageListener listener) {
        synchronized (messageListeners) {
            if (!messageListeners.contains(listener)) {
                messageListeners.add(listener);
            }
        }
    }

    public void removeMessageListener(MessageListener listener) {
        synchronized (messageListeners) {
            messageListeners.remove(listener);
        }
    }

    public void addConnectionListener(ConnectionListener listener) {
        synchronized (connectionListeners) {
            if (!connectionListeners.contains(listener)) {
                connectionListeners.add(listener);
            }
        }
    }

    public void removeConnectionListener(ConnectionListener listener) {
        synchronized (connectionListeners) {
            connectionListeners.remove(listener);
        }
    }

    public void connect() {
        disconnect();

        try {
            URI uri = new URI("ws://" + serverIp + ":" + serverPort);
            client = new WebSocketClient(uri) {
                @Override
                public void onOpen(ServerHandshake handshakedata) {
                    Log.d(TAG, "Connected to: " + uri);
                    sendRole();
                    mainHandler.post(() -> {
                        synchronized (connectionListeners) {
                            for (ConnectionListener l : connectionListeners) l.onConnected();
                        }
                    });
                }

                @Override
                public void onMessage(String message) {
                    try {
                        JSONObject json = new JSONObject(message);
                        mainHandler.post(() -> {
                            synchronized (messageListeners) {
                                for (MessageListener l : new ArrayList<>(messageListeners)) {
                                    l.onMessage(json);
                                }
                            }
                        });
                    } catch (JSONException e) {
                        Log.e(TAG, "JSON parse error: " + e.getMessage());
                    }
                }

                @Override
                public void onClose(int code, String reason, boolean remote) {
                    Log.d(TAG, "Disconnected: " + reason);
                    mainHandler.post(() -> {
                        synchronized (connectionListeners) {
                            for (ConnectionListener l : connectionListeners) l.onDisconnected();
                        }
                    });
                }

                @Override
                public void onError(Exception ex) {
                    Log.e(TAG, "WebSocket error: " + ex.getMessage());
                    mainHandler.post(() -> {
                        synchronized (connectionListeners) {
                            for (ConnectionListener l : connectionListeners) l.onError(ex);
                        }
                    });
                }
            };
            client.connect();
        } catch (Exception e) {
            Log.e(TAG, "Connect error: " + e.getMessage());
        }
    }

    public void disconnect() {
        if (client != null) {
            try { client.close(); } catch (Exception ignored) {}
            client = null;
        }
    }

    public void send(JSONObject json) {
        if (isConnected()) {
            client.send(json.toString());
        }
    }

    public void sendRole() {
        try {
            JSONObject obj = new JSONObject();
            obj.put("type", "set_role");
            obj.put("role", playerRole);
            obj.put("player", playerRole);
            send(obj);
        } catch (JSONException ignored) {}
    }

    public void sendHome() {
        try {
            JSONObject obj = new JSONObject();
            obj.put("type", "home");
            obj.put("t", "menu");
            send(obj);
        } catch (JSONException ignored) {}
    }

    public void sendNav(int dir) {
        try {
            JSONObject obj = new JSONObject();
            obj.put("type", "navigate");
            obj.put("direction", dir == 1 ? "next" : "prev");
            obj.put("t", "nav");
            obj.put("dir", dir);
            send(obj);
        } catch (JSONException ignored) {}
    }

    public void sendStart(String gameId) {
        try {
            JSONObject obj = new JSONObject();
            obj.put("type", "select_game");
            obj.put("t", "start");
            obj.put("game_id", gameId);
            obj.put("id", gameId);
            send(obj);
        } catch (JSONException ignored) {}
    }

    public void sendButton(String key, boolean down) {
        try {
            JSONObject obj = new JSONObject();
            obj.put("t", "b");
            obj.put("k", key);
            obj.put("d", down ? 1 : 0);
            send(obj);
        } catch (JSONException ignored) {}
    }

    public void sendMotion(float[] ag, float[] rr, float[] ori) {
        try {
            JSONObject obj = new JSONObject();
            obj.put("t", "m");
            JSONArray agArr = new JSONArray();
            JSONArray rrArr = new JSONArray();
            JSONArray oriArr = new JSONArray();
            for (float v : ag) agArr.put((double) Math.round(v * 100) / 100.0);
            for (float v : rr) rrArr.put((double) Math.round(v * 100) / 100.0);
            for (float v : ori) oriArr.put((double) Math.round(v * 100) / 100.0);
            obj.put("ag", agArr);
            obj.put("rr", rrArr);
            obj.put("o", oriArr);
            send(obj);
        } catch (JSONException ignored) {}
    }

    public void sendShot(long timestamp) {
        try {
            JSONObject obj = new JSONObject();
            obj.put("type", "shot");
            obj.put("t", "shoot");
            obj.put("player", playerRole);
            obj.put("time", timestamp);
            send(obj);
        } catch (JSONException ignored) {}
    }
}
