package com.valhalla.companion;

import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.inputmethodservice.InputMethodService;
import android.os.Handler;
import android.os.Looper;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.text.InputType;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.HapticFeedbackConstants;
import android.view.MotionEvent;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.Space;
import android.widget.TextView;

import org.json.JSONArray;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Timer;
import java.util.TimerTask;
import java.util.regex.Pattern;

/**
 * 🛡️ Guardian Keyboard — Android Custom IME
 *
 * InputMethodService providing a full QWERTY keyboard with:
 *   1. Guardian — real-time message risk analysis with warning bar
 *   2. Translate — globe button translates text via LAN NLLB-200 or Google fallback
 *
 * Port of guardian.py heuristics to Java. All UI is programmatic (no XML layouts).
 * Design matches Fireside brand: dark charcoal, fire-orange accents.
 */
public class FiresideKeyboardService extends InputMethodService {

    // ── Brand Colors ──
    private static final int BG_COLOR     = Color.parseColor("#0F0F17");
    private static final int KEY_COLOR    = Color.parseColor("#2A2A3A");
    private static final int KEY_PRESSED  = Color.parseColor("#3D3D52");
    private static final int TEXT_COLOR   = Color.parseColor("#FFFFFF");
    private static final int DIM_TEXT     = Color.parseColor("#80FFFFFF");
    private static final int ACCENT       = Color.parseColor("#E8712C");
    private static final int DANGER       = Color.parseColor("#FF4466");
    private static final int SUCCESS      = Color.parseColor("#22C55E");
    private static final int WARNING_AMB  = Color.parseColor("#F59E0B");

    // ── Key Layouts ──
    private static final String[][] LETTER_ROWS = {
        {"Q","W","E","R","T","Y","U","I","O","P"},
        {"A","S","D","F","G","H","J","K","L"},
        {"Z","X","C","V","B","N","M"}
    };
    private static final String[][] NUMBER_ROWS = {
        {"1","2","3","4","5","6","7","8","9","0"},
        {"-","/",":",";","(",")","$","&","@","\""},
        {".",",","?","!","'"}
    };
    private static final String[][] SYMBOL_ROWS = {
        {"[","]","{","}","#","%","^","*","+","="},
        {"_","\\","|","~","<",">","€","£","¥","•"},
        {".",",","?","!","'"}
    };

    // ── Guardian Heuristics ──
    private static final String[] ANGRY_WORDS = {
        "fuck","shit","damn","hell","hate","stupid","idiot","moron",
        "furious","pissed","angry","rage","screw","bastard",
        "wtf","stfu","terrible","worst","disgusting","pathetic"
    };
    private static final String[] SAD_WORDS = {
        "sorry","sad","miss","lonely","hurt","crying","depressed",
        "wish","regret","heartbroken","lost","empty","alone"
    };
    private static final String[] HAPPY_WORDS = {
        "love","amazing","wonderful","great","happy","excited",
        "awesome","beautiful","perfect","best","brilliant","fantastic"
    };
    private static final String[] PROFANITY = {
        "fuck","shit","damn","hell","ass","bitch","bastard","crap"
    };
    private static final String[] EX_PATTERNS = {
        "\\bex\\b","\\bex-","ex girlfriend","ex boyfriend",
        "ex wife","ex husband","my ex","old flame","former partner"
    };
    private static final String[] REPLY_ALL_PATTERNS = {
        "reply.?all","@everyone","@all","@channel","@here",
        "all hands","entire team"
    };
    private static final String[][] SOFTENERS = {
        {"\\byou always\\b", "it sometimes feels like"},
        {"\\byou never\\b", "I wish"},
        {"\\byou're wrong\\b", "I see it differently"},
        {"\\bthat's stupid\\b", "I'm not sure about that approach"},
        {"\\bI hate\\b", "I'm frustrated with"},
        {"\\bshut up\\b", "let me finish"},
        {"\\bwhatever\\b", "I need a moment"},
        {"\\bI don't care\\b", "I need to think about this"},
        {"\\bleave me alone\\b", "I need some space right now"},
    };

    // ── State ──
    private boolean isShifted = false;
    private boolean isCaps = false;
    private boolean isNumberMode = false;
    private boolean isSymbolMode = false;
    private Timer guardianTimer;
    private Handler mainHandler = new Handler(Looper.getMainLooper());
    private String currentSofterVersion = "";

    // ── UI References ──
    private LinearLayout rootLayout;
    private LinearLayout guardianBar;
    private TextView guardianLabel;
    private LinearLayout keyRowsContainer;
    private Button spaceButton;
    private Button modeButton;

    @Override
    public View onCreateInputView() {
        rootLayout = new LinearLayout(this);
        rootLayout.setOrientation(LinearLayout.VERTICAL);
        rootLayout.setBackgroundColor(BG_COLOR);
        rootLayout.setPadding(0, dp(2), 0, dp(4));

        // Guardian warning bar (hidden initially)
        buildGuardianBar();

        // Key rows container
        keyRowsContainer = new LinearLayout(this);
        keyRowsContainer.setOrientation(LinearLayout.VERTICAL);
        rootLayout.addView(keyRowsContainer);

        buildKeyRows(LETTER_ROWS, true);

        // Bottom toolbar
        buildToolbar();

        // Start guardian monitoring
        startGuardianMonitoring();

        return rootLayout;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        if (guardianTimer != null) {
            guardianTimer.cancel();
        }
    }

    // ══════════════════════════════════════════
    // Guardian Warning Bar
    // ══════════════════════════════════════════

    private void buildGuardianBar() {
        guardianBar = new LinearLayout(this);
        guardianBar.setOrientation(LinearLayout.HORIZONTAL);
        guardianBar.setGravity(Gravity.CENTER_VERTICAL);
        guardianBar.setPadding(dp(12), dp(8), dp(10), dp(8));
        guardianBar.setVisibility(View.GONE);

        // Gradient background
        GradientDrawable gradient = new GradientDrawable(
            GradientDrawable.Orientation.LEFT_RIGHT,
            new int[]{DANGER, ACCENT}
        );
        gradient.setCornerRadius(dp(10));

        LinearLayout barInner = new LinearLayout(this);
        barInner.setOrientation(LinearLayout.HORIZONTAL);
        barInner.setGravity(Gravity.CENTER_VERTICAL);
        barInner.setBackground(gradient);
        barInner.setPadding(dp(10), dp(8), dp(10), dp(8));

        // Companion emoji
        TextView emoji = new TextView(this);
        emoji.setText(companionEmoji());
        emoji.setTextSize(TypedValue.COMPLEX_UNIT_SP, 24);
        emoji.setPadding(0, 0, dp(8), 0);
        barInner.addView(emoji);

        // Warning text column
        LinearLayout textCol = new LinearLayout(this);
        textCol.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams textParams = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        textCol.setLayoutParams(textParams);

        TextView header = new TextView(this);
        header.setText(companionEmoji() + " " + companionName() + " says:");
        header.setTextColor(Color.parseColor("#E6FFFFFF"));
        header.setTextSize(TypedValue.COMPLEX_UNIT_SP, 10);

        guardianLabel = new TextView(this);
        guardianLabel.setText("");
        guardianLabel.setTextColor(TEXT_COLOR);
        guardianLabel.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
        guardianLabel.setMaxLines(2);

        textCol.addView(header);
        textCol.addView(guardianLabel);
        barInner.addView(textCol);

        // Softer button
        Button softerBtn = makePillButton("Softer ✨", Color.parseColor("#40FFFFFF"));
        softerBtn.setOnClickListener(v -> softerTapped());
        barInner.addView(softerBtn);

        // Ignore button
        Button ignoreBtn = makePillButton("Ignore", Color.parseColor("#26FFFFFF"));
        ignoreBtn.setOnClickListener(v -> ignoreTapped());
        LinearLayout.LayoutParams ignoreParams = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        ignoreParams.setMargins(dp(4), 0, 0, 0);
        ignoreBtn.setLayoutParams(ignoreParams);
        barInner.addView(ignoreBtn);

        // Wrap with margins
        LinearLayout.LayoutParams barParams = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        barParams.setMargins(dp(6), dp(2), dp(6), dp(4));
        barInner.setLayoutParams(barParams);

        guardianBar.addView(barInner);

        LinearLayout.LayoutParams guardianParams = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        rootLayout.addView(guardianBar, guardianParams);
    }

    private Button makePillButton(String text, int bgColor) {
        Button btn = new Button(this);
        btn.setText(text);
        btn.setTextColor(TEXT_COLOR);
        btn.setTextSize(TypedValue.COMPLEX_UNIT_SP, 10);
        btn.setAllCaps(false);
        btn.setPadding(dp(10), dp(4), dp(10), dp(4));

        GradientDrawable bg = new GradientDrawable();
        bg.setColor(bgColor);
        bg.setCornerRadius(dp(12));
        btn.setBackground(bg);
        btn.setMinHeight(0);
        btn.setMinimumHeight(0);

        return btn;
    }

    // ══════════════════════════════════════════
    // Key Rows
    // ══════════════════════════════════════════

    private void buildKeyRows(String[][] rows, boolean showShift) {
        keyRowsContainer.removeAllViews();

        for (int rowIndex = 0; rowIndex < rows.length; rowIndex++) {
            LinearLayout rowLayout = new LinearLayout(this);
            rowLayout.setOrientation(LinearLayout.HORIZONTAL);
            rowLayout.setGravity(Gravity.CENTER);
            rowLayout.setPadding(dp(2), dp(2), dp(2), dp(2));

            String[] row = rows[rowIndex];

            // Shift / Symbol toggle on bottom letter row
            if (rowIndex == 2 && showShift) {
                Button shiftBtn = makeSpecialKey("⬆");
                shiftBtn.setOnClickListener(v -> shiftTapped());
                shiftBtn.setOnLongClickListener(v -> { capsLockTapped(); return true; });
                LinearLayout.LayoutParams shiftParams = new LinearLayout.LayoutParams(dp(42), dp(42));
                shiftParams.setMargins(dp(2), 0, dp(4), 0);
                rowLayout.addView(shiftBtn, shiftParams);
            } else if (rowIndex == 2 && !showShift) {
                Button symBtn = makeSpecialKey(isSymbolMode ? "123" : "#+=");
                symBtn.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
                symBtn.setOnClickListener(v -> symbolToggleTapped());
                LinearLayout.LayoutParams symParams = new LinearLayout.LayoutParams(dp(42), dp(42));
                symParams.setMargins(dp(2), 0, dp(4), 0);
                rowLayout.addView(symBtn, symParams);
            }

            // Letter keys
            for (String key : row) {
                Button keyBtn = makeKeyButton(key);
                final String k = key;
                keyBtn.setOnClickListener(v -> letterTapped(k));
                LinearLayout.LayoutParams keyParams = new LinearLayout.LayoutParams(0, dp(42), 1f);
                keyParams.setMargins(dp(2), 0, dp(2), 0);
                rowLayout.addView(keyBtn, keyParams);
            }

            // Backspace on bottom row
            if (rowIndex == 2) {
                Button backBtn = makeSpecialKey("⌫");
                backBtn.setOnClickListener(v -> backspaceTapped());
                backBtn.setOnLongClickListener(v -> { backspaceLongPress(); return true; });
                LinearLayout.LayoutParams backParams = new LinearLayout.LayoutParams(dp(42), dp(42));
                backParams.setMargins(dp(4), 0, dp(2), 0);
                rowLayout.addView(backBtn, backParams);
            }

            keyRowsContainer.addView(rowLayout);
        }
    }

    private Button makeKeyButton(String label) {
        Button btn = new Button(this);
        String display = (isShifted || isCaps) ? label.toUpperCase() : label.toLowerCase();
        btn.setText(display);
        btn.setTextColor(TEXT_COLOR);
        btn.setTextSize(TypedValue.COMPLEX_UNIT_SP, 18);
        btn.setAllCaps(false);
        btn.setPadding(0, 0, 0, 0);

        GradientDrawable bg = new GradientDrawable();
        bg.setColor(KEY_COLOR);
        bg.setCornerRadius(dp(6));
        btn.setBackground(bg);

        btn.setOnTouchListener((v, event) -> {
            if (event.getAction() == MotionEvent.ACTION_DOWN) {
                ((GradientDrawable) v.getBackground()).setColor(KEY_PRESSED);
            } else if (event.getAction() == MotionEvent.ACTION_UP || event.getAction() == MotionEvent.ACTION_CANCEL) {
                ((GradientDrawable) v.getBackground()).setColor(KEY_COLOR);
            }
            return false;
        });

        return btn;
    }

    private Button makeSpecialKey(String label) {
        Button btn = new Button(this);
        btn.setText(label);
        btn.setTextColor(TEXT_COLOR);
        btn.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16);
        btn.setAllCaps(false);
        btn.setMinHeight(0);
        btn.setMinimumHeight(0);
        btn.setPadding(0, 0, 0, 0);

        GradientDrawable bg = new GradientDrawable();
        bg.setColor(Color.parseColor("#333333"));
        bg.setCornerRadius(dp(6));
        btn.setBackground(bg);

        return btn;
    }

    // ══════════════════════════════════════════
    // Bottom Toolbar
    // ══════════════════════════════════════════

    private void buildToolbar() {
        LinearLayout toolbar = new LinearLayout(this);
        toolbar.setOrientation(LinearLayout.HORIZONTAL);
        toolbar.setGravity(Gravity.CENTER_VERTICAL);
        toolbar.setPadding(dp(4), dp(3), dp(4), dp(2));

        // Translate button (globe)
        Button translateBtn = new Button(this);
        translateBtn.setText("🌐");
        translateBtn.setTextSize(TypedValue.COMPLEX_UNIT_SP, 20);
        translateBtn.setBackground(null);
        translateBtn.setPadding(dp(8), 0, dp(8), 0);
        translateBtn.setOnClickListener(v -> translateTapped());
        LinearLayout.LayoutParams transParams = new LinearLayout.LayoutParams(dp(44), dp(42));
        toolbar.addView(translateBtn, transParams);

        // Mode toggle (123/ABC)
        modeButton = makeSpecialKey(isNumberMode ? "ABC" : "123");
        modeButton.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13);
        modeButton.setOnClickListener(v -> modeTapped());
        LinearLayout.LayoutParams modeParams = new LinearLayout.LayoutParams(dp(50), dp(42));
        modeParams.setMargins(dp(4), 0, dp(4), 0);
        toolbar.addView(modeButton, modeParams);

        // Space bar
        spaceButton = new Button(this);
        spaceButton.setText("space");
        spaceButton.setTextColor(DIM_TEXT);
        spaceButton.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13);
        spaceButton.setAllCaps(false);

        GradientDrawable spaceBg = new GradientDrawable();
        spaceBg.setColor(KEY_COLOR);
        spaceBg.setCornerRadius(dp(6));
        spaceButton.setBackground(spaceBg);
        spaceButton.setOnClickListener(v -> spaceTapped());
        LinearLayout.LayoutParams spaceParams = new LinearLayout.LayoutParams(0, dp(42), 1f);
        spaceParams.setMargins(dp(4), 0, dp(4), 0);
        toolbar.addView(spaceButton, spaceParams);

        // Return button
        Button returnBtn = makeSpecialKey("return");
        returnBtn.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13);
        returnBtn.setOnClickListener(v -> returnTapped());
        LinearLayout.LayoutParams retParams = new LinearLayout.LayoutParams(dp(72), dp(42));
        toolbar.addView(returnBtn, retParams);

        rootLayout.addView(toolbar);
    }

    // ══════════════════════════════════════════
    // Key Actions
    // ══════════════════════════════════════════

    private void letterTapped(String key) {
        InputConnection ic = getCurrentInputConnection();
        if (ic == null) return;

        String letter = (isShifted || isCaps) ? key.toUpperCase() : key.toLowerCase();
        ic.commitText(letter, 1);

        // Haptic feedback
        View view = rootLayout;
        if (view != null) {
            view.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP);
        }

        // Auto-unshift
        if (isShifted && !isCaps) {
            isShifted = false;
            refreshKeyLabels();
        }
    }

    private void spaceTapped() {
        InputConnection ic = getCurrentInputConnection();
        if (ic != null) ic.commitText(" ", 1);
    }

    private void returnTapped() {
        InputConnection ic = getCurrentInputConnection();
        if (ic != null) ic.commitText("\n", 1);
    }

    private void backspaceTapped() {
        InputConnection ic = getCurrentInputConnection();
        if (ic != null) ic.deleteSurroundingText(1, 0);
    }

    private void backspaceLongPress() {
        InputConnection ic = getCurrentInputConnection();
        if (ic != null) ic.deleteSurroundingText(10, 0);
    }

    private void shiftTapped() {
        isShifted = !isShifted;
        isCaps = false;
        refreshKeyLabels();
    }

    private void capsLockTapped() {
        isCaps = true;
        isShifted = true;
        refreshKeyLabels();
    }

    private void modeTapped() {
        isNumberMode = !isNumberMode;
        isSymbolMode = false;
        rebuildKeys();
    }

    private void symbolToggleTapped() {
        isSymbolMode = !isSymbolMode;
        rebuildKeys();
    }

    private void rebuildKeys() {
        if (isNumberMode) {
            buildKeyRows(isSymbolMode ? SYMBOL_ROWS : NUMBER_ROWS, false);
        } else {
            buildKeyRows(LETTER_ROWS, true);
        }
        modeButton.setText(isNumberMode ? "ABC" : "123");
    }

    private void refreshKeyLabels() {
        // Rebuild with updated shift state
        if (isNumberMode) {
            buildKeyRows(isSymbolMode ? SYMBOL_ROWS : NUMBER_ROWS, false);
        } else {
            buildKeyRows(LETTER_ROWS, true);
        }
    }

    // ══════════════════════════════════════════
    // Guardian Engine (Java port of guardian.py)
    // ══════════════════════════════════════════

    private static class GuardianFlag {
        String type, severity, reason;
        GuardianFlag(String type, String severity, String reason) {
            this.type = type; this.severity = severity; this.reason = reason;
        }
    }

    private static class GuardianResult {
        String riskLevel, warning, softerVersion;
        List<GuardianFlag> flags;
        GuardianResult(String risk, String warn, String softer, List<GuardianFlag> flags) {
            this.riskLevel = risk; this.warning = warn; this.softerVersion = softer; this.flags = flags;
        }
    }

    private GuardianResult analyzeMessage(String text) {
        List<GuardianFlag> flags = new ArrayList<>();
        if (text == null || text.trim().isEmpty()) {
            return new GuardianResult("none", "", "", flags);
        }

        String lower = text.toLowerCase(Locale.ROOT);

        // 1. Late night (midnight–5am)
        int hour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY);
        if (hour >= 0 && hour <= 5) {
            flags.add(new GuardianFlag("late_night", "medium",
                "It's late. Messages sent between midnight and 5am have a higher regret rate."));
        }

        // 2. ALL CAPS
        int alphaCount = 0, upperCount = 0;
        for (char c : text.toCharArray()) {
            if (Character.isLetter(c)) {
                alphaCount++;
                if (Character.isUpperCase(c)) upperCount++;
            }
        }
        if (alphaCount > 0 && text.length() > 10) {
            double capsRatio = (double) upperCount / alphaCount;
            if (capsRatio > 0.7) {
                flags.add(new GuardianFlag("all_caps", "medium",
                    "ALL CAPS can come across as shouting."));
            }
        }

        // 3. Ex-partner
        for (String pattern : EX_PATTERNS) {
            if (Pattern.compile(pattern, Pattern.CASE_INSENSITIVE).matcher(lower).find()) {
                flags.add(new GuardianFlag("ex_partner", "high",
                    "This might be going to an ex. Sleep on it?"));
                break;
            }
        }

        // 4. Reply-all
        for (String pattern : REPLY_ALL_PATTERNS) {
            if (Pattern.compile(pattern, Pattern.CASE_INSENSITIVE).matcher(lower).find()) {
                flags.add(new GuardianFlag("reply_all", "high",
                    "This looks like a reply-all or broadcast. Everyone gets this."));
                break;
            }
        }

        // 5. Profanity density
        int wordCount = Math.max(text.split("\\s+").length, 1);
        int profanityCount = 0;
        for (String p : PROFANITY) { if (lower.contains(p)) profanityCount++; }
        if (profanityCount >= 2 || (double) profanityCount / wordCount > 0.1) {
            flags.add(new GuardianFlag("profanity", "medium",
                "High profanity density. Might want to cool down first."));
        }

        // 6. Exclamation density
        int excCount = 0;
        for (char c : text.toCharArray()) { if (c == '!') excCount++; }
        if (excCount >= 3) {
            flags.add(new GuardianFlag("exclamation_heavy", "low",
                "Lots of exclamation marks. High energy detected."));
        }

        // 7. Angry wall
        if (text.length() > 500 && classifySentiment(text).equals("angry")) {
            flags.add(new GuardianFlag("angry_wall", "high",
                "Long angry message. These rarely land well."));
        }

        // Calculate risk
        Map<String, Integer> sevScores = new HashMap<>();
        sevScores.put("low", 1); sevScores.put("medium", 2); sevScores.put("high", 3);
        int totalRisk = 0;
        for (GuardianFlag f : flags) {
            totalRisk += sevScores.getOrDefault(f.severity, 0);
        }

        String riskLevel;
        if (totalRisk >= 5) riskLevel = "high";
        else if (totalRisk >= 2) riskLevel = "medium";
        else if (totalRisk >= 1) riskLevel = "low";
        else riskLevel = "none";

        String warning = companionWarning(riskLevel);
        String softer = !riskLevel.equals("none") ? suggestSofter(text) : "";

        return new GuardianResult(riskLevel, warning, softer, flags);
    }

    private String classifySentiment(String text) {
        String lower = text.toLowerCase(Locale.ROOT);
        int angry = 0, sad = 0, happy = 0;
        for (String w : ANGRY_WORDS) { if (lower.contains(w)) angry++; }
        for (String w : SAD_WORDS) { if (lower.contains(w)) sad++; }
        for (String w : HAPPY_WORDS) { if (lower.contains(w)) happy++; }

        int max = Math.max(angry, Math.max(sad, happy));
        if (max == 0) return "neutral";
        if (angry == max) return "angry";
        if (sad == max) return "sad";
        return "happy";
    }

    private String suggestSofter(String text) {
        String result = text;
        for (String[] pair : SOFTENERS) {
            result = Pattern.compile(pair[0], Pattern.CASE_INSENSITIVE).matcher(result).replaceAll(pair[1]);
        }
        return result.equals(text) ? "" : result;
    }

    // ══════════════════════════════════════════
    // Companion Personality
    // ══════════════════════════════════════════

    private String companionEmoji() {
        String species = loadCompanionSpecies();
        switch (species) {
            case "dog": return "🐕";
            case "penguin": return "🐧";
            case "fox": return "🦊";
            case "owl": return "🦉";
            case "dragon": return "🐉";
            default: return "🐱";
        }
    }

    private String companionName() {
        SharedPreferences prefs = getSharedPreferences("fireside_companion", Context.MODE_PRIVATE);
        return prefs.getString("companion_name", "Sir Wadsworth");
    }

    private String loadCompanionSpecies() {
        SharedPreferences prefs = getSharedPreferences("fireside_companion", Context.MODE_PRIVATE);
        return prefs.getString("companion_species", "penguin");
    }

    private String companionWarning(String riskLevel) {
        String species = loadCompanionSpecies();
        Map<String, Map<String, String>> all = new HashMap<>();

        Map<String, String> cat = new HashMap<>();
        cat.put("high", "Are you sure? This sounds like 2am energy.");
        cat.put("medium", "Hmm. I'd sleep on this one.");
        cat.put("low", "Just checking — you good?");
        all.put("cat", cat);

        Map<String, String> dog = new HashMap<>();
        dog.put("high", "Hey buddy... are we sure about this one? 🥺");
        dog.put("medium", "Want to take a walk first? Clear your head?");
        dog.put("low", "I believe in you! But maybe re-read it?");
        all.put("dog", dog);

        Map<String, String> penguin = new HashMap<>();
        penguin.put("high", "Sir. I must advise against this correspondence.");
        penguin.put("medium", "Perhaps a more... measured approach?");
        penguin.put("low", "Noted. Proceed with mild caution.");
        all.put("penguin", penguin);

        Map<String, String> fox = new HashMap<>();
        fox.put("high", "My instincts say wait. Trust the instincts.");
        fox.put("medium", "There's a smarter play here. Want to think on it?");
        fox.put("low", "Looks fine, but I'm watching.");
        all.put("fox", fox);

        Map<String, String> owl = new HashMap<>();
        owl.put("high", "Historically, messages like this have a 78% regret rate.");
        owl.put("medium", "The data suggests a 15-minute cooling period.");
        owl.put("low", "Minor risk detected. Proceeding is acceptable.");
        all.put("owl", owl);

        Map<String, String> dragon = new HashMap<>();
        dragon.put("high", "I RESPECT THE ENERGY but your boss might not.");
        dragon.put("medium", "Save the fire for something worth burning.");
        dragon.put("low", "This is fine. Probably. SEND IT.");
        all.put("dragon", dragon);

        Map<String, String> speciesMap = all.getOrDefault(species, cat);
        return speciesMap.getOrDefault(riskLevel, "");
    }

    // ══════════════════════════════════════════
    // Guardian Monitoring
    // ══════════════════════════════════════════

    private void startGuardianMonitoring() {
        guardianTimer = new Timer();
        guardianTimer.scheduleAtFixedRate(new TimerTask() {
            @Override
            public void run() {
                mainHandler.post(() -> runGuardianAnalysis());
            }
        }, 500, 500);
    }

    private void runGuardianAnalysis() {
        InputConnection ic = getCurrentInputConnection();
        if (ic == null) return;

        // Get current text
        CharSequence before = ic.getTextBeforeCursor(1000, 0);
        CharSequence after = ic.getTextAfterCursor(1000, 0);
        String fullText = (before != null ? before.toString() : "") +
                          (after != null ? after.toString() : "");

        if (fullText.length() <= 5) {
            hideGuardianBar();
            return;
        }

        GuardianResult result = analyzeMessage(fullText);
        if (!result.riskLevel.equals("none")) {
            currentSofterVersion = result.softerVersion;
            showGuardianBar(result);
        } else {
            currentSofterVersion = "";
            hideGuardianBar();
        }
    }

    private void showGuardianBar(GuardianResult result) {
        guardianLabel.setText(result.warning);
        if (guardianBar.getVisibility() != View.VISIBLE) {
            guardianBar.setVisibility(View.VISIBLE);
            guardianBar.setAlpha(0f);
            guardianBar.animate().alpha(1f).setDuration(200).start();
        }
    }

    private void hideGuardianBar() {
        if (guardianBar.getVisibility() == View.VISIBLE) {
            guardianBar.animate().alpha(0f).setDuration(150).withEndAction(() ->
                guardianBar.setVisibility(View.GONE)
            ).start();
        }
    }

    private void softerTapped() {
        if (currentSofterVersion.isEmpty()) return;

        InputConnection ic = getCurrentInputConnection();
        if (ic == null) return;

        // Select all and replace
        CharSequence before = ic.getTextBeforeCursor(1000, 0);
        CharSequence after = ic.getTextAfterCursor(1000, 0);
        int totalLen = (before != null ? before.length() : 0) + (after != null ? after.length() : 0);

        ic.deleteSurroundingText(before != null ? before.length() : 0, after != null ? after.length() : 0);
        ic.commitText(currentSofterVersion, 1);
        hideGuardianBar();
    }

    private void ignoreTapped() {
        hideGuardianBar();
        currentSofterVersion = "";
    }

    // ══════════════════════════════════════════
    // Translate Engine
    // ══════════════════════════════════════════

    private void translateTapped() {
        InputConnection ic = getCurrentInputConnection();
        if (ic == null) return;

        CharSequence before = ic.getTextBeforeCursor(2000, 0);
        CharSequence after = ic.getTextAfterCursor(2000, 0);
        String fullText = ((before != null ? before.toString() : "") +
                          (after != null ? after.toString() : "")).trim();

        if (fullText.isEmpty()) return;

        spaceButton.setText("Translating...");
        spaceButton.setTextColor(ACCENT);

        String pcHost = loadPCHost();
        if (!pcHost.isEmpty()) {
            translateViaPC(fullText, pcHost);
        } else {
            translateViaGoogle(fullText);
        }
    }

    private String loadPCHost() {
        SharedPreferences prefs = getSharedPreferences("fireside_companion", Context.MODE_PRIVATE);
        return prefs.getString("pc_host", "");
    }

    private void translateViaPC(String text, String host) {
        new Thread(() -> {
            try {
                String deviceLang = Locale.getDefault().getLanguage();
                String targetLang = "en".equals(deviceLang) ? "spa_Latn" : deviceLang + "_Latn";

                URL url = new URL("http://" + host + ":8000/translate");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setConnectTimeout(5000);
                conn.setReadTimeout(5000);
                conn.setDoOutput(true);

                String body = "{\"text\":\"" + text.replace("\"", "\\\"") +
                              "\",\"target_lang\":\"" + targetLang + "\"}";
                OutputStream os = conn.getOutputStream();
                os.write(body.getBytes("UTF-8"));
                os.close();

                BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) sb.append(line);
                reader.close();

                // Parse JSON
                org.json.JSONObject json = new org.json.JSONObject(sb.toString());
                String translated = json.optString("translated", "");

                if (!translated.isEmpty()) {
                    mainHandler.post(() -> applyTranslation(translated, "🏠 Home PC"));
                    return;
                }
            } catch (Exception e) {
                // Fall through to Google
            }
            mainHandler.post(() -> translateViaGoogle(text));
        }).start();
    }

    private void translateViaGoogle(String text) {
        new Thread(() -> {
            try {
                String deviceLang = Locale.getDefault().getLanguage();
                String targetLang = "en".equals(deviceLang) ? "es" : deviceLang;
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

                String translated = result.toString().trim();
                if (!translated.isEmpty()) {
                    mainHandler.post(() -> applyTranslation(translated, "☁️ Google"));
                } else {
                    mainHandler.post(this::resetSpaceBar);
                }
            } catch (Exception e) {
                mainHandler.post(this::resetSpaceBar);
            }
        }).start();
    }

    private void applyTranslation(String translated, String source) {
        InputConnection ic = getCurrentInputConnection();
        if (ic == null) { resetSpaceBar(); return; }

        CharSequence before = ic.getTextBeforeCursor(2000, 0);
        CharSequence after = ic.getTextAfterCursor(2000, 0);
        ic.deleteSurroundingText(
            before != null ? before.length() : 0,
            after != null ? after.length() : 0
        );
        ic.commitText(translated, 1);

        spaceButton.setText(source);
        spaceButton.setTextColor(source.contains("Home") ? SUCCESS : WARNING_AMB);

        mainHandler.postDelayed(this::resetSpaceBar, 2000);
    }

    private void resetSpaceBar() {
        spaceButton.setText("space");
        spaceButton.setTextColor(DIM_TEXT);
    }

    // ══════════════════════════════════════════
    // Utility
    // ══════════════════════════════════════════

    private int dp(int value) {
        return (int) TypedValue.applyDimension(
            TypedValue.COMPLEX_UNIT_DIP, value, getResources().getDisplayMetrics()
        );
    }
}
