package com.example.quickdrawcontroller;

import android.os.Bundle;
import android.widget.Button;
import android.widget.TextView;

import org.json.JSONObject;

/**
 * TiltMazeActivity: Phone controller for Tilt Maze ball rolling game.
 * Uses MotionHelper for fused orientation (aim/roll & lean/pitch) and shake hop detection.
 */
public class TiltMazeActivity extends BaseGameActivity {

    private TextView txtTiltStatus;
    private TextView txtSensorStats;
    private TextView txtPlayerBadge;
    private Button btnJump;
    private Button btnCalibrate;

    private MotionHelper motionHelper;
    private long lastJumpTime = 0;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_tilt_maze);

        setupHomeButton(R.id.btnHome);

        txtTiltStatus = findViewById(R.id.txtTiltStatus);
        txtSensorStats = findViewById(R.id.txtSensorStats);
        txtPlayerBadge = findViewById(R.id.txtPlayerBadge);
        btnJump = findViewById(R.id.btnJump);
        btnCalibrate = findViewById(R.id.btnCalibrate);

        String role = wsManager.getPlayerRole();
        txtPlayerBadge.setText(role.equalsIgnoreCase("player1") ? "P1" : "P2");
        txtPlayerBadge.setBackgroundColor(role.equalsIgnoreCase("player1") ? 0xFF38BDF8 : 0xFFF97316);

        motionHelper = new MotionHelper(this);
        motionHelper.setCallback((ag, rr, ori, statsText) -> {
            float ax = ag[0], ay = ag[1], az = ag[2];
            double mag = Math.sqrt(ax * ax + ay * ay + az * az);
            double dyn = Math.max(0, mag - 9.8);

            runOnUiThread(() -> {
                txtSensorStats.setText(statsText);

                long now = System.currentTimeMillis();
                // Shake phone triggers jump
                if (dyn > 15.0 && (now - lastJumpTime > 500)) {
                    lastJumpTime = now;
                    fireJump("SHAKE JUMP!");
                }
            });
        });

        btnJump.setOnClickListener(v -> fireJump("JUMP!"));

        if (btnCalibrate != null) {
            btnCalibrate.setOnClickListener(v -> {
                motionHelper.calibrate();
                try {
                    JSONObject cal = new JSONObject();
                    cal.put("t", "cal");
                    wsManager.send(cal);
                } catch (Exception ignored) {
                }
                txtTiltStatus.setText("NEUTRAL TILT ZEROED");
                vibrate(40);
                txtTiltStatus.postDelayed(() -> txtTiltStatus.setText("TILT PHONE TO ROLL"), 1200);
            });
        }
    }

    private void fireJump(String label) {
        vibrate(35);
        txtTiltStatus.setText("🦘 " + label);
        wsManager.sendButton("a", true);
        btnJump.postDelayed(() -> {
            wsManager.sendButton("a", false);
            txtTiltStatus.setText("TILT PHONE TO ROLL");
        }, 120);
    }

    @Override
    public void onMessage(JSONObject data) {
        super.onMessage(data);
        String type = data.optString("t", data.optString("type"));
        if ("buzz".equals(type) || "vibrate".equals(type)) {
            int ms = data.optInt("ms", 40);
            vibrate(ms);
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (motionHelper != null) {
            motionHelper.start();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (motionHelper != null) {
            motionHelper.stop();
        }
    }
}
