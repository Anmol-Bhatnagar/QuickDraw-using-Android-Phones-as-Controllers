package com.example.quickdrawcontroller;

import android.os.Bundle;
import android.view.MotionEvent;
import android.widget.Button;
import android.widget.ProgressBar;
import android.widget.TextView;

/**
 * RacingActivity: Steering wheel & gas/brake pedals controller.
 * Uses MotionHelper for gravity-projected steering & smooth responsive handling.
 */
public class RacingActivity extends BaseGameActivity {

    private TextView txtSteerAngle;
    private TextView txtPlayerBadge;
    private ProgressBar barSteer;
    private Button btnGas;
    private Button btnBrake;
    private Button btnCalibrate;

    private MotionHelper motionHelper;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_racing);

        setupHomeButton(R.id.btnHome);

        txtSteerAngle = findViewById(R.id.txtSteerAngle);
        txtPlayerBadge = findViewById(R.id.txtPlayerBadge);
        barSteer = findViewById(R.id.barSteer);
        btnGas = findViewById(R.id.btnGas);
        btnBrake = findViewById(R.id.btnBrake);
        btnCalibrate = findViewById(R.id.btnCalibrate);

        txtPlayerBadge.setText(wsManager.getPlayerRole().equalsIgnoreCase("player1") ? "P1" : "P2");
        txtPlayerBadge.setBackgroundColor(wsManager.getPlayerRole().equalsIgnoreCase("player1") ? 0xFF0077FF : 0xFFFF4400);

        motionHelper = new MotionHelper(this);
        motionHelper.setCallback((ag, rr, ori, statsText) -> {
            // Steering wheel angle: phone held sideways or upright, rotation in X-Y plane
            float ax = ag[0], ay = ag[1];
            double angleRad = Math.atan2(ax, -ay);
            int angleDeg = (int) Math.toDegrees(angleRad);
            int clamped = Math.max(-55, Math.min(55, angleDeg));
            int progress = (int) (((clamped + 55) / 110.0) * 100);

            runOnUiThread(() -> {
                barSteer.setProgress(progress);
                if (Math.abs(angleDeg) < 3) {
                    txtSteerAngle.setText("CENTER: 0°");
                } else {
                    txtSteerAngle.setText(angleDeg >= 0 ? "STEER RIGHT: +" + angleDeg + "°" : "STEER LEFT: " + angleDeg + "°");
                }
            });
        });

        if (btnCalibrate != null) {
            btnCalibrate.setOnClickListener(v -> {
                motionHelper.calibrate();
                txtSteerAngle.setText("STEERING CENTERED");
            });
        }

        // Gas Pedal (hold to accelerate)
        btnGas.setOnTouchListener((v, event) -> {
            if (event.getAction() == MotionEvent.ACTION_DOWN) {
                vibrate(20);
                wsManager.sendButton("gas", true);
                btnGas.setAlpha(0.7f);
                return true;
            } else if (event.getAction() == MotionEvent.ACTION_UP || event.getAction() == MotionEvent.ACTION_CANCEL) {
                wsManager.sendButton("gas", false);
                btnGas.setAlpha(1.0f);
                return true;
            }
            return false;
        });

        // Brake Pedal (hold to brake/reverse)
        btnBrake.setOnTouchListener((v, event) -> {
            if (event.getAction() == MotionEvent.ACTION_DOWN) {
                vibrate(25);
                wsManager.sendButton("brake", true);
                btnBrake.setAlpha(0.7f);
                return true;
            } else if (event.getAction() == MotionEvent.ACTION_UP || event.getAction() == MotionEvent.ACTION_CANCEL) {
                wsManager.sendButton("brake", false);
                btnBrake.setAlpha(1.0f);
                return true;
            }
            return false;
        });
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
