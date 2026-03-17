"use client";

/**
 * 🔊 FiresideSounds — Web Audio API sound effects.
 *
 * Generates all sounds procedurally (no external files needed):
 * - Fire crackling: layered filtered noise
 * - UI whoosh: filtered sweep
 * - Confirm tone: warm two-note chime
 * - Step complete: quick bright ping
 * - Ambient hum: low filtered drone
 */

let audioCtx: AudioContext | null = null;

function getCtx(): AudioContext {
  if (!audioCtx) {
    audioCtx = new AudioContext();
  }
  if (audioCtx.state === "suspended") {
    audioCtx.resume();
  }
  return audioCtx;
}

/** Fire crackling — DISABLED (procedural sound was poor quality) */
export function playCrackle(_volume = 0.12) {
  // No-op — needs real audio sample, not synthesis
}

/** Fire loop — DISABLED */
export function startFireLoop(_intensity = 0.5): () => void {
  return () => {}; // No-op
}

/** UI whoosh — sweep filter on noise */
export function playWhoosh(volume = 0.08) {
  try {
    const ctx = getCtx();
    const duration = 0.25;
    const bufferSize = ctx.sampleRate * duration;
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);

    for (let i = 0; i < bufferSize; i++) {
      data[i] = Math.random() * 2 - 1;
    }

    const source = ctx.createBufferSource();
    source.buffer = buffer;

    const filter = ctx.createBiquadFilter();
    filter.type = "bandpass";
    filter.frequency.setValueAtTime(200, ctx.currentTime);
    filter.frequency.exponentialRampToValueAtTime(2000, ctx.currentTime + duration * 0.3);
    filter.frequency.exponentialRampToValueAtTime(100, ctx.currentTime + duration);
    filter.Q.value = 5;

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0, ctx.currentTime);
    gain.gain.linearRampToValueAtTime(volume, ctx.currentTime + 0.03);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);

    source.connect(filter).connect(gain).connect(ctx.destination);
    source.start();
    source.stop(ctx.currentTime + duration);
  } catch { /* Audio not available */ }
}

/** Confirm tone — warm two-note major chime */
export function playConfirm(volume = 0.15) {
  try {
    const ctx = getCtx();
    const notes = [523.25, 659.25]; // C5, E5 — warm major third

    notes.forEach((freq, i) => {
      const osc = ctx.createOscillator();
      osc.type = "sine";
      osc.frequency.value = freq;

      const gain = ctx.createGain();
      const startTime = ctx.currentTime + i * 0.12;
      gain.gain.setValueAtTime(0, startTime);
      gain.gain.linearRampToValueAtTime(volume, startTime + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.6);

      osc.connect(gain).connect(ctx.destination);
      osc.start(startTime);
      osc.stop(startTime + 0.6);
    });
  } catch { /* Audio not available */ }
}

/** Step complete — quick bright ping */
export function playPing(volume = 0.1) {
  try {
    const ctx = getCtx();
    const osc = ctx.createOscillator();
    osc.type = "sine";
    osc.frequency.value = 880; // A5

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(volume, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.15);

    osc.connect(gain).connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.15);
  } catch { /* Audio not available */ }
}

/** Select/hover sound — subtle tick */
export function playTick(volume = 0.05) {
  try {
    const ctx = getCtx();
    const osc = ctx.createOscillator();
    osc.type = "sine";
    osc.frequency.value = 600;

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(volume, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.05);

    osc.connect(gain).connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.05);
  } catch { /* Audio not available */ }
}
