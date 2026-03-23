package com.valhalla.companion;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.util.Locale;

/**
 * 🦊 Translate with Ember — Android Overlay Activity
 *
 * Shows a translucent popup over WhatsApp/Messages when text is shared.
 * Translates inline (PC first → Google fallback) and copies to clipboard.
 * The user never fully leaves their messaging app.
 *
 * Registered in AndroidManifest.xml as the handler for ACTION_SEND text/plain.
 * Uses Theme.Translucent so the calling app is visible behind.
 */
public class TranslateOverlayActivity extends Activity {

    private TextView resultView;
    private TextView statusView;
    private Button copyBtn;
    private ProgressBar spinner;
    private String translatedText = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Make the activity translucent (overlay mode)
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setBackgroundDrawableResource(android.R.color.transparent);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_DIM_BEHIND);
        getWindow().setDimAmount(0.5f);

        // Get shared text
        String sharedText = "";
        Intent intent = getIntent();
        if (Intent.ACTION_SEND.equals(intent.getAction()) && "text/plain".equals(intent.getType())) {
            sharedText = intent.getStringExtra(Intent.EXTRA_TEXT);
        }

        if (sharedText == null || sharedText.trim().isEmpty()) {
            finish();
            return;
        }

        buildUI(sharedText);
        translate(sharedText);
    }

    private void buildUI(String sourceText) {
        int bgColor = Color.parseColor("#0F0F17");
        int cardColor = Color.parseColor("#1A1A24");
        int accentColor = Color.parseColor("#E8712C");
        int textColor = Color.parseColor("#FFFFFF");
        int dimColor = Color.parseColor("#888888");

        // Root container with rounded corners
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.BOTTOM);
        root.setLayoutParams(new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.MATCH_PARENT
        ));

        // Card
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(20), dp(20), dp(20), dp(30));

        GradientDrawable cardBg = new GradientDrawable();
        cardBg.setColor(bgColor);
        cardBg.setCornerRadii(new float[]{dp(20), dp(20), dp(20), dp(20), 0, 0, 0, 0});
        card.setBackground(cardBg);

        // Header: 🦊 Translate with Ember    ✕
        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);

        TextView icon = new TextView(this);
        icon.setText("🦊");
        icon.setTextSize(TypedValue.COMPLEX_UNIT_SP, 22);
        icon.setPadding(0, 0, dp(8), 0);

        TextView title = new TextView(this);
        title.setText("Translate with Ember");
        title.setTextColor(textColor);
        title.setTextSize(TypedValue.COMPLEX_UNIT_SP, 17);

        // Spacer
        View spacer = new View(this);
        spacer.setLayoutParams(new LinearLayout.LayoutParams(0, 0, 1f));

        TextView close = new TextView(this);
        close.setText("✕");
        close.setTextColor(dimColor);
        close.setTextSize(TypedValue.COMPLEX_UNIT_SP, 20);
        close.setPadding(dp(12), dp(4), dp(4), dp(4));
        close.setOnClickListener(v -> finish());

        header.addView(icon);
        header.addView(title);
        header.addView(spacer);
        header.addView(close);
        card.addView(header);

        // Source label
        TextView sourceLabel = new TextView(this);
        sourceLabel.setText("Source");
        sourceLabel.setTextColor(dimColor);
        sourceLabel.setTextSize(TypedValue.COMPLEX_UNIT_SP, 11);
        sourceLabel.setPadding(0, dp(12), 0, dp(4));
        card.addView(sourceLabel);

        // Source text
        TextView sourceView = new TextView(this);
        sourceView.setText(sourceText.length() > 200 ? sourceText.substring(0, 200) + "..." : sourceText);
        sourceView.setTextColor(Color.parseColor("#AAAAAA"));
        sourceView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13);
        sourceView.setPadding(dp(12), dp(10), dp(12), dp(10));
        sourceView.setMaxLines(3);

        GradientDrawable sourceBg = new GradientDrawable();
        sourceBg.setColor(cardColor);
        sourceBg.setCornerRadius(dp(10));
        sourceView.setBackground(sourceBg);
        card.addView(sourceView);

        // Status row (spinner + label)
        LinearLayout statusRow = new LinearLayout(this);
        statusRow.setOrientation(LinearLayout.HORIZONTAL);
        statusRow.setGravity(Gravity.CENTER_VERTICAL);
        statusRow.setPadding(0, dp(12), 0, dp(4));

        spinner = new ProgressBar(this, null, android.R.attr.progressBarStyleSmall);
        spinner.setPadding(0, 0, dp(8), 0);

        statusView = new TextView(this);
        statusView.setText("Translating...");
        statusView.setTextColor(accentColor);
        statusView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13);

        statusRow.addView(spinner);
        statusRow.addView(statusView);
        card.addView(statusRow);

        // Result text
        resultView = new TextView(this);
        resultView.setTextColor(textColor);
        resultView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16);
        resultView.setPadding(dp(14), dp(14), dp(14), dp(14));
        resultView.setVisibility(View.GONE);
        resultView.setTextIsSelectable(true);

        GradientDrawable resultBg = new GradientDrawable();
        resultBg.setColor(Color.parseColor("#1A120A"));
        resultBg.setCornerRadius(dp(10));
        resultBg.setStroke(1, Color.parseColor("#4DE8712C"));
        resultView.setBackground(resultBg);
        card.addView(resultView);

        // Copy button
        copyBtn = new Button(this);
        copyBtn.setText("📋  Copy Translation");
        copyBtn.setTextColor(bgColor);
        copyBtn.setTextSize(TypedValue.COMPLEX_UNIT_SP, 15);
        copyBtn.setAllCaps(false);
        copyBtn.setVisibility(View.GONE);

        GradientDrawable btnBg = new GradientDrawable();
        btnBg.setColor(accentColor);
        btnBg.setCornerRadius(dp(12));
        copyBtn.setBackground(btnBg);
        copyBtn.setPadding(0, dp(14), 0, dp(14));

        LinearLayout.LayoutParams btnParams = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, dp(48)
        );
        btnParams.setMargins(0, dp(12), 0, 0);
        copyBtn.setLayoutParams(btnParams);

        copyBtn.setOnClickListener(v -> {
            ClipboardManager clipboard = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
            clipboard.setPrimaryClip(ClipData.newPlainText("translation", translatedText));
            copyBtn.setText("✅  Copied!");
            copyBtn.postDelayed(this::finish, 800);
        });
        card.addView(copyBtn);

        root.addView(card);
        setContentView(root);

        // Tap outside card to close
        root.setOnClickListener(v -> finish());
        card.setOnClickListener(v -> {}); // prevent close propagation
    }

    private void translate(String text) {
        new Thread(() -> {
            // Try Google Translate (most reliable when away from home)
            String deviceLang = Locale.getDefault().getLanguage();
            String targetLang = "en".equals(deviceLang) ? "es" : deviceLang;

            try {
                String encoded = URLEncoder.encode(text, "UTF-8");
                String urlStr = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl="
                    + targetLang + "&dt=t&q=" + encoded;

                HttpURLConnection conn = (HttpURLConnection) new URL(urlStr).openConnection();
                conn.setConnectTimeout(8000);
                conn.setReadTimeout(8000);

                BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) sb.append(line);
                reader.close();

                JSONArray json = new JSONArray(sb.toString());
                JSONArray segments = json.getJSONArray(0);
                StringBuilder result = new StringBuilder();
                for (int i = 0; i < segments.length(); i++) {
                    result.append(segments.getJSONArray(i).getString(0));
                }

                String detected = json.optString(2, "auto");
                final String translated = result.toString().trim();

                if (!translated.isEmpty()) {
                    runOnUiThread(() -> showResult(translated, "☁️ Google Translate", detected + " → " + targetLang));
                    return;
                }
            } catch (Exception e) {
                // Fall through
            }

            runOnUiThread(() -> showError("Translation failed — check internet"));
        }).start();
    }

    private void showResult(String text, String source, String langPair) {
        translatedText = text;
        spinner.setVisibility(View.GONE);
        statusView.setText(source + "  •  " + langPair);
        statusView.setTextColor(source.contains("Home") ?
            Color.parseColor("#22C55E") : Color.parseColor("#F59E0B"));
        resultView.setText(text);
        resultView.setVisibility(View.VISIBLE);
        copyBtn.setVisibility(View.VISIBLE);
    }

    private void showError(String msg) {
        spinner.setVisibility(View.GONE);
        statusView.setText(msg);
        statusView.setTextColor(Color.parseColor("#EF4444"));
    }

    private int dp(int value) {
        return (int) TypedValue.applyDimension(
            TypedValue.COMPLEX_UNIT_DIP, value, getResources().getDisplayMetrics()
        );
    }
}
