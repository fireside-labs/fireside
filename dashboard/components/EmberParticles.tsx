"use client";

import { useRef, useEffect, useCallback } from "react";

/**
 * 🔥 EmberParticles — Canvas-based fire particle system.
 *
 * Intensity (0-100) controls:
 *  - Particle count (10 at 0% → 60 at 100%)
 *  - Speed & size of embers
 *  - Color temperature (dark red → golden-white)
 *  - Opacity and glow intensity
 *
 * Used in the installer during install + throughout the dashboard.
 */

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  life: number;
  maxLife: number;
  color: string;
  opacity: number;
  flickerSpeed: number;
  flickerPhase: number;
}

interface EmberParticlesProps {
  /** 0-100, controls intensity of the fire effect */
  intensity?: number;
  /** If true, triggers a burst of sparks (resets after burst) */
  burst?: boolean;
  /** CSS className for the container */
  className?: string;
  /** Inline styles */
  style?: React.CSSProperties;
}

// Color palette: cold embers → raging fire
const COLORS_BY_HEAT = [
  // Low heat (0-25%)
  ["#5C2D06", "#7C3A0A", "#92400E", "#A44B10"],
  // Medium heat (25-50%)
  ["#92400E", "#B45309", "#D97706", "#D97706"],
  // High heat (50-75%)
  ["#D97706", "#F59E0B", "#FBBF24", "#F59E0B"],
  // Max heat (75-100%)
  ["#F59E0B", "#FBBF24", "#FDE68A", "#FEF3C7"],
];

function getHeatColors(intensity: number): string[] {
  const idx = Math.min(Math.floor(intensity / 25), 3);
  return COLORS_BY_HEAT[idx];
}

function randomBetween(min: number, max: number) {
  return Math.random() * (max - min) + min;
}

export default function EmberParticles({
  intensity = 30,
  burst = false,
  className = "",
  style = {},
}: EmberParticlesProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const animFrameRef = useRef<number>(0);
  const intensityRef = useRef(intensity);
  const burstCountRef = useRef(0);

  intensityRef.current = intensity;

  const spawnParticle = useCallback(
    (canvas: HTMLCanvasElement, isBurst = false): Particle => {
      const heat = intensityRef.current;
      const colors = getHeatColors(heat);
      const color = colors[Math.floor(Math.random() * colors.length)];

      // Spawn from bottom-center area with spread
      const spreadX = canvas.width * (0.15 + (heat / 100) * 0.35);
      const centerX = canvas.width / 2;

      const speedMult = 0.5 + (heat / 100) * 1.5;
      const sizeMult = 0.5 + (heat / 100) * 1.0;

      return {
        x: centerX + randomBetween(-spreadX, spreadX),
        y: isBurst
          ? canvas.height * randomBetween(0.5, 0.85)
          : canvas.height + randomBetween(0, 20),
        vx: randomBetween(-0.8, 0.8) * speedMult,
        vy: randomBetween(-1.5, -0.4) * speedMult * (isBurst ? 2.5 : 1),
        size: randomBetween(1.5, 5) * sizeMult,
        life: 0,
        maxLife: randomBetween(60, 180) * (isBurst ? 0.6 : 1),
        color,
        opacity: randomBetween(0.4, 1.0),
        flickerSpeed: randomBetween(0.02, 0.08),
        flickerPhase: Math.random() * Math.PI * 2,
      };
    },
    []
  );

  useEffect(() => {
    if (burst) {
      burstCountRef.current += 20;
    }
  }, [burst]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Resize canvas to container
    const resizeObserver = new ResizeObserver(() => {
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * window.devicePixelRatio;
      canvas.height = rect.height * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    });
    resizeObserver.observe(canvas);

    const animate = () => {
      const rect = canvas.getBoundingClientRect();
      const w = rect.width;
      const h = rect.height;
      ctx.clearRect(0, 0, w, h);

      const heat = intensityRef.current;
      const targetCount = Math.floor(10 + (heat / 100) * 50);

      // Spawn new particles to maintain count
      while (particlesRef.current.length < targetCount) {
        particlesRef.current.push(spawnParticle(canvas));
      }

      // Spawn burst particles
      while (burstCountRef.current > 0) {
        particlesRef.current.push(spawnParticle(canvas, true));
        burstCountRef.current--;
      }

      // Update & draw
      const alive: Particle[] = [];
      for (const p of particlesRef.current) {
        p.life++;
        if (p.life > p.maxLife) continue;

        // Physics
        p.x += p.vx + Math.sin(p.life * 0.02) * 0.3; // gentle sway
        p.y += p.vy;
        p.vy -= 0.005; // slight upward acceleration
        p.vx *= 0.998; // air resistance

        // Fade lifecycle
        const lifeRatio = p.life / p.maxLife;
        const fadeIn = Math.min(p.life / 15, 1);
        const fadeOut = lifeRatio > 0.7 ? 1 - (lifeRatio - 0.7) / 0.3 : 1;
        const flicker =
          0.7 + 0.3 * Math.sin(p.life * p.flickerSpeed + p.flickerPhase);
        const alpha = p.opacity * fadeIn * fadeOut * flicker;

        if (alpha <= 0.01) continue;

        // Shrink as they die
        const currentSize = p.size * (1 - lifeRatio * 0.4);

        // Draw ember
        ctx.save();
        ctx.globalAlpha = alpha;

        // Glow
        const glowSize = currentSize * (2 + (heat / 100) * 3);
        const gradient = ctx.createRadialGradient(
          p.x,
          p.y,
          0,
          p.x,
          p.y,
          glowSize
        );
        gradient.addColorStop(0, p.color);
        gradient.addColorStop(0.3, p.color + "80");
        gradient.addColorStop(1, "transparent");
        ctx.fillStyle = gradient;
        ctx.fillRect(
          p.x - glowSize,
          p.y - glowSize,
          glowSize * 2,
          glowSize * 2
        );

        // Core ember
        ctx.beginPath();
        ctx.arc(p.x, p.y, currentSize, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.fill();

        // Hot center
        if (heat > 50) {
          ctx.beginPath();
          ctx.arc(p.x, p.y, currentSize * 0.4, 0, Math.PI * 2);
          ctx.fillStyle = "#FEF3C7";
          ctx.globalAlpha = alpha * 0.6;
          ctx.fill();
        }

        ctx.restore();
        alive.push(p);
      }

      particlesRef.current = alive;
      animFrameRef.current = requestAnimationFrame(animate);
    };

    animFrameRef.current = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(animFrameRef.current);
      resizeObserver.disconnect();
    };
  }, [spawnParticle]);

  return (
    <canvas
      ref={canvasRef}
      className={className}
      style={{
        position: "absolute",
        inset: 0,
        pointerEvents: "none",
        width: "100%",
        height: "100%",
        ...style,
      }}
    />
  );
}
