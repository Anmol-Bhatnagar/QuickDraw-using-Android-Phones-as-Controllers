package com.example.quickdrawcontroller;

import android.os.Bundle;
import android.widget.Button;
import android.widget.TextView;

/**
 * SportsActivity: Universal sensor & action controller for sports games
 * (Bowling, Basketball, Golf, Baseball, Ducks, Darts, Cup Pong, Billiards, Tanks, etc.).
 * Uses MotionHelper for fused, smoothed orientation and accurate HTML5-compliant motion packets.
 */
public class SportsActivity extends BaseGameActivity {

    private TextView txtSportTitle;
    private TextView txtSportHint;
    private TextView txtSensorStats;
    private TextView txtPlayerBadge;
    private Button btnAction;
    private Button btnCalibrate;

    private MotionHelper motionHelper;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_sports);

        setupHomeButton(R.id.btnHome);

        txtSportTitle = findViewById(R.id.txtSportTitle);
        txtSportHint = findViewById(R.id.txtSportHint);
        txtSensorStats = findViewById(R.id.txtSensorStats);
        txtPlayerBadge = findViewById(R.id.txtPlayerBadge);
        btnAction = findViewById(R.id.btnAction);
        btnCalibrate = findViewById(R.id.btnCalibrate);

        String title = getIntent().getStringExtra("title");
        if (title != null && !title.isEmpty()) {
            txtSportTitle.setText("🎮 " + title.toUpperCase());
        }

        String desc = getIntent().getStringExtra("desc");
        if (desc != null && !desc.isEmpty()) {
            txtSportHint.setText(desc);
        }

        txtPlayerBadge.setText(wsManager.getPlayerRole().equalsIgnoreCase("player1") ? "P1" : "P2");
        txtPlayerBadge.setBackgroundColor(wsManager.getPlayerRole().equalsIgnoreCase("player1") ? 0xFF0077FF : 0xFFFF4400);

        // Initialize motion processor with fused orientation & smoothing
        motionHelper = new MotionHelper(this);
        motionHelper.setCallback((ag, rr, ori, statsText) -> {
            runOnUiThread(() -> txtSensorStats.setText(statsText));
        });

        btnAction.setOnClickListener(v -> fireAction());
        btnCalibrate.setOnClickListener(v -> {
            motionHelper.calibrate();
            txtSensorStats.setText("RE-CENTERED (AIM ZEROED)");
        });
    }

    private void fireAction() {
        vibrate(50);
        wsManager.sendButton("a", true);
        btnAction.postDelayed(() -> wsManager.sendButton("a", false), 80);
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
