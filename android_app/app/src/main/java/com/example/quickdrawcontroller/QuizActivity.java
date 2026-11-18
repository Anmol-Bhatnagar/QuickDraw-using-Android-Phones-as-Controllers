package com.example.quickdrawcontroller;

import android.os.Bundle;
import android.widget.Button;
import android.widget.TextView;

import org.json.JSONObject;

/**
 * QuizActivity: 4-key trivia answer pad controller.
 */
public class QuizActivity extends BaseGameActivity {

    private TextView txtQuizStatus;
    private TextView txtPlayerBadge;
    private Button ansA;
    private Button ansB;
    private Button ansC;
    private Button ansD;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_quiz);

        setupHomeButton(R.id.btnHome);

        txtQuizStatus = findViewById(R.id.txtQuizStatus);
        txtPlayerBadge = findViewById(R.id.txtPlayerBadge);
        ansA = findViewById(R.id.ansA);
        ansB = findViewById(R.id.ansB);
        ansC = findViewById(R.id.ansC);
        ansD = findViewById(R.id.ansD);

        txtPlayerBadge.setText(wsManager.getPlayerRole().equalsIgnoreCase("player1") ? "P1" : "P2");
        txtPlayerBadge.setBackgroundColor(wsManager.getPlayerRole().equalsIgnoreCase("player1") ? 0xFF0077FF : 0xFFFF4400);

        ansA.setOnClickListener(v -> submitAnswer("q1", "A"));
        ansB.setOnClickListener(v -> submitAnswer("q2", "B"));
        ansC.setOnClickListener(v -> submitAnswer("q3", "C"));
        ansD.setOnClickListener(v -> submitAnswer("q4", "D"));
    }

    private void submitAnswer(String key, String label) {
        vibrate(40);
        txtQuizStatus.setText("LOCKED IN: CHOICE [" + label + "]");
        txtQuizStatus.setTextColor(0xFF00FF88);

        wsManager.sendButton(key, true);
        ansA.postDelayed(() -> wsManager.sendButton(key, false), 80);
    }

    @Override
    public void onMessage(JSONObject data) {
        super.onMessage(data);

        String kind = data.optString("t");
        if ("hud".equals(kind)) {
            boolean lock = data.optBoolean("lock", false);
            if (lock) {
                txtQuizStatus.setText("ANSWER LOCKED!");
            } else {
                txtQuizStatus.setText("LOCK IN YOUR ANSWER!");
                txtQuizStatus.setTextColor(0xFFFFD166);
            }
            String hint = data.optString("hint", "");
            if (!hint.isEmpty()) {
                txtQuizStatus.setText(hint);
            }
        }
    }
}
