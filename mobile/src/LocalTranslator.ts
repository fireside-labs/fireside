/**
 * 📱 LocalTranslator — On-device translation fallback when PC is offline.
 *
 * Architecture: PC (NLLB-200, 200 langs) is always preferred.
 * When offline, the phone falls back to:
 *   1. Small brain (Qwen 0.5B via local llama-server if running)
 *   2. Basic phrase dictionary for ultra-common phrases
 *
 * The phone brain is small and stupid — this is a graceful degradation,
 * NOT a replacement for the PC's NLLB model.
 */

// ── Common phrase dictionary (last-resort fallback) ──
// Only covers greetings + essentials in the top 10 languages.
// Better than nothing when both PC AND small brain are offline.

interface PhraseEntry {
    [langCode: string]: string;
}

const PHRASE_DICT: Record<string, PhraseEntry> = {
    "hello": {
        es: "Hola", fr: "Bonjour", de: "Hallo", pt: "Olá", it: "Ciao",
        ja: "こんにちは", ko: "안녕하세요", zh: "你好", ar: "مرحبا", hi: "नमस्ते",
        ru: "Здравствуйте", tr: "Merhaba", vi: "Xin chào", tl: "Kumusta",
    },
    "goodbye": {
        es: "Adiós", fr: "Au revoir", de: "Auf Wiedersehen", pt: "Adeus", it: "Arrivederci",
        ja: "さようなら", ko: "안녕히 가세요", zh: "再见", ar: "مع السلامة", hi: "अलविदा",
        ru: "До свидания", tr: "Hoşça kal", vi: "Tạm biệt", tl: "Paalam",
    },
    "thank you": {
        es: "Gracias", fr: "Merci", de: "Danke", pt: "Obrigado", it: "Grazie",
        ja: "ありがとう", ko: "감사합니다", zh: "谢谢", ar: "شكرا", hi: "धन्यवाद",
        ru: "Спасибо", tr: "Teşekkür ederim", vi: "Cảm ơn", tl: "Salamat",
    },
    "yes": {
        es: "Sí", fr: "Oui", de: "Ja", pt: "Sim", it: "Sì",
        ja: "はい", ko: "네", zh: "是", ar: "نعم", hi: "हाँ",
        ru: "Да", tr: "Evet", vi: "Vâng", tl: "Oo",
    },
    "no": {
        es: "No", fr: "Non", de: "Nein", pt: "Não", it: "No",
        ja: "いいえ", ko: "아니요", zh: "不", ar: "لا", hi: "नहीं",
        ru: "Нет", tr: "Hayır", vi: "Không", tl: "Hindi",
    },
    "please": {
        es: "Por favor", fr: "S'il vous plaît", de: "Bitte", pt: "Por favor", it: "Per favore",
        ja: "お願いします", ko: "제발", zh: "请", ar: "من فضلك", hi: "कृपया",
        ru: "Пожалуйста", tr: "Lütfen", vi: "Xin vui lòng", tl: "Pakiusap",
    },
    "sorry": {
        es: "Lo siento", fr: "Désolé", de: "Es tut mir leid", pt: "Desculpe", it: "Mi dispiace",
        ja: "すみません", ko: "미안합니다", zh: "对不起", ar: "آسف", hi: "माफ़ कीजिए",
        ru: "Извините", tr: "Özür dilerim", vi: "Xin lỗi", tl: "Pasensya na",
    },
    "how are you": {
        es: "¿Cómo estás?", fr: "Comment allez-vous?", de: "Wie geht es Ihnen?",
        pt: "Como você está?", it: "Come stai?", ja: "お元気ですか？",
        ko: "어떻게 지내세요?", zh: "你好吗？", ar: "كيف حالك؟", hi: "आप कैसे हैं?",
        ru: "Как дела?", tr: "Nasılsınız?", vi: "Bạn khỏe không?", tl: "Kamusta ka?",
    },
    "i love you": {
        es: "Te quiero", fr: "Je t'aime", de: "Ich liebe dich", pt: "Eu te amo",
        it: "Ti amo", ja: "愛してる", ko: "사랑해요", zh: "我爱你",
        ar: "أحبك", hi: "मैं तुमसे प्यार करता हूँ", ru: "Я тебя люблю",
        tr: "Seni seviyorum", vi: "Tôi yêu bạn", tl: "Mahal kita",
    },
    "where is the bathroom": {
        es: "¿Dónde está el baño?", fr: "Où sont les toilettes?",
        de: "Wo ist die Toilette?", pt: "Onde fica o banheiro?",
        it: "Dov'è il bagno?", ja: "トイレはどこですか？",
        ko: "화장실이 어디예요?", zh: "洗手间在哪里？",
        ar: "أين الحمام؟", hi: "शौचालय कहाँ है?",
        ru: "Где туалет?", tr: "Tuvalet nerede?",
        vi: "Nhà vệ sinh ở đâu?", tl: "Nasaan ang banyo?",
    },
    "how much does it cost": {
        es: "¿Cuánto cuesta?", fr: "Combien ça coûte?",
        de: "Wie viel kostet das?", pt: "Quanto custa?",
        it: "Quanto costa?", ja: "いくらですか？",
        ko: "얼마예요?", zh: "多少钱？",
        ar: "كم الثمن؟", hi: "कितने का है?",
        ru: "Сколько стоит?", tr: "Ne kadar?",
        vi: "Giá bao nhiêu?", tl: "Magkano?",
    },
    "i don't understand": {
        es: "No entiendo", fr: "Je ne comprends pas",
        de: "Ich verstehe nicht", pt: "Não entendo",
        it: "Non capisco", ja: "わかりません",
        ko: "이해하지 못합니다", zh: "我不明白",
        ar: "لا أفهم", hi: "मुझे समझ नहीं आया",
        ru: "Я не понимаю", tr: "Anlamıyorum",
        vi: "Tôi không hiểu", tl: "Hindi ko naiintindihan",
    },
    "help": {
        es: "Ayuda", fr: "Aide", de: "Hilfe", pt: "Ajuda", it: "Aiuto",
        ja: "助けて", ko: "도와주세요", zh: "帮助", ar: "مساعدة", hi: "मदद",
        ru: "Помогите", tr: "Yardım", vi: "Giúp đỡ", tl: "Tulong",
    },
};

// NLLB code → ISO 639-1 mapping (for dictionary lookup)
const NLLB_TO_ISO: Record<string, string> = {
    "eng_Latn": "en", "spa_Latn": "es", "fra_Latn": "fr", "deu_Latn": "de",
    "por_Latn": "pt", "ita_Latn": "it", "jpn_Jpan": "ja", "kor_Hang": "ko",
    "zho_Hans": "zh", "zho_Hant": "zh", "arb_Arab": "ar", "hin_Deva": "hi",
    "rus_Cyrl": "ru", "tur_Latn": "tr", "vie_Latn": "vi", "tgl_Latn": "tl",
    "nld_Latn": "nl", "pol_Latn": "pl", "tha_Thai": "th", "ind_Latn": "id",
    "swe_Latn": "sv", "ces_Latn": "cs", "ell_Grek": "el", "heb_Hebr": "he",
    "ukr_Cyrl": "uk", "swh_Latn": "sw", "ben_Beng": "bn", "urd_Arab": "ur",
    "pes_Arab": "fa", "zsm_Latn": "ms", "tam_Taml": "ta",
};

export interface LocalTranslationResult {
    ok: boolean;
    translated: string;
    method: "dictionary" | "small_brain" | "failed";
    source_lang?: string;
    target_lang?: string;
    note?: string;
}

/**
 * Translate text on-device. Tries small brain first, then phrase dictionary.
 *
 * @param text - Text to translate
 * @param targetLangNLLB - Target language in NLLB format (e.g., "spa_Latn")
 */
export async function translateLocal(
    text: string,
    targetLangNLLB: string
): Promise<LocalTranslationResult> {
    const targetISO = NLLB_TO_ISO[targetLangNLLB] || "";
    const normalized = text.trim().toLowerCase().replace(/[?.!]+$/, "");

    // 1. Try phrase dictionary first (instant, no model needed)
    if (PHRASE_DICT[normalized]?.[targetISO]) {
        return {
            ok: true,
            translated: PHRASE_DICT[normalized][targetISO],
            method: "dictionary",
            target_lang: targetISO,
            note: "Common phrase — translated from built-in dictionary",
        };
    }

    // 2. Try small brain (Qwen 0.5B if running locally)
    try {
        const result = await trySmallBrain(text, targetISO, targetLangNLLB);
        if (result) return result;
    } catch { }

    // 3. No translation available
    return {
        ok: false,
        translated: text,
        method: "failed",
        note: "Connect to your home PC for full translation (200 languages)",
    };
}

/**
 * Try to translate via the small on-device brain (Qwen 0.5B).
 * Returns null if the small brain is not available.
 */
async function trySmallBrain(
    text: string,
    targetISO: string,
    targetNLLB: string
): Promise<LocalTranslationResult | null> {
    // The small brain runs as a local llama-server on the phone
    // Check if it's available at localhost:8080 (default llama.cpp port)
    const SMALL_BRAIN_URL = "http://127.0.0.1:8080/completion";
    const TIMEOUT_MS = 5000;

    const langNames: Record<string, string> = {
        es: "Spanish", fr: "French", de: "German", pt: "Portuguese",
        it: "Italian", ja: "Japanese", ko: "Korean", zh: "Chinese",
        ar: "Arabic", hi: "Hindi", ru: "Russian", tr: "Turkish",
        vi: "Vietnamese", tl: "Tagalog", nl: "Dutch", pl: "Polish",
        th: "Thai", id: "Indonesian", sv: "Swedish", cs: "Czech",
        el: "Greek", he: "Hebrew", uk: "Ukrainian",
    };
    const langName = langNames[targetISO] || targetISO;

    try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

        const res = await fetch(SMALL_BRAIN_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                prompt: `Translate to ${langName}: "${text}"\nTranslation:`,
                n_predict: 128,
                temperature: 0.1,
                stop: ["\n", "\""],
            }),
            signal: controller.signal,
        });

        clearTimeout(timer);

        if (res.ok) {
            const data = await res.json();
            const translated = (data.content || "").trim().replace(/^["']|["']$/g, "");
            if (translated && translated !== text) {
                return {
                    ok: true,
                    translated,
                    method: "small_brain",
                    target_lang: targetISO,
                    note: "Translated on-device (quality may vary)",
                };
            }
        }
    } catch {
        // Small brain not available
    }

    return null;
}

/**
 * Check if any local translation capability is available.
 */
export async function isLocalTranslationAvailable(): Promise<boolean> {
    // Check if small brain is running
    try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 1000);
        const res = await fetch("http://127.0.0.1:8080/health", { signal: controller.signal });
        clearTimeout(timer);
        return res.ok;
    } catch {
        // Small brain not running — dictionary is always available
        return true; // Dictionary is always available as last resort
    }
}
