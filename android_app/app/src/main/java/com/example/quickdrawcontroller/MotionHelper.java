package com.example.quickdrawcontroller;

import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.Build;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.util.Log;

import org.json.JSONObject;

/**
 * Universal Motion & Sensor Fusion Processor
 * Accurately translates Android hardware sensors into HTML5-compatible
 * motion packets:
 *   - ag: [ax, ay, az] in m/s^2 (accelerometer with gravity)
 *   - rr: [rz, rx, ry] in deg/s (gyroscope rotation rate: alpha(z), beta(x), gamma(y))
 *   - o:  [alpha, beta, gamma] in degrees (Euler orientation angles)
 *
 * Implements exponential moving average (EMA) smoothing for silky smooth cursor / reticle
 * movement, and dynamic zero-calibration for pitch, roll, and steering wheel angles.
 */
public class MotionHelper implements SensorEventListener {
    private static final String TAG = "MotionHelper";

    public interface MotionCallback {
        void onMotionUpdate(float[] ag, float[] rr, float[] ori, String statsText);
    }

    private final Context context;
    private final SensorManager sensorManager;
    private final Vibrator vibrator;
    private MotionCallback callback;

    private Sensor accelSensor;
    private Sensor gyroSensor;
    private Sensor rotationSensor;

    // Raw sensor values
    private final float[] rawAccel = new float[]{0, 0, 9.81f};
    private final float[] rawGyro = new float[]{0, 0, 0}; // rad/s from Android
    private final float[] rotationMatrix = new float[9];
    private final float[] orientationAngles = new float[3];

    // Orientation in degrees
    private float alphaDeg = 0f; // Compass / yaw (0..360)
    private float betaDeg = 0f;  // Pitch front/back (-180..180)
    private float gammaDeg = 0f; // Roll left/right (-90..90)

    // Smoothed values (exponential moving average for jitter-free aiming)
    private float smoothBeta = 0f;
    private float smoothGamma = 0f;
    private final float SMOOTH_FACTOR = 0.28f; // Fast, natural tracking without jitter

    // Calibration offsets
    private float calRoll = 0f;
    private float calPitch = 0f;

    private long lastStreamTime = 0;
    private static final long STREAM_INTERVAL_MS = 25; // ~40 FPS smooth streaming

    public MotionHelper(Context context) {
        this.context = context;
        this.sensorManager = (SensorManager) context.getSystemService(Context.SENSOR_SERVICE);
        this.vibrator = (Vibrator) context.getSystemService(Context.VIBRATOR_SERVICE);

        if (sensorManager != null) {
            accelSensor = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
            gyroSensor = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE);
            rotationSensor = sensorManager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR);
            if (rotationSensor == null) {
                rotationSensor = sensorManager.getDefaultSensor(Sensor.TYPE_GAME_ROTATION_VECTOR);
            }
        }
    }

    public void setCallback(MotionCallback cb) {
        this.callback = cb;
    }

    public void start() {
        if (sensorManager == null) return;
        if (accelSensor != null) {
            sensorManager.registerListener(this, accelSensor, SensorManager.SENSOR_DELAY_GAME);
        }
        if (gyroSensor != null) {
            sensorManager.registerListener(this, gyroSensor, SensorManager.SENSOR_DELAY_GAME);
        }
        if (rotationSensor != null) {
            sensorManager.registerListener(this, rotationSensor, SensorManager.SENSOR_DELAY_GAME);
        }
    }

    public void stop() {
        if (sensorManager != null) {
            sensorManager.unregisterListener(this);
        }
    }

    /**
     * Calibrate: zero out pitch and roll to the phone's current holding angle.
     * Also signals the laptop game to recalibrate its internal references.
     */
    public void calibrate() {
        calRoll = smoothGamma;
        calPitch = smoothBeta;

        // Send calibration command to laptop
        try {
            JSONObject cal = new JSONObject();
            cal.put("t", "cal");
            WebSocketManager.getInstance().send(cal);
        } catch (Exception ignored) {}

        // Haptic feedback
        vibrate(40);
        Log.d(TAG, "Calibrated to zero reference: Roll=" + calRoll + "°, Pitch=" + calPitch + "°");
    }

    private void vibrate(long ms) {
        if (vibrator == null) return;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            vibrator.vibrate(VibrationEffect.createOneShot(ms, VibrationEffect.DEFAULT_AMPLITUDE));
        } else {
            vibrator.vibrate(ms);
        }
    }

    @Override
    public void onSensorChanged(SensorEvent event) {
        int type = event.sensor.getType();

        if (type == Sensor.TYPE_ACCELEROMETER) {
            rawAccel[0] = event.values[0];
            rawAccel[1] = event.values[1];
            rawAccel[2] = event.values[2];

            // Fallback tilt calculation if device lacks hardware rotation vector
            if (rotationSensor == null) {
                float ax = rawAccel[0], ay = rawAccel[1], az = rawAccel[2];
                float pitch = (float) Math.toDegrees(Math.atan2(-ax, Math.hypot(ay, az)));
                float roll  = (float) Math.toDegrees(Math.atan2(ay, az));
                updateOrientation(0f, pitch, roll);
            }
        } else if (type == Sensor.TYPE_GYROSCOPE) {
            rawGyro[0] = event.values[0];
            rawGyro[1] = event.values[1];
            rawGyro[2] = event.values[2];
        } else if (type == Sensor.TYPE_ROTATION_VECTOR || type == Sensor.TYPE_GAME_ROTATION_VECTOR) {
            SensorManager.getRotationMatrixFromVector(rotationMatrix, event.values);
            SensorManager.getOrientation(rotationMatrix, orientationAngles);

            // Convert radians to degrees matching HTML5 deviceorientation:
            // orientationAngles[0] = azimuth / yaw (-PI to PI)
            // orientationAngles[1] = pitch (-PI to PI)
            // orientationAngles[2] = roll (-PI/2 to PI/2)
            float alpha = (float) Math.toDegrees(orientationAngles[0]);
            if (alpha < 0) alpha += 360f;
            float beta = (float) Math.toDegrees(orientationAngles[1]);
            float gamma = (float) Math.toDegrees(orientationAngles[2]);

            updateOrientation(alpha, beta, gamma);
        }

        long now = System.currentTimeMillis();
        if (now - lastStreamTime >= STREAM_INTERVAL_MS) {
            lastStreamTime = now;
            dispatchMotion();
        }
    }

    private void updateOrientation(float alpha, float beta, float gamma) {
        alphaDeg = alpha;
        betaDeg = beta;
        gammaDeg = gamma;

        // Exponential smoothing filter to eliminate hand micro-jitters
        smoothBeta = smoothBeta * (1f - SMOOTH_FACTOR) + betaDeg * SMOOTH_FACTOR;
        smoothGamma = smoothGamma * (1f - SMOOTH_FACTOR) + gammaDeg * SMOOTH_FACTOR;
    }

    private void dispatchMotion() {
        // Rotation rate in deg/s: [alpha(z), beta(x), gamma(y)]
        // Android returns rad/s [x, y, z] -> convert to deg/s
        float rz = (float) Math.toDegrees(rawGyro[2]); // alpha
        float rx = (float) Math.toDegrees(rawGyro[0]); // beta
        float ry = (float) Math.toDegrees(rawGyro[1]); // gamma
        float[] rr = new float[]{rz, rx, ry};

        // Orientation in degrees: [alpha, beta, gamma]
        float[] ori = new float[]{alphaDeg, smoothBeta, smoothGamma};

        // Acceleration in m/s^2: [ax, ay, az]
        float[] ag = new float[]{rawAccel[0], rawAccel[1], rawAccel[2]};

        // Stream over WebSocket
        WebSocketManager.getInstance().sendMotion(ag, rr, ori);

        // Notify UI callback
        if (callback != null) {
            float relRoll = smoothGamma - calRoll;
            float relPitch = smoothBeta - calPitch;
            String stats = String.format("AIM: [%+.1f°, %+.1f°] | TILT: %+.0f°", relRoll, relPitch, smoothGamma);
            callback.onMotionUpdate(ag, rr, ori, stats);
        }
    }

    public float getSmoothBeta() { return smoothBeta; }
    public float getSmoothGamma() { return smoothGamma; }
    public float[] getRawAccel() { return rawAccel; }
    public float[] getRawGyro() { return rawGyro; }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {}
}
