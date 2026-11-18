package com.example.quickdrawcontroller;

import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.Bundle;
import android.view.MotionEvent;
import android.widget.Button;
import android.widget.ProgressBar;
import android.widget.TextView;

/**
 * RacingActivity: Steering wheel tilt & Gas/Brake pedals controller.
 */
public class RacingActivity extends BaseGameActivity implements SensorEventListener {

    private TextView txtSteerAngle;
    private TextView txtPlayerBadge;
    private ProgressBar barSteer;
    private Button btnGas;
    private Button btnBrake;

    private SensorManager sensorManager;
    private Sensor accelSensor;
    private long lastSendTime = 0;

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

        txtPlayerBadge.setText(wsManager.getPlayerRole().equalsIgnoreCase("player1") ? "P1" : "P2");
        txtPlayerBadge.setBackgroundColor(wsManager.getPlayerRole().equalsIgnoreCase("player1") ? 0xFF0077FF : 0xFFFF4400);

        sensorManager = (SensorManager) getSystemService(Context.SENSOR_SERVICE);
        if (sensorManager != null) {
            accelSensor = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
        }

        setupPedals();
    }

    private void setupPedals() {
        btnGas.setOnTouchListener((v, event) -> {
            if (event.getAction() == MotionEvent.ACTION_DOWN) {
                vibrate(15);
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

        btnBrake.setOnTouchListener((v, event) -> {
            if (event.getAction() == MotionEvent.ACTION_DOWN) {
                vibrate(15);
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
        if (sensorManager != null && accelSensor != null) {
            sensorManager.registerListener(this, accelSensor, SensorManager.SENSOR_DELAY_GAME);
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (sensorManager != null) {
            sensorManager.unregisterListener(this);
        }
    }

    @Override
    public void onSensorChanged(SensorEvent event) {
        if (event.sensor.getType() == Sensor.TYPE_ACCELEROMETER) {
            float ax = event.values[0];
            float ay = event.values[1];
            float az = event.values[2];

            // Calculate steering wheel angle from phone orientation
            double angleRad = Math.atan2(ax, -ay);
            int angleDeg = (int) Math.toDegrees(angleRad);
            int clamped = Math.max(-45, Math.min(45, angleDeg));
            int progress = (int) (((clamped + 45) / 90.0) * 100);

            barSteer.setProgress(progress);
            txtSteerAngle.setText(angleDeg >= 0 ? "STEER RIGHT: +" + angleDeg + "°" : "STEER LEFT: " + angleDeg + "°");

            long now = System.currentTimeMillis();
            if (now - lastSendTime >= 33) { // ~30 fps motion streaming
                lastSendTime = now;
                wsManager.sendMotion(new float[]{ax, ay, az}, new float[]{0, 0, 0}, new float[]{angleDeg, 0, 0});
            }
        }
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {}
}
