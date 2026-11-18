package com.example.quickdrawcontroller;

import android.content.Context;
import android.os.Build;
import android.os.Bundle;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.os.VibratorManager;
import android.widget.Button;

import androidx.appcompat.app.AppCompatActivity;

import org.json.JSONObject;

/**
 * Base Activity for all Game Controller screens.
 * Provides the persistent ⌂ HOME button and common haptic feedback.
 */
public abstract class BaseGameActivity extends AppCompatActivity implements WebSocketManager.MessageListener {

    protected WebSocketManager wsManager;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        wsManager = WebSocketManager.getInstance();
    }

    @Override
    protected void onResume() {
        super.onResume();
        wsManager.addMessageListener(this);
    }

    @Override
    protected void onPause() {
        super.onPause();
        wsManager.removeMessageListener(this);
    }

    /**
     * Wires the persistent ⌂ HOME button to return to the Home/Library screen.
     */
    protected void setupHomeButton(int homeButtonId) {
        Button btnHome = findViewById(homeButtonId);
        if (btnHome != null) {
            btnHome.setOnClickListener(v -> {
                vibrate(40);
                wsManager.sendHome();
                finish(); // Returns to HomeActivity
            });
        }
    }

    @Override
    public void onMessage(JSONObject data) {
        String type = data.optString("type");
        String kind = data.optString("t");

        // If laptop console exits to library, return to HomeActivity
        if ("home".equals(type) || "menu".equals(kind) || "game_stopped".equals(type)) {
            finish();
        }
    }

    @SuppressWarnings("deprecation")
    public void vibrate(long durationMs) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                VibratorManager vm = (VibratorManager) getSystemService(Context.VIBRATOR_MANAGER_SERVICE);
                if (vm != null) {
                    vm.getDefaultVibrator().vibrate(VibrationEffect.createOneShot(durationMs, VibrationEffect.DEFAULT_AMPLITUDE));
                    return;
                }
            }
            Vibrator v = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
            if (v != null) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    v.vibrate(VibrationEffect.createOneShot(durationMs, VibrationEffect.DEFAULT_AMPLITUDE));
                } else {
                    v.vibrate(durationMs);
                }
            }
        } catch (Exception ignored) {}
    }
}
