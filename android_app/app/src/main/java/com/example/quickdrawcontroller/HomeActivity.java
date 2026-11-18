package com.example.quickdrawcontroller;

import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

/**
 * HomeActivity: The Console Game Library Browser.
 * Traverses games sequentially and launches the selected game via Android Intent.
 */
public class HomeActivity extends AppCompatActivity implements WebSocketManager.MessageListener, WebSocketManager.ConnectionListener {

    public static class GameInfo {
        public String id;
        public String title;
        public String description;
        public String icon;
        public Class<?> activityClass;

        public GameInfo(String id, String title, String description, String icon, Class<?> activityClass) {
            this.id = id;
            this.title = title;
            this.description = description;
            this.icon = icon;
            this.activityClass = activityClass;
        }
    }

    private static final String PREFS_NAME = "QuickdrawPrefs";
    private static final String KEY_SERVER_IP = "server_ip";
    private static final String KEY_PLAYER_ROLE = "player_role";

    private TextView txtStatus;
    private TextView txtGameBadge;
    private TextView txtGameIcon;
    private TextView txtGameTitle;
    private TextView txtGameDesc;
    private Button btnRoleToggle;
    private Button btnServerIp;
    private Button btnPrev;
    private Button btnLaunch;
    private Button btnNext;

    private WebSocketManager wsManager;
    private SharedPreferences prefs;
    private int currentIndex = 0;
    private final List<GameInfo> games = new ArrayList<>();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_home);

        initGameCatalog();

        prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        String savedIp = prefs.getString(KEY_SERVER_IP, "10.217.76.160");
        String savedRole = prefs.getString(KEY_PLAYER_ROLE, "player1");

        wsManager = WebSocketManager.getInstance();
        wsManager.setServerIp(savedIp);
        wsManager.setPlayerRole(savedRole);

        initViews();
        setupListeners();
        updateRoleDisplay();
        updateCardDisplay();

        wsManager.connect();
    }

    @Override
    protected void onResume() {
        super.onResume();
        wsManager.addMessageListener(this);
        wsManager.addConnectionListener(this);
        updateStatusDisplay();
    }

    @Override
    protected void onPause() {
        super.onPause();
        wsManager.removeMessageListener(this);
        wsManager.removeConnectionListener(this);
    }

    private void initGameCatalog() {
        games.add(new GameInfo("quickdraw", "Quickdraw", "Wild West Outlaw Duel! Holster phone, listen, and draw on target word.", "🤠", QuickdrawActivity.class));
        games.add(new GameInfo("tennis", "Tennis", "Swing phone to hit. Tilt as you swing to place the ball.", "🎾", TennisActivity.class));
        games.add(new GameInfo("racing", "Racing", "Steer phone like a steering wheel, hold gas & brake pedals.", "🏎️", RacingActivity.class));
        games.add(new GameInfo("boxing", "Boxing", "Punch forward to hit, hold button to guard, tilt hard to dodge.", "🥊", BoxingActivity.class));
        games.add(new GameInfo("quiz", "Quiz", "Four-button trivia showdown; race to lock in A, B, C, or D!", "❓", QuizActivity.class));
        games.add(new GameInfo("bowling", "Bowling", "Tilt to aim, hold trigger, swing down, release to bowl with real pin physics!", "🎳", SportsActivity.class));
        games.add(new GameInfo("basketball", "Basketball", "Tilt to aim, swing up to shoot before the shot clock expires.", "🏀", SportsActivity.class));
        games.add(new GameInfo("ducks", "Duck Shooting", "Aim phone like a light gun; track your reticle and pull trigger!", "🦆", SportsActivity.class));
        games.add(new GameInfo("darts", "Darts", "Tilt to sight your throw, flick phone to launch dart at the board.", "🎯", SportsActivity.class));
        games.add(new GameInfo("cuppong", "Cup Pong", "Table tennis ball throw physics into red cups.", "🥤", SportsActivity.class));
        games.add(new GameInfo("golf", "Golf", "Address the ball, calibrate your backswing, and drive onto green.", "⛳", SportsActivity.class));
        games.add(new GameInfo("billiards", "Billiards", "8-ball pool with real-time cue ball spin and pocketing.", "🎱", SportsActivity.class));
        games.add(new GameInfo("tanks", "Tanks", "Drive your tank and aim artillery shells around obstacles.", "🚀", SportsActivity.class));
        games.add(new GameInfo("airhockey", "Air Hockey", "Glide your mallet across the table surface to score puck goals.", "🏒", SportsActivity.class));
        games.add(new GameInfo("baseball", "Baseball", "Watch the pitch, time your swing with the phone bat!", "⚾", SportsActivity.class));
        games.add(new GameInfo("lightcycles", "Light Cycles", "High-speed neon light trails; dodge walls and cut off opponents!", "⚡", SportsActivity.class));
        games.add(new GameInfo("connect4", "Connect Four", "Drop chips into columns by tilting and tapping.", "🔴", SportsActivity.class));
        games.add(new GameInfo("battleships", "Battleships", "Command your naval fleet against a friend or AI.", "🚢", SportsActivity.class));
        games.add(new GameInfo("chess", "Chess", "3D chess arena; tilt to piece, pick up, and place.", "♟️", SportsActivity.class));
        games.add(new GameInfo("dame", "Dame (Checkers)", "Classic checkers board with real piece jumping.", "🏁", SportsActivity.class));
    }

    private void initViews() {
        txtStatus = findViewById(R.id.txtStatus);
        txtGameBadge = findViewById(R.id.txtGameBadge);
        txtGameIcon = findViewById(R.id.txtGameIcon);
        txtGameTitle = findViewById(R.id.txtGameTitle);
        txtGameDesc = findViewById(R.id.txtGameDesc);
        btnRoleToggle = findViewById(R.id.btnRoleToggle);
        btnServerIp = findViewById(R.id.btnServerIp);
        btnPrev = findViewById(R.id.btnPrev);
        btnLaunch = findViewById(R.id.btnLaunch);
        btnNext = findViewById(R.id.btnNext);
    }

    private void setupListeners() {
        btnRoleToggle.setOnClickListener(v -> {
            String newRole = wsManager.getPlayerRole().equals("player1") ? "player2" : "player1";
            wsManager.setPlayerRole(newRole);
            prefs.edit().putString(KEY_PLAYER_ROLE, newRole).apply();
            updateRoleDisplay();
        });

        btnServerIp.setOnClickListener(v -> showIpDialog());

        btnPrev.setOnClickListener(v -> {
            navigate(-1);
            wsManager.sendNav(-1);
        });

        btnNext.setOnClickListener(v -> {
            navigate(1);
            wsManager.sendNav(1);
        });

        btnLaunch.setOnClickListener(v -> launchCurrentGame());
    }

    private void navigate(int delta) {
        int n = games.size();
        currentIndex = ((currentIndex + delta) % n + n) % n;
        updateCardDisplay();
    }

    private void updateCardDisplay() {
        if (currentIndex >= 0 && currentIndex < games.size()) {
            GameInfo game = games.get(currentIndex);
            txtGameBadge.setText("GAME " + (currentIndex + 1) + " OF " + games.size());
            txtGameIcon.setText(game.icon);
            txtGameTitle.setText(game.title.toUpperCase());
            txtGameDesc.setText(game.description);
        }
    }

    private void updateRoleDisplay() {
        String role = wsManager.getPlayerRole();
        btnRoleToggle.setText(role.equals("player1") ? "P1" : "P2");
        btnRoleToggle.setBackgroundColor(role.equals("player1") ? 0xFF0077FF : 0xFFFF4400);
    }

    private void updateStatusDisplay() {
        if (wsManager.isConnected()) {
            txtStatus.setText("● Connected to " + wsManager.getServerIp());
            txtStatus.setTextColor(0xFF00FF88);
        } else {
            txtStatus.setText("○ Disconnected - Tap ⚙ IP to configure");
            txtStatus.setTextColor(0xFFFF4444);
        }
    }

    private void showIpDialog() {
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("Console Server IP");
        final EditText input = new EditText(this);
        input.setText(wsManager.getServerIp());
        builder.setView(input);

        builder.setPositiveButton("Connect", (dialog, which) -> {
            String ip = input.getText().toString().trim();
            wsManager.setServerIp(ip);
            prefs.edit().putString(KEY_SERVER_IP, ip).apply();
            wsManager.connect();
        });
        builder.setNegativeButton("Cancel", (dialog, which) -> dialog.cancel());
        builder.show();
    }

    private void launchCurrentGame() {
        if (currentIndex < 0 || currentIndex >= games.size()) return;
        GameInfo game = games.get(currentIndex);

        // Tell the laptop console server to launch this game
        wsManager.sendStart(game.id);

        // Start the matching Android Activity via Intent
        Intent intent = new Intent(this, game.activityClass);
        intent.putExtra("game_id", game.id);
        intent.putExtra("title", game.title);
        intent.putExtra("desc", game.description);
        startActivity(intent);
    }

    private void launchGameById(String gameId) {
        for (int i = 0; i < games.size(); i++) {
            if (games.get(i).id.equalsIgnoreCase(gameId)) {
                currentIndex = i;
                updateCardDisplay();
                Intent intent = new Intent(this, games.get(i).activityClass);
                intent.putExtra("game_id", games.get(i).id);
                intent.putExtra("title", games.get(i).title);
                intent.putExtra("desc", games.get(i).description);
                startActivity(intent);
                return;
            }
        }
    }

    // -------------------------------------------------------------
    // WebSocket Message & Connection Listeners
    // -------------------------------------------------------------
    @Override
    public void onMessage(JSONObject data) {
        String type = data.optString("type");
        String kind = data.optString("t");

        // Real-time synchronization when laptop scrolls carousel
        if ("sync_card".equals(kind)) {
            int idx = data.optInt("index", currentIndex);
            if (idx >= 0 && idx < games.size()) {
                currentIndex = idx;
                updateCardDisplay();
            }
        } else if ("sync_state".equals(type)) {
            int idx = data.optInt("selected_index", currentIndex);
            if (idx >= 0 && idx < games.size()) {
                currentIndex = idx;
                updateCardDisplay();
            }
        } else if ("game_started".equals(type)) {
            String gameId = data.optString("game_id", "quickdraw");
            launchGameById(gameId);
        } else if ("mode".equals(kind)) {
            String layout = data.optString("layout", "");
            if ("quickdraw".equals(layout)) {
                launchGameById("quickdraw");
            } else if ("pedals".equals(layout)) {
                launchGameById("racing");
            } else if ("quiz".equals(layout)) {
                launchGameById("quiz");
            }
        }
    }

    @Override
    public void onConnected() {
        updateStatusDisplay();
    }

    @Override
    public void onDisconnected() {
        updateStatusDisplay();
    }

    @Override
    public void onError(Exception ex) {
        updateStatusDisplay();
    }
}
