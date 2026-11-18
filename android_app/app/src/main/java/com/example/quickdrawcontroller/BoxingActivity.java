package com.example.quickdrawcontroller;

import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.Bundle;
import android.view.MotionEvent;
import android.widget.Button;
import android.widget.TextView;

/**
 * BoxingActivity: Punch motion detection & Guard block controller.
 */
public class BoxingActivity extends BaseGameActivity implements SensorEventListener {

    private TextView txtPlayerBadge;
    private Button btnPunch;
    private Button btnGuard;

    private SensorManager sensorManager;
    private Sensor accelSensor;
    private long lastPunchTime = 0;
    private long lastStreamTime = 0;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_boxing);

        setupHomeButton(R.id.btnHome);

        txtPlayerBadge = findViewById(R.id.txtPlayerBadge);
        btnPunch = findViewById(R.id.btnPunch);
        btnGuard = findViewById(R.id.btnGuard);

        txtPlayerBadge.setText(wsManager.getPlayerRole().equalsIgnoreCase("player1") ? "P1" : "P2");
        txtPlayerBadge.setBackgroundColor(wsManager.getPlayerRole().equalsIgnoreCase("player1") ? 0xFF0077FF : 0xFFFF4400);

        sensorManager = (SensorManager) getSystemService(Context.SENSOR_SERVICE);
        if (sensorManager != null) {
            accelSensor = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
        }

        btnPunch.setOnClickListener(v -> firePunch());

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

            long now = System.currentTimeMillis();

            // Detect forward punch thrust along Z or Y axis
            if ((Math.abs(az) > 18.0f || Math.abs(ay) > 18.0f) && (now - lastPunchTime > 400)) {
                lastPunchTime = now;
                firePunch();
            }

            if (now - lastStreamTime >= 33) {
                lastStreamTime = now;
                wsManager.sendMotion(new float[]{ax, ay, az}, new float[]{0, 0, 0}, new float[]{ax * 4, ay * 4, az * 4});
            }
        }
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {}
}
