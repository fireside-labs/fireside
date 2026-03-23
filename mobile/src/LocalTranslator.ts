/**
 * 📱 LocalTranslator — Fallback translation when the home PC is offline.
 *
 * Architecture: PC (NLLB-200, 200 langs, private) is always preferred.
 * When offline from the PC, the phone falls back to Google Translate.
 * This keeps the user inside the app while giving real translations.
 *
 * Privacy: Texts go through Google's servers when using this fallback.
 * The UI shows "☁️ Google Translate" so the user knows.
 */

// ── NLLB code → ISO 639-1 mapping (Google Translate uses ISO codes) ──
const NLLB_TO_ISO: Record<string, string> = {
    "eng_Latn": "en", "spa_Latn": "es", "fra_Latn": "fr", "deu_Latn": "de",
    "por_Latn": "pt", "ita_Latn": "it", "jpn_Jpan": "ja", "kor_Hang": "ko",
    "zho_Hans": "zh", "zho_Hant": "zh-TW", "arb_Arab": "ar", "hin_Deva": "hi",
    "rus_Cyrl": "ru", "tur_Latn": "tr", "vie_Latn": "vi", "tgl_Latn": "tl",
    "nld_Latn": "nl", "pol_Latn": "pl", "tha_Thai": "th", "ind_Latn": "id",
    "swe_Latn": "sv", "ces_Latn": "cs", "ell_Grek": "el", "heb_Hebr": "he",
    "ukr_Cyrl": "uk", "swh_Latn": "sw", "ben_Beng": "bn", "urd_Arab": "ur",
    "pes_Arab": "fa", "zsm_Latn": "ms", "tam_Taml": "ta",
};

export interface LocalTranslationResult {
    ok: boolean;
    translated: string;
    method: "google" | "failed";
    source_lang?: string;
    target_lang?: string;
    note?: string;
}

/**
 * Translate text via Google Translate (free web API).
 * Used as fallback when the home PC's NLLB model is unreachable.
 *
 * @param text - Text to translate
 * @param targetLangNLLB - Target language in NLLB format (e.g., "spa_Latn")
 */
export async function translateLocal(
    text: string,
    targetLangNLLB: string
): Promise<LocalTranslationResult> {
    const targetISO = NLLB_TO_ISO[targetLangNLLB] || targetLangNLLB.split("_")[0];

    try {
        const result = await googleTranslate(text, targetISO);
        if (result) return result;
    } catch { }

    return {
        ok: false,
        translated: text,
        method: "failed",
        note: "Translation unavailable — check your internet connection",
    };
}

/**
 * Call Google Translate's free web API.
 * No API key needed — uses the same endpoint as translate.google.com.
 */
async function googleTranslate(
    text: string,
    targetLang: string
): Promise<LocalTranslationResult | null> {
    const TIMEOUT_MS = 8000;
    const encoded = encodeURIComponent(text);
    const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=${targetLang}&dt=t&q=${encoded}`;

    try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

        const res = await fetch(url, {
            method: "GET",
            signal: controller.signal,
        });

        clearTimeout(timer);

        if (res.ok) {
            const data = await res.json();
            // Google returns nested arrays: [[["translated text","source text",...],...],null,"detected_lang"]
            const segments: string[] = [];
            if (Array.isArray(data[0])) {
                for (const segment of data[0]) {
                    if (segment[0]) segments.push(segment[0]);
                }
            }

            const translated = segments.join("").trim();
            const detectedLang = data[2] || "auto";

            if (translated && translated.toLowerCase() !== text.toLowerCase()) {
                return {
                    ok: true,
                    translated,
                    method: "google",
                    source_lang: detectedLang,
                    target_lang: targetLang,
                    note: "Translated via Google Translate (cloud)",
                };
            }
        }
    } catch {
        // Network error or timeout
    }

    return null;
}

/**
 * Check if fallback translation is available (has internet).
 */
export async function isLocalTranslationAvailable(): Promise<boolean> {
    try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 2000);
        const res = await fetch("https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=es&dt=t&q=test", {
            signal: controller.signal,
        });
        clearTimeout(timer);
        return res.ok;
    } catch {
        return false;
    }
}
