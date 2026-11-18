package com.example.quickdrawcontroller;

import android.os.Bundle;
import android.view.KeyEvent;
import android.widget.Button;
import android.widget.TextView;

import org.json.JSONObject;

/**
 * QuickdrawActivity: Wild West Outlaw Duel Controller.
 * Intercepts hardware volume buttons and on-screen trigger to fire.
 */
public class QuickdrawActivity extends BaseGameActivity {

    private TextView txtDuelState;
    private TextView txtPlayerBadge;
    private Button btnTrigger;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_quickdraw);

        setupHomeButton(R.id.btnHome);

        txtDuelState = findViewById(R.id.txtDuelState);
        txtPlayerBadge = findViewById(R.id.txtPlayerBadge);
        btnTrigger = findViewById(R.id.btnTrigger);

        txtPlayerBadge.setText(wsManager.getPlayerRole().equalsIgnoreCase("player1") ? "P1" : "P2");
        txtPlayerBadge.setBackgroundColor(wsManager.getPlayerRole().equalsIgnoreCase("player1") ? 0xFF0077FF : 0xFFFF4400);

        btnTrigger.setOnClickListener(v -> fireTrigger());
    }

    private void fireTrigger() {
        vibrate(70);
        long now = System.currentTimeMillis();
        wsManager.sendShot(now);
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        // Physical trigger: Hardware volume up/down buttons fire duel trigger!
        if ((event.getKeyCode() == KeyEvent.KEYCODE_VOLUME_UP || event.getKeyCode() == KeyEvent.KEYCODE_VOLUME_DOWN)
                && event.getAction() == KeyEvent.ACTION_DOWN) {
            fireTrigger();
            return true;
        }
        return super.dispatchKeyEvent(event);
    }

    @Override
    public void onMessage(JSONObject data) {
        super.onMessage(data);

        String type = data.optString("type");
        String kind = data.optString("t");

        if ("game_state".equals(type) || "quickdraw_state".equals(kind)) {
            String state = data.optString("game_state", data.optString("state"));
            if ("SHOOT".equals(state)) {
                String word = data.optString("word", "DRAW");
                txtDuelState.setText("⚡ SHOOT! \"" + word + "\" ⚡");
                txtDuelState.setTextColor(0xFF00FF88);
                vibrate(120);
            } else if ("FALSE_START".equals(state)) {
                String loser = data.optString("loser", "player");
                txtDuelState.setText("FALSE START by " + loser + "!");
                txtDuelState.setTextColor(0xFFFF4444);
                vibrate(200);
            } else if ("ROUND_OVER".equals(state)) {
                String info = data.optString("info", "ROUND OVER");
                txtDuelState.setText(info);
                txtDuelState.setTextColor(0xFF00D2FF);
                vibrate(50);
            } else {
                String info = data.optString("info", state);
                txtDuelState.setText(info);
                txtDuelState.setTextColor(0xFFFFAA00);
            }
        }
    }
}
