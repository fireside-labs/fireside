/**
 * Sound manager — Sprint 3.
 *
 * Plays short sound effects on key actions.
 * Feed, walk, level-up, chat send.
 *
 * Note: Sound files are tiny MP3s (<50KB).
 * If files are missing, sounds degrade silently.
 */
import { Audio } from "expo-av";

let initialized = false;

async function ensureAudioMode() {
    if (initialized) return;
    await Audio.setAudioModeAsync({
        playsInSilentModeIOS: false,
        staysActiveInBackground: false,
        shouldDuckAndroid: true,
    });
    initialized = true;
}

const soundFiles = {
    feed: require("../assets/sounds/feed.mp3"),
    walk: require("../assets/sounds/walk.mp3"),
    levelUp: require("../assets/sounds/level_up.mp3"),
    send: require("../assets/sounds/send.mp3"),
};

/**
 * Play a named sound effect.
 * Silently fails if the sound file is missing or playback errors.
 */
export async function playSound(name: keyof typeof soundFiles) {
    try {
        await ensureAudioMode();
        const { sound } = await Audio.Sound.createAsync(soundFiles[name]);
        await sound.playAsync();
        sound.setOnPlaybackStatusUpdate((status) => {
            if (status.isLoaded && status.didJustFinish) {
                sound.unloadAsync();
            }
        });
    } catch {
        // Silently fail — sound is a nice-to-have, not critical
    }
}
