package com.example.quickdrawcontroller;

import android.os.Bundle;
import android.view.MotionEvent;
import android.widget.Button;
import android.widget.TextView;

/**
 * BoxingActivity: Punch motion detection & Guard block controller.
 * Uses MotionHelper for fused dodge/lean orientation & forward thrust detection.
 */
public class BoxingActivity extends BaseGameActivity {

    private TextView txtPlayerBadge;
    private Button btnPunch;
    private Button btnGuard;
    private Button btnCalibrate;

    private MotionHelper motionHelper;
    private long lastPunchTime = 0;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_boxing);

        setupHomeButton(R.id.btnHome);

        txtPlayerBadge = findViewById(R.id.txtPlayerBadge);
        btnPunch = findViewById(R.id.btnPunch);
        btnGuard = findViewById(R.id.btnGuard);
        btnCalibrate = findViewById(R.id.btnCalibrate);

        txtPlayerBadge.setText(wsManager.getPlayerRole().equalsIgnoreCase("player1") ? "P1" : "P2");
        txtPlayerBadge.setBackgroundColor(wsManager.getPlayerRole().equalsIgnoreCase("player1") ? 0xFF0077FF : 0xFFFF4400);

        motionHelper = new MotionHelper(this);
        motionHelper.setCallback((ag, rr, ori, statsText) -> {
            float ax = ag[0], ay = ag[1], az = ag[2];
            long now = System.currentTimeMillis();

            // Detect forward punch thrust along Z or Y axis
            if ((Math.abs(az) > 18.0f || Math.abs(ay) > 18.0f) && (now - lastPunchTime > 400)) {
                lastPunchTime = now;
                runOnUiThread(this::firePunch);
            }
        });

        btnPunch.setOnClickListener(v -> firePunch());

        if (btnCalibrate != null) {
            btnCalibrate.setOnClickListener(v -> {
                motionHelper.calibrate();
            });
        }

        btnGuard.setOnTouchListener((v, event) -> {
            if (event.getAction() == MotionEvent.ACTION_DOWN) {
                vibrate(20);
                wsManager.sendButton("b", true);
                btnGuard.setAlpha(0.7f);
                return true;
            } else if (event.getAction() == MotionEvent.ACTION_UP || event.getAction() == MotionEvent.ACTION_CANCEL) {
                wsManager.sendButton("b", false);
                btnGuard.setAlpha(1.0f);
                return true;
            }
            return false;
        });
    }

    private void firePunch() {
        vibrate(80);
        wsManager.sendButton("a", true);
        btnPunch.postDelayed(() -> wsManager.sendButton("a", false), 80);
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
