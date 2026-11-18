package com.example.quickdrawcontroller;

import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.Bundle;
import android.widget.Button;
import android.widget.TextView;

/**
 * SportsActivity: Universal sensor & action controller for sports games
 * (Bowling, Basketball, Golf, Baseball, Ducks, Darts, Cup Pong, Billiards, Tanks, etc.).
 */
public class SportsActivity extends BaseGameActivity implements SensorEventListener {

    private TextView txtSportTitle;
    private TextView txtSportHint;
    private TextView txtSensorStats;
    private TextView txtPlayerBadge;
    private Button btnAction;
    private Button btnCalibrate;

    private SensorManager sensorManager;
    private Sensor accelSensor;
    private Sensor gyroSensor;
    private long lastStreamTime = 0;
    private float[] lastGyro = new float[]{0, 0, 0};

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

        sensorManager = (SensorManager) getSystemService(Context.SENSOR_SERVICE);
        if (sensorManager != null) {
            accelSensor = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
            gyroSensor = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE);
        }

        btnAction.setOnClickListener(v -> fireAction());

        btnCalibrate.setOnClickListener(v -> {
            vibrate(30);
            try {
                org.json.JSONObject cal = new org.json.JSONObject();
                cal.put("t", "cal");
                wsManager.send(cal);
            } catch (Exception ignored) {}
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
        if (sensorManager != null) {
            if (accelSensor != null) sensorManager.registerListener(this, accelSensor, SensorManager.SENSOR_DELAY_GAME);
            if (gyroSensor != null) sensorManager.registerListener(this, gyroSensor, SensorManager.SENSOR_DELAY_GAME);
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
        if (event.sensor.getType() == Sensor.TYPE_GYROSCOPE) {
            lastGyro[0] = event.values[0];
            lastGyro[1] = event.values[1];
            lastGyro[2] = event.values[2];
        } else if (event.sensor.getType() == Sensor.TYPE_ACCELEROMETER) {
            float ax = event.values[0];
            float ay = event.values[1];
            float az = event.values[2];

            long now = System.currentTimeMillis();
            if (now - lastStreamTime >= 33) {
                lastStreamTime = now;
                txtSensorStats.setText(String.format("ACCEL: [%.1f, %.1f, %.1f]", ax, ay, az));
                wsManager.sendMotion(new float[]{ax, ay, az}, lastGyro, new float[]{ax * 4, ay * 4, az * 4});
            }
        }
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {}
}
