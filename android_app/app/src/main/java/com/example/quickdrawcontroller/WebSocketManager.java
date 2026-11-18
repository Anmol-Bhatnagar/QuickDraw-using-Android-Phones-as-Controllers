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

import javax.net.ssl.SSLContext;

/**
 * Singleton WebSocket Manager
 * Maintains a persistent WebSocket connection across all Android Activities.
 * Supports both local IP (ws://<ip>:8000) and Cloudflare/ngrok tunnels (wss://xxxx.trycloudflare.com/ws).
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
    private String serverIp = "192.168.86.28";
    private int serverPort = 8000;
    private String playerRole = "player1";
    private String lastErrorReason = "";
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

    public String getLastErrorReason() {
        return lastErrorReason;
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
            final URI uri = buildWebSocketUri(serverIp, serverPort);
            Log.d(TAG, "Connecting to WebSocket: " + uri);
            lastErrorReason = "Connecting to " + uri.getHost() + "...";

            client = new WebSocketClient(uri) {
                @Override
                public void onOpen(ServerHandshake handshakedata) {
                    Log.d(TAG, "Successfully connected to: " + uri);
                    lastErrorReason = "";
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
                    Log.d(TAG, "Disconnected (code " + code + "): " + reason);
                    lastErrorReason = (reason != null && !reason.isEmpty()) ? reason : ("Closed (" + code + ")");
                    mainHandler.post(() -> {
                        synchronized (connectionListeners) {
                            for (ConnectionListener l : connectionListeners) l.onDisconnected();
                        }
                    });
                }

                @Override
                public void onError(Exception ex) {
                    String msg = (ex != null && ex.getMessage() != null) ? ex.getMessage() : "Connection failed";
                    Log.e(TAG, "WebSocket error: " + msg, ex);
                    lastErrorReason = msg;
                    mainHandler.post(() -> {
                        synchronized (connectionListeners) {
                            for (ConnectionListener l : connectionListeners) l.onError(ex);
                        }
                    });
                }
            };

            // CRITICAL for Cloudflare tunnels, ngrok and all wss:// connections:
            // Explicitly set Android's default TLS SSLSocketFactory so Cloudflare's TLS certificate & SNI are accepted!
            if ("wss".equalsIgnoreCase(uri.getScheme())) {
                SSLContext sslContext = SSLContext.getInstance("TLS");
                sslContext.init(null, null, null);
                client.setSocketFactory(sslContext.getSocketFactory());
            }

            client.connect();
        } catch (Exception e) {
            String msg = e.getMessage() != null ? e.getMessage() : "URI error";
            Log.e(TAG, "Connect error: " + msg, e);
            lastErrorReason = msg;
            mainHandler.post(() -> {
                synchronized (connectionListeners) {
                    for (ConnectionListener l : connectionListeners) l.onError(e);
                }
            });
        }
    }

    /**
     * Parse any user input (IP, hostname, full URL, /phone link) into a valid WebSocket URI.
     */
    public static URI buildWebSocketUri(String raw, int defaultPort) throws Exception {
        if (raw == null || raw.trim().isEmpty()) {
            throw new IllegalArgumentException("Empty address");
        }
        String s = raw.trim();

        // 1. Strip trailing browser paths like /phone, /phone.html, /index.html
        if (s.endsWith("/phone")) {
            s = s.substring(0, s.length() - "/phone".length());
        } else if (s.endsWith("/phone.html")) {
            s = s.substring(0, s.length() - "/phone.html".length());
        }
        while (s.endsWith("/")) {
            s = s.substring(0, s.length() - 1);
        }

        // 2. Normalize scheme
        if (s.startsWith("https://")) {
            s = "wss://" + s.substring("https://".length());
        } else if (s.startsWith("http://")) {
            s = "ws://" + s.substring("http://".length());
        } else if (!s.startsWith("ws://") && !s.startsWith("wss://")) {
            // No scheme provided
            if (s.contains(".trycloudflare.com") || s.contains(".ngrok") || s.contains(".loca.lt")) {
                s = "wss://" + s;
            } else {
                if (!s.contains(":")) {
                    s = "ws://" + s + ":" + defaultPort;
                } else {
                    s = "ws://" + s;
                }
            }
        }

        // 3. For Cloudflare / ngrok tunnel URLs, ensure the path is /ws
        if (s.contains(".trycloudflare.com") || s.contains(".ngrok") || s.contains(".loca.lt")) {
            URI temp = new URI(s);
            String path = temp.getPath();
            if (path == null || path.isEmpty() || path.equals("/")) {
                s = s + "/ws";
            }
        }

        return new URI(s);
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
