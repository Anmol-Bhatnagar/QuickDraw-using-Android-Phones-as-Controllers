package com.example.quickdrawcontroller;

import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.Bundle;
import android.widget.Button;
import android.widget.ProgressBar;
import android.widget.TextView;

/**
 * TennisActivity: Real-time swing detection racquet controller.
 */
public class TennisActivity extends BaseGameActivity implements SensorEventListener {

    private TextView txtSwingEnergy;
    private TextView txtPlayerBadge;
    private ProgressBar barEnergy;
    private Button btnSwing;

    private SensorManager sensorManager;
    private Sensor accelSensor;
    private Sensor gyroSensor;
    private long lastSwingTime = 0;
    private long lastStreamTime = 0;
    private float[] lastGyro = new float[]{0, 0, 0};

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_tennis);

        setupHomeButton(R.id.btnHome);

        txtSwingEnergy = findViewById(R.id.txtSwingEnergy);
        txtPlayerBadge = findViewById(R.id.txtPlayerBadge);
        barEnergy = findViewById(R.id.barEnergy);
        btnSwing = findViewById(R.id.btnSwing);

        txtPlayerBadge.setText(wsManager.getPlayerRole().equalsIgnoreCase("player1") ? "P1" : "P2");
        txtPlayerBadge.setBackgroundColor(wsManager.getPlayerRole().equalsIgnoreCase("player1") ? 0xFF0077FF : 0xFFFF4400);

        sensorManager = (SensorManager) getSystemService(Context.SENSOR_SERVICE);
        if (sensorManager != null) {
            accelSensor = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
            gyroSensor = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE);
        }

        btnSwing.setOnClickListener(v -> fireSwing());
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
        if (sensorManager != null) {
            if (accelSensor != null) sensorManager.registerListener(this, accelSensor, SensorManager.SENSOR_DELAY_GAME);
            if (gyroSensor != null) sensorManager.registerListener(this, gyroSensor, SensorManager.SENSOR_DELAY_GAME);
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (sensorManager != null) sensorManager.unregisterListener(this);
    }

    @Override
    public void onSensorChanged(SensorEvent event) {
        if (event.sensor.getType() == Sensor.TYPE_GYROSCOPE) {
            lastGyro[0] = event.values[0];
            lastGyro[1] = event.values[1];
            lastGyro[2] = event.values[2];
        } else if (event.sensor.getType() == Sensor.TYPE_ACCELEROMETER) {
            float ax = event.values[0];
            float ay = event.values[1];
            float az = event.values[2];

            double mag = Math.sqrt(ax * ax + ay * ay + az * az);
            double dynamicMag = Math.max(0, mag - 9.8);
            int energyPct = (int) Math.min(100, (dynamicMag / 25.0) * 100);

            barEnergy.setProgress(energyPct);

            long now = System.currentTimeMillis();

            // Swing Threshold detection
            if (dynamicMag > 16.0 && (now - lastSwingTime > 400)) {
                lastSwingTime = now;
                fireSwing();
            } else if (now - lastSwingTime > 500) {
                txtSwingEnergy.setText(energyPct > 20 ? "ENERGY: " + energyPct + "%" : "READY TO SWING");
            }

            if (now - lastStreamTime >= 33) {
                lastStreamTime = now;
                wsManager.sendMotion(new float[]{ax, ay, az}, lastGyro, new float[]{ax * 4, ay * 4, 0});
            }
        }
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {}
}
