package com.example.quickdrawcontroller;

import android.os.Bundle;
import android.widget.Button;
import android.widget.ProgressBar;
import android.widget.TextView;

/**
 * TennisActivity: Real-time swing detection racquet controller.
 * Uses MotionHelper for fused orientation (shot placement) & linear swing power.
 */
public class TennisActivity extends BaseGameActivity {

    private TextView txtSwingEnergy;
    private TextView txtPlayerBadge;
    private ProgressBar barEnergy;
    private Button btnSwing;
    private Button btnCalibrate;

    private MotionHelper motionHelper;
    private long lastSwingTime = 0;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_tennis);

        setupHomeButton(R.id.btnHome);

        txtSwingEnergy = findViewById(R.id.txtSwingEnergy);
        txtPlayerBadge = findViewById(R.id.txtPlayerBadge);
        barEnergy = findViewById(R.id.barEnergy);
        btnSwing = findViewById(R.id.btnSwing);
        btnCalibrate = findViewById(R.id.btnCalibrate);

        txtPlayerBadge.setText(wsManager.getPlayerRole().equalsIgnoreCase("player1") ? "P1" : "P2");
        txtPlayerBadge.setBackgroundColor(wsManager.getPlayerRole().equalsIgnoreCase("player1") ? 0xFF0077FF : 0xFFFF4400);

        motionHelper = new MotionHelper(this);
        motionHelper.setCallback((ag, rr, ori, statsText) -> {
            float ax = ag[0], ay = ag[1], az = ag[2];
            double mag = Math.sqrt(ax * ax + ay * ay + az * az);
            double dynamicMag = Math.max(0, mag - 9.8);
            int energyPct = (int) Math.min(100, (dynamicMag / 25.0) * 100);

            runOnUiThread(() -> {
                barEnergy.setProgress(energyPct);

                long now = System.currentTimeMillis();
                if (dynamicMag > 16.0 && (now - lastSwingTime > 400)) {
                    lastSwingTime = now;
                    fireSwing();
                } else if (now - lastSwingTime > 500) {
                    txtSwingEnergy.setText(energyPct > 20 ? "ENERGY: " + energyPct + "%" : "READY TO SWING");
                }
            });
        });

        btnSwing.setOnClickListener(v -> fireSwing());
        if (btnCalibrate != null) {
            btnCalibrate.setOnClickListener(v -> {
                motionHelper.calibrate();
                txtSwingEnergy.setText("AIM RE-CENTERED");
            });
        }
    }

    private void fireSwing() {
        vibrate(60);
        txtSwingEnergy.setText("⚡ SMASH SWING! ⚡");
        wsManager.sendButton("a", true);
        btnSwing.postDelayed(() -> wsManager.sendButton("a", false), 80);
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
