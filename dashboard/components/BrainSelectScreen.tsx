"use client";

import { useState, useMemo, useEffect } from "react";

/* ═══════════════════════════════════════════════════════════════════
   Brain Select — Premium Two-Screen RPG Flow
   Screen 1: Three category cards with generated card art + glow effects
   Screen 2: 3-column model grid + slide-out detail panel + mascot guide
   Ported from design_preview.html prototype
   ═══════════════════════════════════════════════════════════════════ */

// ── Data ──

interface QuantDef {
  label: string;
  bits: string;
  intel: number;
  spd: number;
  sizeGB: number;
  size: string;
}

interface ModelDef {
  id: string;
  name: string;
  family: string;
  params: string;
  speed: string;
  category: "speed" | "power" | "specialist";
  tags: string[];
  recommended: boolean;
  desc: string;
  quants: QuantDef[];
}

const MODELS: ModelDef[] = [

  // ── SPEED: Fast, runs on any laptop ──────────────────────────────────────────

  {
    id: "qwen3-0.6b", name: "Qwen 3 0.6B", family: "Alibaba",
    params: "0.6B", speed: "~200 tok/s", category: "speed",
    tags: ["tiny", "instant"], recommended: false,
    desc: "Impossibly small. Half a billion parameters that run on basically anything with a CPU. Think of it as the \"always-on\" model when your companion just needs to reply to a single sentence instantly.",
    quants: [
      { label: "High", bits: "8-bit", intel: 12, spd: 99, sizeGB: 0.6, size: "0.6 GB" },
    ],
  },
  {
    id: "qwen3-1.7b", name: "Qwen 3 1.7B", family: "Alibaba",
    params: "1.7B", speed: "~160 tok/s", category: "speed",
    tags: ["tiny", "fast"], recommended: false,
    desc: "Remarkably smart for its size. Qwen 3's architecture squeezes genuine reasoning ability into 1.7B parameters. A huge upgrade over older small models for the same hardware.",
    quants: [
      { label: "High", bits: "8-bit", intel: 20, spd: 97, sizeGB: 1.7, size: "1.7 GB" },
    ],
  },
  {
    id: "llama-3.2-3b", name: "Llama 3.2 3B", family: "Meta",
    params: "3B", speed: "~90 tok/s", category: "speed",
    tags: ["ultra-light", "mobile"], recommended: false,
    desc: "Meta's newest ultra-lightweight open model. Unbelievably fast and perfect for running in the background on a laptop without draining the battery. Instant responses for everyday tasks.",
    quants: [
      { label: "High", bits: "8-bit", intel: 30, spd: 95, sizeGB: 3.2, size: "3.2 GB" },
    ],
  },
  {
    id: "qwen3-4b", name: "Qwen 3 4B", family: "Alibaba",
    params: "4B", speed: "~80 tok/s", category: "speed",
    tags: ["fast", "smart"], recommended: false,
    desc: "The sweet spot if you only have 4-8 GB of VRAM. Matches or beats models twice its size from 2023, with the added bonus of Qwen 3's new hybrid thinking mode.",
    quants: [
      { label: "Medium", bits: "6-bit", intel: 38, spd: 85, sizeGB: 3.3, size: "3.3 GB" },
    ],
  },
  {
    id: "qwen3-8b", name: "Qwen 3 8B", family: "Alibaba",
    params: "8B", speed: "~55 tok/s", category: "speed",
    tags: ["thinking", "fast"], recommended: true,
    desc: "Alibaba's 2025 flagship small model. Has a hybrid 'thinking' mode that switches between instant replies and deep step-by-step reasoning depending on the difficulty of the question. Genuinely impressive.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 60, spd: 70, sizeGB: 5.2, size: "5.2 GB" },
      { label: "Medium", bits: "6-bit", intel: 65, spd: 60, sizeGB: 6.7, size: "6.7 GB" },
      { label: "High", bits: "8-bit", intel: 68, spd: 48, sizeGB: 8.5, size: "8.5 GB" },
    ],
  },
  {
    id: "qwen-2.5-7b", name: "Qwen 2.5 7B", family: "Alibaba",
    params: "7B", speed: "~60 tok/s", category: "speed",
    tags: ["smart", "punchy"], recommended: false,
    desc: "The previous pound-for-pound champion of small models. Still excellent — more mature and stable than Qwen 3 if you don't want thinking mode.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 50, spd: 75, sizeGB: 4.4, size: "4.4 GB" },
      { label: "Medium", bits: "6-bit", intel: 55, spd: 65, sizeGB: 5.6, size: "5.6 GB" },
      { label: "High", bits: "8-bit", intel: 60, spd: 55, sizeGB: 7.5, size: "7.5 GB" },
    ],
  },
  {
    id: "llama-3.1-8b", name: "Llama 3.1 8B", family: "Meta",
    params: "8B", speed: "~45 tok/s", category: "speed",
    tags: ["general", "reliable"], recommended: false,
    desc: "The open-source gold standard. Battle-tested and reliable for writing, summarizing, and brainstorming. Enormous ecosystem of fine-tunes on top of it.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 45, spd: 70, sizeGB: 4.9, size: "4.9 GB" },
      { label: "Medium", bits: "6-bit", intel: 50, spd: 60, sizeGB: 6.6, size: "6.6 GB" },
      { label: "High", bits: "8-bit", intel: 55, spd: 50, sizeGB: 8.5, size: "8.5 GB" },
    ],
  },
  {
    id: "dolphin-2.9-llama3-8b", name: "Dolphin Llama-3 8B", family: "Community",
    params: "8B", speed: "~45 tok/s", category: "speed",
    tags: ["uncensored", "rebel"], recommended: false,
    desc: "Eric Hartford's famous rogue model. Corporate safety filters stripped out entirely. Highly compliant, completely uncensored, and built for gritty creative writing or unfiltered brainstorming.",
    quants: [
      { label: "Medium", bits: "6-bit", intel: 52, spd: 60, sizeGB: 6.6, size: "6.6 GB" },
    ],
  },
  {
    id: "hermes-3-8b", name: "Hermes 3 Llama-3.1 8B", family: "Nous Research",
    params: "8B", speed: "~45 tok/s", category: "speed",
    tags: ["agent", "uncensored", "functions"], recommended: false,
    desc: "Nous Research's agent specialist. Trained to perfectly follow system prompts, call functions, and stay in character indefinitely without breaking. The ideal brain for AI workflows that need to take real computer actions.",
    quants: [
      { label: "Medium", bits: "6-bit", intel: 58, spd: 60, sizeGB: 6.6, size: "6.6 GB" },
    ],
  },
  {
    id: "gemma-2-9b", name: "Gemma 2 9B", family: "Google",
    params: "9B", speed: "~40 tok/s", category: "speed",
    tags: ["balanced", "modern"], recommended: false,
    desc: "Google's open model built on Gemini research. Clean, balanced, and surprisingly witty. A great all-rounder with strong instruction following.",
    quants: [
      { label: "Medium", bits: "6-bit", intel: 55, spd: 55, sizeGB: 7.0, size: "7.0 GB" },
    ],
  },
  {
    id: "mistral-nemo-12b", name: "Mistral Nemo 12B", family: "Mistral",
    params: "12B", speed: "~35 tok/s", category: "speed",
    tags: ["long-context", "capable"], recommended: false,
    desc: "Built jointly by Mistral and Nvidia. Features a massive 128k context window — perfect for dropping in entire legal documents or codebase diffs for analysis.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 55, spd: 60, sizeGB: 7.1, size: "7.1 GB" },
      { label: "Medium", bits: "6-bit", intel: 60, spd: 45, sizeGB: 9.2, size: "9.2 GB" },
    ],
  },

  // ── POWER: Heavy hitters and cloud APIs ──────────────────────────────────────

  {
    id: "qwen3-14b", name: "Qwen 3 14B", family: "Alibaba",
    params: "14B", speed: "~28 tok/s", category: "power",
    tags: ["thinking", "reasoning"], recommended: true,
    desc: "Qwen 3's 14B is a serious proposition — real-time, deep step-by-step reasoning in a model that still runs on a single 16 GB GPU. Handles nearly everything a power user needs without cloud API costs.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 75, spd: 50, sizeGB: 9.0, size: "9.0 GB" },
      { label: "Medium", bits: "6-bit", intel: 79, spd: 38, sizeGB: 11.4, size: "11.4 GB" },
    ],
  },
  {
    id: "qwen3-30b-a3b", name: "Qwen 3 30B-A3B (MoE)", family: "Alibaba",
    params: "30B (3B active)", speed: "~45 tok/s", category: "power",
    tags: ["MoE", "efficient", "fast"], recommended: false,
    desc: "A Mixture-of-Experts model with 30B total parameters but only 3B active at once. Achieves 30B-level intelligence at 8B-level speed. A brilliant architecture that runs surprisingly fast.",
    quants: [
      { label: "Medium", bits: "6-bit", intel: 82, spd: 48, sizeGB: 18.9, size: "18.9 GB" },
    ],
  },
  {
    id: "qwen3.5-35b-a3b", name: "Qwen 3.5 35B-A3B (MoE)", family: "Alibaba",
    params: "35B (3B active)", speed: "~40 tok/s", category: "power",
    tags: ["MoE", "tool-calling", "efficient", "recommended"], recommended: true,
    desc: "The next-gen Mixture-of-Experts upgrade — 35B total parameters with only 3B active per token, delivering frontier-class intelligence at near-8B speeds. Specifically trained for tool calling and function use. The ideal brain for Fireside's agentic features (browsing, file access, pipelines) on a single 24+ GB GPU.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 85, spd: 55, sizeGB: 20.0, size: "20.0 GB" },
      { label: "Medium", bits: "6-bit", intel: 89, spd: 42, sizeGB: 28.0, size: "28.0 GB" },
    ],
  },
  {
    id: "qwen3-32b", name: "Qwen 3 32B", family: "Alibaba",
    params: "32B", speed: "~18 tok/s", category: "power",
    tags: ["thinking", "frontier-local"], recommended: false,
    desc: "The flagship of local models. Qwen 3 32B with thinking mode enabled is genuinely frontier-level — it destroys many cloud APIs in coding and math benchmarks while running completely offline.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 88, spd: 35, sizeGB: 19.5, size: "19.5 GB" },
      { label: "Medium", bits: "6-bit", intel: 91, spd: 22, sizeGB: 26.0, size: "26.0 GB" },
    ],
  },
  {
    id: "qwq-32b", name: "QwQ 32B (Reasoning)", family: "Alibaba",
    params: "32B", speed: "~18 tok/s", category: "power",
    tags: ["reasoning", "math", "logic"], recommended: false,
    desc: "Alibaba's original answer to DeepSeek R1 and OpenAI o1. Thinks quietly for several minutes before answering. Will crack logic puzzles, proof-read math derivations, and debug cryptic code failures.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 85, spd: 35, sizeGB: 19.5, size: "19.5 GB" },
      { label: "Medium", bits: "6-bit", intel: 88, spd: 25, sizeGB: 26.0, size: "26.0 GB" },
    ],
  },
  {
    id: "qwen-2.5-32b", name: "Qwen 2.5 32B", family: "Alibaba",
    params: "32B", speed: "~20 tok/s", category: "power",
    tags: ["deep", "reasoning"], recommended: false,
    desc: "Alibaba's previous generation 32B. Still excellent — very mature and stable for writing, analysis, and complex instructions. A great choice if you find Qwen 3 32B too slow.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 80, spd: 40, sizeGB: 19.5, size: "19.5 GB" },
      { label: "Medium", bits: "6-bit", intel: 83, spd: 30, sizeGB: 26.0, size: "26.0 GB" },
    ],
  },
  {
    id: "gemma-2-27b", name: "Gemma 2 27B", family: "Google",
    params: "27B", speed: "~22 tok/s", category: "power",
    tags: ["big", "google"], recommended: false,
    desc: "Google's heavyweight open model. Not the strongest 27B available, but benefits from incredible instruction-following finesse inherited from Gemini. Needs ~24 GB VRAM.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 76, spd: 38, sizeGB: 16.4, size: "16.4 GB" },
    ],
  },
  {
    id: "yi-1.5-34b", name: "Yi 1.5 34B", family: "01.AI",
    params: "34B", speed: "~14 tok/s", category: "power",
    tags: ["bilingual", "long-context"], recommended: false,
    desc: "Made by Kai-Fu Lee's 01.AI. Outstanding at switching between Chinese and English without losing a beat. Extremely long context window (200k tokens). Underrated by the western AI community.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 82, spd: 28, sizeGB: 20.6, size: "20.6 GB" },
    ],
  },
  {
    id: "command-r-35b", name: "Command R 35B", family: "Cohere",
    params: "35B", speed: "~15 tok/s", category: "power",
    tags: ["RAG", "roleplay", "grounded"], recommended: false,
    desc: "Built for enterprise, secretly loved by novelists. Never repeats itself, has remarkable emotional intelligence, and cites real-world sources accurately. Great at long-form creative writing.",
    quants: [
      { label: "Medium", bits: "6-bit", intel: 82, spd: 22, sizeGB: 27, size: "27 GB" },
    ],
  },
  {
    id: "llama-3.1-70b", name: "Llama 3.1 70B", family: "Meta",
    params: "70B", speed: "~8 tok/s", category: "power",
    tags: ["frontier", "heavy"], recommended: false,
    desc: "70 billion parameters of raw intelligence. The closest thing to GPT-4 that runs fully local. Requires a 48 GB GPU or dual-GPU rig, but the results are worth it.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 90, spd: 18, sizeGB: 40, size: "40 GB" },
      { label: "Medium", bits: "6-bit", intel: 93, spd: 10, sizeGB: 55, size: "55 GB" },
    ],
  },
  {
    id: "nemotron-70b", name: "Nemotron 70B", family: "Nvidia",
    params: "70B", speed: "~8 tok/s", category: "power",
    tags: ["compliant", "roleplay"], recommended: false,
    desc: "Nvidia took Meta's Llama 3.1 70B and fine-tuned it for near-perfect compliance. It almost never refuses, almost never hallucinates a refusal, and executes complex system prompts flawlessly. A power user's dream.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 92, spd: 17, sizeGB: 40, size: "40 GB" },
    ],
  },
  {
    id: "midnight-miqu-70b", name: "Midnight Miqu 70B", family: "Community",
    params: "70B", speed: "~8 tok/s", category: "power",
    tags: ["roleplay", "creative", "writing"], recommended: false,
    desc: "An absolute legend in the AI roleplay and fiction writing community. Writes like a bestselling author with flawless character voice consistency and zero moralizing.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 88, spd: 18, sizeGB: 41.5, size: "41.5 GB" },
    ],
  },
  {
    id: "glm-4.7", name: "GLM-4.7", family: "Zhipu AI",
    params: "32B-A32B", speed: "~12 tok/s", category: "power",
    tags: ["reasoning", "bilingual", "thinking"], recommended: false,
    desc: "Zhipu's December 2025 flagship. A large Mixture-of-Experts reasoning model with genuine chain-of-thought thinking — trained like China's answer to o1. Handles complex math, legal text, and deep bilingual reasoning that smaller models fumble.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 90, spd: 15, sizeGB: 20, size: "~20 GB" },
    ],
  },
  // Cloud giants
  {
    id: "cloud-deepseek-r1", name: "DeepSeek R1 (Cloud)", family: "DeepSeek",
    params: "671B", speed: "~50 tok/s", category: "power",
    tags: ["cloud", "reasoning", "frontier"], recommended: true,
    desc: "The frontier model that shocked the world and rattled OpenAI stocks. Rivals o1 in math and coding via pure Reinforcement Learning. API costs a fraction of OpenAI. Requires a free API key.",
    quants: [
      { label: "Cloud", bits: "API", intel: 99, spd: 65, sizeGB: 0, size: "0 GB" },
    ],
  },
  {
    id: "cloud-deepseek-v3", name: "DeepSeek V3 (Cloud)", family: "DeepSeek",
    params: "671B", speed: "~60 tok/s", category: "power",
    tags: ["cloud", "fast", "cheap"], recommended: false,
    desc: "DeepSeek's general-purpose frontier model. Matching GPT-4o's capability at roughly 1/10th the API cost. Exceptionally fast, excellent at chat and coding. One of the best value APIs available.",
    quants: [
      { label: "Cloud", bits: "API", intel: 97, spd: 80, sizeGB: 0, size: "0 GB" },
    ],
  },
  {
    id: "cloud-claude-3-5", name: "Claude 3.5 Sonnet (Cloud)", family: "Anthropic",
    params: "~200B+", speed: "~70 tok/s", category: "power",
    tags: ["cloud", "coding", "writing"], recommended: false,
    desc: "Anthropic's masterpiece. The undisputed champion for coding and nuanced creative writing. Produces the most human-feeling text of any AI available today. Cloud API only.",
    quants: [
      { label: "Cloud", bits: "API", intel: 98, spd: 90, sizeGB: 0, size: "0 GB" },
    ],
  },
  {
    id: "cloud-gpt4", name: "GPT-4o (Cloud)", family: "OpenAI",
    params: "~200B+", speed: "~60 tok/s", category: "power",
    tags: ["cloud", "multimodal"], recommended: false,
    desc: "OpenAI's multimodal flagship. The gold standard in general intelligence — handles text, vision, and audio. Huge plugin ecosystem. No local option; data leaves your machine.",
    quants: [
      { label: "Cloud", bits: "API", intel: 98, spd: 85, sizeGB: 0, size: "0 GB" },
    ],
  },
  {
    id: "cloud-grok2", name: "Grok 2 (Cloud)", family: "xAI",
    params: "Unknown", speed: "~70 tok/s", category: "power",
    tags: ["cloud", "rebel", "uncensored"], recommended: false,
    desc: "Elon Musk's xAI model. Famous for abandoning the overly cautious safety filters of OpenAI and Anthropic. Has a sarcastic, rebellious personality baked in. Will tackle topics others decline. Cloud API required.",
    quants: [
      { label: "Cloud", bits: "API", intel: 95, spd: 88, sizeGB: 0, size: "0 GB" },
    ],
  },
  {
    id: "cloud-mistral-large", name: "Mistral Large 2 (Cloud)", family: "Mistral",
    params: "123B", speed: "~55 tok/s", category: "power",
    tags: ["cloud", "european", "multilingual"], recommended: false,
    desc: "Mistral's heavyweight cloud model. 128k context, outstanding multilingual (French, German, Spanish, etc.), and one of the best non-US options for privacy-conscious European users.",
    quants: [
      { label: "Cloud", bits: "API", intel: 96, spd: 80, sizeGB: 0, size: "0 GB" },
    ],
  },
  {
    id: "cloud-kimi", name: "Kimi k1.5 (Cloud)", family: "Moonshot AI",
    params: "Unknown", speed: "~45 tok/s", category: "power",
    tags: ["cloud", "long-context", "reasoning"], recommended: false,
    desc: "Moonshot AI's long-context reasoning model. You can feed it millions of tokens — entire books, entire codebases — and it won't lose a single detail. Kimi k1.5 also has an o1-style reasoning mode for hard problems.",
    quants: [
      { label: "Cloud", bits: "API", intel: 93, spd: 70, sizeGB: 0, size: "0 GB" },
    ],
  },
  {
    id: "cloud-minimax", name: "MiniMax abab6.5 (Cloud)", family: "MiniMax",
    params: "Unknown", speed: "~50 tok/s", category: "power",
    tags: ["cloud", "roleplay", "character"], recommended: false,
    desc: "MiniMax's frontier model. Specifically fine-tuned for deep, long-form character interactions without breaking persona. The best cloud option if you want your AI companion to feel like a real personality.",
    quants: [
      { label: "Cloud", bits: "API", intel: 91, spd: 75, sizeGB: 0, size: "0 GB" },
    ],
  },

  // ── SPECIALIST: Code, Vision, Bilingual ──────────────────────────────────────

  {
    id: "qwen3-coder-8b", name: "Qwen 3 Coder 8B", family: "Alibaba",
    params: "8B", speed: "~55 tok/s", category: "specialist",
    tags: ["code", "fast"], recommended: true,
    desc: "The latest from Alibaba's Qwen 3 Coder series. Excellent autocomplete and code generation across 90+ languages at 8B speed. The best option for coding on mid-range hardware.",
    quants: [
      { label: "Medium", bits: "6-bit", intel: 72, spd: 58, sizeGB: 6.7, size: "6.7 GB" },
    ],
  },
  {
    id: "qwen-2.5-coder-32b", name: "Qwen 2.5 Coder 32B", family: "Alibaba",
    params: "32B", speed: "~20 tok/s", category: "specialist",
    tags: ["code", "autocomplete", "review"], recommended: false,
    desc: "Your personal Senior Staff Engineer. Handles autocomplete, code review, entire repo overhauls, and generation across 90+ programming languages with superb accuracy.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 85, spd: 35, sizeGB: 19.5, size: "19.5 GB" },
      { label: "Medium", bits: "6-bit", intel: 88, spd: 25, sizeGB: 26.0, size: "26.0 GB" },
    ],
  },
  {
    id: "codestral-22b", name: "Codestral 22B", family: "Mistral",
    params: "22B", speed: "~25 tok/s", category: "specialist",
    tags: ["code", "fill-in-middle"], recommended: false,
    desc: "Mistral's dedicated coding model. Blazing fast fill-in-the-middle for every IDE plugin. Exceptionally strong on C++, Rust, and Go — languages where other models struggle.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 80, spd: 42, sizeGB: 13.2, size: "13.2 GB" },
      { label: "Medium", bits: "6-bit", intel: 84, spd: 30, sizeGB: 17.2, size: "17.2 GB" },
    ],
  },
  {
    id: "deepseek-coder-v2", name: "DeepSeek Coder V2", family: "DeepSeek",
    params: "16B", speed: "~22 tok/s", category: "specialist",
    tags: ["code", "math", "MoE"], recommended: false,
    desc: "A Mixture-of-Experts model that excels at hunting down deep codebase bugs and complex math proofs. Brilliant architecture — acts like a 236B model but runs at 16B speed.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 75, spd: 45, sizeGB: 9.5, size: "9.5 GB" },
      { label: "Medium", bits: "6-bit", intel: 80, spd: 35, sizeGB: 12, size: "12 GB" },
    ],
  },
  {
    id: "hermes-3-70b", name: "Hermes 3 Llama-3.1 70B", family: "Nous Research",
    params: "70B", speed: "~8 tok/s", category: "specialist",
    tags: ["agent", "functions", "roleplay"], recommended: false,
    desc: "The 70B version of Nous Research's agent specialist. Perfectly follows system prompts, handles multi-turn tool calling, and holds deep, coherent roleplay for hours without breaking character. The gold standard for agentic workflows.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 92, spd: 17, sizeGB: 40, size: "40 GB" },
    ],
  },
  {
    id: "glm-4-9b", name: "GLM-4 9B Chat", family: "Zhipu AI",
    params: "9B", speed: "~35 tok/s", category: "specialist",
    tags: ["bilingual", "chinese"], recommended: false,
    desc: "Zhipu AI's classic bilingual open model. Phenomenal English/Chinese reasoning that runs on a laptop. Great for tasks that span both languages.",
    quants: [
      { label: "Medium", bits: "6-bit", intel: 65, spd: 45, sizeGB: 8.0, size: "8.0 GB" },
    ],
  },
  {
    id: "glm-4v-9b", name: "GLM-4V 9B (Vision)", family: "Zhipu AI",
    params: "9B", speed: "~30 tok/s", category: "specialist",
    tags: ["vision", "bilingual", "ocr"], recommended: false,
    desc: "Sees images in two languages. Reads documents, screenshots and UI layouts in both Chinese and English. Best bilingual vision model you can run locally.",
    quants: [
      { label: "Medium", bits: "6-bit", intel: 66, spd: 38, sizeGB: 9.5, size: "9.5 GB" },
    ],
  },
  {
    id: "glm-z1-9b", name: "GLM-Z1 9B (Reasoning)", family: "Zhipu AI",
    params: "9B", speed: "~33 tok/s", category: "specialist",
    tags: ["reasoning", "math", "thinking"], recommended: false,
    desc: "Zhipu's dedicated reasoning model. Has a deep-thinking mode that shines on math proofs, logic puzzles and code debugging. Same size as GLM-4 9B but trained specifically to reason step by step.",
    quants: [
      { label: "Medium", bits: "6-bit", intel: 70, spd: 40, sizeGB: 8.0, size: "8.0 GB" },
    ],
  },
  {
    id: "glm-4.7-flash", name: "GLM-4.7 Flash", family: "Zhipu AI",
    params: "30B-A3B", speed: "~55 tok/s", category: "specialist",
    tags: ["fast", "bilingual", "MoE"], recommended: false,
    desc: "The fast lane of the GLM-4.7 family. A 30B Mixture-of-Experts model that only activates 3B params per token — so it's lightning fast while still pulling in the full knowledge of a much larger model. Excellent for bilingual tasks on standard hardware.",
    quants: [
      { label: "Low", bits: "4-bit", intel: 68, spd: 65, sizeGB: 10.5, size: "10.5 GB" },
      { label: "Medium", bits: "6-bit", intel: 72, spd: 55, sizeGB: 14, size: "14 GB" },
    ],
  },
  {
    id: "qwen2-vl-7b", name: "Qwen2-VL 7B (Vision)", family: "Alibaba",
    params: "7B", speed: "~40 tok/s", category: "specialist",
    tags: ["vision", "ocr", "screen"], recommended: true,
    desc: "The current king of open-source vision. Unbelievably good at reading text in images and understanding UI layouts. Let your companion actually 'see' your screen and describe what's on it.",
    quants: [
      { label: "Medium", bits: "6-bit", intel: 65, spd: 50, sizeGB: 6.2, size: "6.2 GB" },
    ],
  },
  {
    id: "pixtral-12b", name: "Pixtral 12B (Vision)", family: "Mistral",
    params: "12B", speed: "~32 tok/s", category: "specialist",
    tags: ["vision", "multimodal"], recommended: false,
    desc: "Mistral's multimodal model that can see. Strong at document understanding and reading complex image layouts. A solid alternative to Qwen2-VL for Western languages.",
    quants: [
      { label: "Medium", bits: "6-bit", intel: 68, spd: 40, sizeGB: 9.5, size: "9.5 GB" },
    ],
  },
];

const CATEGORIES = [
  { id: "speed" as const, img: "/hub/card_speed.png", label: "Speed", color: "#F59E0B", subtitle: "Fast responses, lighter models" },
  { id: "power" as const, img: "/hub/card_power.png", label: "Power", color: "#A78BFA", subtitle: "Deep intelligence, larger models" },
  { id: "specialist" as const, img: "/hub/card_specialist.png", label: "Specialist", color: "#34D399", subtitle: "Code, math, creative writing" },
];

const CAT_LABELS: Record<string, string> = { speed: "\u26A1 SPEED", power: "\uD83E\uDDE0 POWER", specialist: "\uD83D\uDD27 SPECIALIST" };

const MASCOT_MESSAGES: Record<string, string> = {
  categories: "Hey there! Pick a path that fits your style \u2728",
  models: "Click any model card to see the details! \u2605 means I recommend it \uD83E\uDD8A",
  detail: "Try different quality levels! Higher quality = smarter but slower \uD83E\uDDE0",
};

// ── Component ──

interface Props {
  selected?: string;
  onSelect: (modelId: string, label: string, size: string, quant: string) => void;
  detectedVram?: number;
  onBack?: () => void;
  fullscreen?: boolean;
}

export default function BrainSelectScreen({ onSelect, detectedVram = 0, onBack, fullscreen }: Props) {
  const [screen, setScreen] = useState<"categories" | "models">("categories");
  const [category, setCategory] = useState<"speed" | "power" | "specialist">("speed");
  const [search, setSearch] = useState("");
  const [detailModel, setDetailModel] = useState<number | null>(null);
  const [detailQuant, setDetailQuant] = useState(0);
  const [mascotText, setMascotText] = useState(MASCOT_MESSAGES.categories);
  const [species, setSpecies] = useState("fox");

  useEffect(() => {
    const s = typeof window !== "undefined" ? localStorage.getItem("fireside_companion_species") || "fox" : "fox";
    setSpecies(s);
  }, []);

  const mascotSrc = `/hub/mascot_${species}.png`;

  const catColor = CATEGORIES.find(c => c.id === category)?.color || "#F59E0B";

  const filteredModels = useMemo(() => {
    let list = MODELS.filter(m => m.category === category);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(m =>
        m.name.toLowerCase().includes(q) ||
        m.family.toLowerCase().includes(q) ||
        m.tags.some(t => t.includes(q))
      );
    }
    return list;
  }, [category, search]);

  const pickCategory = (cat: typeof category) => {
    setCategory(cat);
    setScreen("models");
    setSearch("");
    setDetailModel(null);
    setMascotText(MASCOT_MESSAGES.models);
  };

  const openDetail = (idx: number) => {
    setDetailModel(idx);
    setDetailQuant(0);
    setMascotText(MASCOT_MESSAGES.detail);
  };

  const closeDetail = () => {
    setDetailModel(null);
    setMascotText(MASCOT_MESSAGES.models);
  };

  const confirmModel = (model: ModelDef, quant: QuantDef) => {
    const label = `${model.name} (${quant.bits})`;
    onSelect(model.id, label, quant.size, quant.bits);
  };

  // Reset mascot when returning to categories
  useEffect(() => {
    if (screen === "categories") setMascotText(MASCOT_MESSAGES.categories);
  }, [screen]);

  const detailModelData = detailModel !== null ? filteredModels[detailModel] : null;
  const detailQuantData = detailModelData ? detailModelData.quants[detailQuant] : null;

  return (
    <div className={`bs-root ${fullscreen ? "bs-fullscreen" : ""}`} style={{ "--cat-color": catColor } as React.CSSProperties}>
      <style>{css}</style>

      {/* ═══ SCREEN 1: CATEGORIES ═══ */}
      {screen === "categories" && (
        <div className="bs-categories">
          <h2 className="bs-title">Choose Your Path</h2>
          <p className="bs-sub">What matters most to you?</p>
          <div className="bs-cat-grid">
            {CATEGORIES.map((cat, i) => (
              <button
                key={cat.id}
                className={`bs-card bs-card-${cat.id}`}
                onClick={() => pickCategory(cat.id)}
                style={{ animationDelay: `${i * 0.12}s, ${i * 0.5}s` }}
              >
                <div className="bs-shimmer" />
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img className="bs-card-icon" src={cat.img} alt={cat.label} />
                <span className="bs-card-label">{cat.label}</span>
                <span className="bs-card-desc">{cat.subtitle}</span>
                <span className="bs-card-count">
                  {MODELS.filter(m => m.category === cat.id).length} MODELS
                </span>
              </button>
            ))}
          </div>
          <div className="bs-hint">Click a card to begin →</div>
          {onBack && (
            <button className="bs-back-link" onClick={onBack}>
              ← Back to recommended
            </button>
          )}
        </div>
      )}

      {/* ═══ SCREEN 2: MODEL GRID ═══ */}
      {screen === "models" && (
        <div className="bs-models">
          {/* Header */}
          <div className="bs-models-header">
            <button className="bs-s2-back" onClick={() => { setScreen("categories"); closeDetail(); }}>
              ← Back
            </button>
            <span className="bs-cat-badge" style={{ color: catColor, borderColor: catColor + "4D", background: catColor + "14" }}>
              {CAT_LABELS[category]}
            </span>
            {detectedVram > 0 && (
              <span className="bs-vram-badge">🖥 {detectedVram} GB VRAM</span>
            )}
          </div>

          {/* Search */}
          <div className="bs-search-wrap">
            <span className="bs-search-icon">🔍</span>
            <input
              className="bs-search"
              placeholder="Search models..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>

          {/* Model grid */}
          <div className="bs-model-grid">
            {filteredModels.length === 0 && (
              <p className="bs-empty">No models found. Try a different search.</p>
            )}
            {filteredModels.map((model, i) => {
              const defaultQ = model.quants[0];
              const overVram = defaultQ.sizeGB > detectedVram && detectedVram > 0 && defaultQ.bits !== "API";
              const isSelected = detailModel === i;
              return (
                <button
                  key={model.id}
                  className={`bs-model-card ${overVram ? "bs-dim-vram" : ""} ${isSelected ? "bs-selected" : ""}`}
                  onClick={() => openDetail(i)}
                  style={{ animationDelay: `${i * 0.07}s` }}
                >
                  {model.recommended && <div className="bs-rec-badge">★ Best Pick</div>}
                  <span className="bs-mc-name">{model.name}</span>
                  <span className="bs-mc-family">{model.family}</span>
                  <div className="bs-mc-badges">
                    <span className="bs-mc-badge">{model.params}</span>
                    <span className="bs-mc-badge">{model.speed}</span>
                  </div>
                  <div className="bs-mc-stats">
                    <div className="bs-mc-stat">
                      <span className="bs-mc-stat-label">🧠</span>
                      <div className="bs-mc-stat-bar"><div className="bs-mc-stat-fill bs-fill-intel" style={{ width: `${defaultQ.intel}%` }} /></div>
                    </div>
                    <div className="bs-mc-stat">
                      <span className="bs-mc-stat-label">⚡</span>
                      <div className="bs-mc-stat-bar"><div className="bs-mc-stat-fill bs-fill-speed" style={{ width: `${defaultQ.spd}%` }} /></div>
                    </div>
                    <div className="bs-mc-stat">
                      <span className="bs-mc-stat-label">💾</span>
                      <div className="bs-mc-stat-bar"><div className="bs-mc-stat-fill bs-fill-size" style={{ width: `${Math.min(100, defaultQ.sizeGB / 40 * 100)}%` }} /></div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* ═══ DETAIL OVERLAY + SLIDE-OUT PANEL ═══ */}
      {detailModel !== null && detailModelData && detailQuantData && (
        <>
          <div className="bs-detail-overlay" onClick={closeDetail} />
          <div className="bs-detail-panel">
            <button className="bs-dp-close" onClick={closeDetail}>✕ Close</button>
            <div className="bs-dp-name">{detailModelData.name}</div>
            <div className="bs-dp-family">{detailModelData.family} · {detailModelData.params} · {detailModelData.speed}</div>
            <div className="bs-dp-tags">
              {detailModelData.tags.map(t => (
                <span key={t} className="bs-dp-tag">{t}</span>
              ))}
            </div>
            <div className="bs-dp-desc">{detailModelData.desc}</div>

            <div className="bs-dp-section-title">Quality</div>
            <div className="bs-dp-quant-pills">
              {detailModelData.quants.map((qo, j) => {
                const qFits = qo.bits === "API" || detectedVram <= 0 || qo.sizeGB <= detectedVram;
                return (
                <button
                  key={j}
                  className={`bs-dp-qpill ${j === detailQuant ? "bs-dp-qpill-active" : ""}`}
                  onClick={() => setDetailQuant(j)}
                >
                  <span>{qo.label}</span>
                  <span className="bs-dp-qpill-bits">{qo.bits}</span>
                  {detectedVram > 0 && qo.bits !== "API" && (
                    <span className={`bs-dp-qpill-fit ${qFits ? "bs-dp-fit-ok" : "bs-dp-fit-warn"}`}>
                      {qFits ? "✓ Fits" : "⚠ Big"}
                    </span>
                  )}
                </button>
                );
              })}
            </div>

            <div className="bs-dp-section-title">Stats</div>
            <div className="bs-dp-stats">
              <div className="bs-dp-stat-row">
                <span className="bs-dp-stat-icon">🧠</span>
                <span className="bs-dp-stat-name">Intelligence</span>
                <div className="bs-dp-stat-bar-bg"><div className="bs-dp-stat-fill bs-dp-intel" style={{ width: `${detailQuantData.intel}%` }} /></div>
                <span className="bs-dp-stat-value">{detailModelData.params}</span>
              </div>
              <div className="bs-dp-stat-row">
                <span className="bs-dp-stat-icon">⚡</span>
                <span className="bs-dp-stat-name">Speed</span>
                <div className="bs-dp-stat-bar-bg"><div className="bs-dp-stat-fill bs-dp-speed" style={{ width: `${detailQuantData.spd}%` }} /></div>
                <span className="bs-dp-stat-value">~{Math.round(detailQuantData.spd * 1.1)} tok/s</span>
              </div>
              <div className="bs-dp-stat-row">
                <span className="bs-dp-stat-icon">💾</span>
                <span className="bs-dp-stat-name">Size</span>
                <div className="bs-dp-stat-bar-bg"><div className="bs-dp-stat-fill bs-dp-size" style={{ width: `${Math.min(100, detailQuantData.sizeGB / 40 * 100)}%` }} /></div>
                <span className="bs-dp-stat-value">{detailQuantData.size}</span>
              </div>
            </div>

            {/* VRAM warning */}
            {detectedVram > 0 && detailQuantData.sizeGB > detectedVram && detailQuantData.bits !== "API" && (
              <p className="bs-dp-vram-warn">
                ⚠ Needs ~{detailQuantData.sizeGB} GB VRAM (you have {detectedVram} GB)
              </p>
            )}

            <button className="bs-dp-select" onClick={() => confirmModel(detailModelData, detailQuantData)}>
              Select {detailModelData.name} · {detailQuantData.bits} →
            </button>
          </div>
        </>
      )}

      {/* ═══ MASCOT GUIDE ═══ */}
      <div className="bs-mascot">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className="bs-mascot-img" src={mascotSrc} alt="Guide" />
        <div className="bs-mascot-bubble">{mascotText}</div>
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════
// CSS — ported from design_preview.html
// ════════════════════════════════════════════════════════════════════

const css = `
  .bs-root {
    width: 100%; min-height: 100%;
    font-family: 'Outfit', 'Inter', system-ui, sans-serif;
    color: #F0DCC8;
    background: #060609;
    position: relative;
  }
  .bs-fullscreen {
    position: fixed; inset: 0; z-index: 100;
    background: #060609;
    overflow-y: auto;
  }

  /* ═══ SCREEN 1: CATEGORIES ═══ */
  .bs-categories {
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    padding: 40px 24px; min-height: 100vh; width: 100%;
    animation: bsFadeUp 0.5s ease forwards;
  }
  @keyframes bsFadeUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
  }
  .bs-title {
    font-size: 32px; font-weight: 900; margin: 0 0 6px;
    background: linear-gradient(135deg, #F0DCC8 0%, #FBBF24 50%, #D97706 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .bs-sub { font-size: 14px; color: #4A3D30; margin: 0 0 48px; }
  .bs-cat-grid {
    display: grid; grid-template-columns: repeat(3, 200px);
    gap: 28px;
  }
  .bs-hint {
    margin-top: 48px; font-size: 11px; color: #2A2520;
    letter-spacing: 1px; text-transform: uppercase;
    animation: bsFadeIn 1s 0.8s both;
  }
  @keyframes bsFadeIn { from { opacity: 0; } to { opacity: 1; } }
  .bs-back-link {
    margin-top: 16px;
    background: none; border: none; cursor: pointer;
    color: #5A4D40; font-size: 12px; font-family: inherit;
    transition: color 0.2s;
  }
  .bs-back-link:hover { color: #F0DCC8; }

  /* Card */
  .bs-card {
    position: relative; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 16px;
    padding: 48px 24px 40px; border-radius: 22px; aspect-ratio: 3 / 4;
    cursor: pointer; font-family: inherit;
    background: radial-gradient(ellipse at 50% 25%, var(--glow-soft) 0%, rgba(8,8,14,0.98) 55%);
    border: 2px solid var(--border-idle);
    box-shadow: 0 0 35px var(--shadow-outer), 0 0 15px var(--shadow-diffuse), inset 0 0 25px rgba(0,0,0,0.3);
    transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
    animation: bsCardIn 0.7s cubic-bezier(0.34, 1.56, 0.64, 1) both, bsBorderPulse 3s ease-in-out infinite alternate;
  }
  @keyframes bsCardIn { from { opacity: 0; transform: translateY(50px) scale(0.8); } to { opacity: 1; transform: translateY(0) scale(1); } }
  @keyframes bsBorderPulse { 0% { border-color: var(--border-idle); } 100% { border-color: var(--border-glow); box-shadow: 0 0 45px var(--shadow-outer), 0 0 20px var(--shadow-diffuse); } }

  .bs-card::before {
    content: ''; position: absolute; top: -30px; left: 50%; width: 220px; height: 220px;
    transform: translateX(-50%); border-radius: 50%;
    background: radial-gradient(circle, var(--glow-strong) 0%, var(--glow-mid) 35%, transparent 65%);
    z-index: -1; pointer-events: none; animation: bsOuterGlow 3.5s ease-in-out infinite alternate; opacity: 0.6;
  }
  @keyframes bsOuterGlow { 0% { opacity: 0.4; transform: translateX(-50%) scale(0.85); } 100% { opacity: 0.8; transform: translateX(-50%) scale(1.1); } }

  .bs-card:hover {
    transform: translateY(-12px) scale(1.06);
    border-color: var(--border-hover);
    box-shadow: 0 30px 80px var(--shadow-outer), 0 0 120px var(--shadow-diffuse), 0 0 40px var(--shadow-outer);
  }
  .bs-card:hover::before { opacity: 1; width: 280px; height: 280px; }
  .bs-card:hover .bs-card-icon { filter: drop-shadow(0 0 50px var(--glow-strong)); transform: translateY(-4px) scale(1.1); }

  .bs-shimmer { position: absolute; inset: 0; border-radius: 22px; overflow: hidden; pointer-events: none; }
  .bs-shimmer::after {
    content: ''; position: absolute; inset: -50% -50%;
    background: linear-gradient(105deg, transparent 30%, var(--shimmer-color) 50%, transparent 100%);
    animation: bsSweep 6s ease-in-out infinite;
  }
  @keyframes bsSweep { 0% { left: -100%; } 35%, 100% { left: 250%; } }

  .bs-card-icon {
    width: 140px; height: 140px; object-fit: contain;
    position: relative; z-index: 2;
    filter: drop-shadow(0 0 30px var(--glow-strong));
    animation: bsIconBreathe 5s ease-in-out infinite;
    mix-blend-mode: screen;
    -webkit-mask-image: radial-gradient(circle, white 35%, transparent 70%);
    mask-image: radial-gradient(circle, white 35%, transparent 70%);
  }
  @keyframes bsIconBreathe { 0%, 100% { transform: translateY(0) scale(1); } 50% { transform: translateY(-7px) scale(1.04); } }
  .bs-card-label {
    font-size: 18px; font-weight: 900; color: var(--accent);
    text-transform: uppercase; letter-spacing: 4px;
    position: relative; z-index: 2;
    text-shadow: 0 0 30px var(--glow-strong);
  }
  .bs-card-desc {
    font-size: 12px; color: #5A4D40; text-align: center; line-height: 1.5;
    position: relative; z-index: 2; max-width: 140px;
  }
  .bs-card-count {
    font-size: 9px; color: #3A3530; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1.5px;
    position: relative; z-index: 2;
  }

  /* Card color variants */
  .bs-card-speed { --accent: #F59E0B; --glow-strong: rgba(245,158,11,0.25); --glow-mid: rgba(217,119,6,0.10); --glow-soft: rgba(245,158,11,0.06); --border-idle: rgba(245,158,11,0.30); --border-hover: rgba(245,158,11,0.85); --border-glow: rgba(245,158,11,0.55); --border-glow-dim: rgba(245,158,11,0.25); --shadow-outer: rgba(245,158,11,0.12); --shadow-diffuse: rgba(245,158,11,0.06); --shimmer-color: rgba(245,158,11,0.04); }
  .bs-card-power { --accent: #A78BFA; --glow-strong: rgba(167,139,250,0.25); --glow-mid: rgba(139,92,246,0.10); --glow-soft: rgba(167,139,250,0.06); --border-idle: rgba(167,139,250,0.30); --border-hover: rgba(167,139,250,0.85); --border-glow: rgba(167,139,250,0.55); --border-glow-dim: rgba(167,139,250,0.25); --shadow-outer: rgba(167,139,250,0.12); --shadow-diffuse: rgba(167,139,250,0.06); --shimmer-color: rgba(167,139,250,0.04); }
  .bs-card-specialist { --accent: #34D399; --glow-strong: rgba(52,211,153,0.25); --glow-mid: rgba(16,185,129,0.10); --glow-soft: rgba(52,211,153,0.06); --border-idle: rgba(52,211,153,0.30); --border-hover: rgba(52,211,153,0.85); --border-glow: rgba(52,211,153,0.55); --border-glow-dim: rgba(52,211,153,0.25); --shadow-outer: rgba(52,211,153,0.12); --shadow-diffuse: rgba(52,211,153,0.06); --shimmer-color: rgba(52,211,153,0.04); }

  /* ═══ SCREEN 2: MODEL GRID ═══ */
  .bs-models {
    width: 100%; max-width: 960px;
    min-height: 100vh; padding: 28px 24px;
    margin: 0 auto;
    animation: bsFadeUp 0.4s ease forwards;
  }
  .bs-models-header {
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 20px;
  }
  .bs-s2-back {
    padding: 8px 16px; border-radius: 10px;
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
    color: #8A7A6A; font-size: 13px; font-weight: 600;
    cursor: pointer; font-family: inherit; transition: all 0.3s;
  }
  .bs-s2-back:hover { background: rgba(255,255,255,0.08); color: #F0DCC8; }
  .bs-cat-badge {
    padding: 6px 16px; border-radius: 8px;
    font-size: 12px; font-weight: 800;
    text-transform: uppercase; letter-spacing: 2px;
    border: 1px solid;
  }
  .bs-vram-badge {
    margin-left: auto; padding: 6px 14px; border-radius: 8px;
    font-size: 11px; color: #6A5A4A; font-weight: 600;
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
  }

  /* Search */
  .bs-search-wrap { position: relative; margin-bottom: 16px; }
  .bs-search-icon {
    position: absolute; left: 18px; top: 50%; transform: translateY(-50%);
    font-size: 16px; pointer-events: none; opacity: 0.6;
  }
  .bs-search {
    width: 100%; padding: 16px 20px 16px 48px; border-radius: 16px;
    border: 1.5px solid rgba(245,158,11,0.12);
    background: rgba(245,158,11,0.03);
    color: #F0DCC8; font-size: 15px; font-family: inherit; outline: none;
    transition: all 0.3s; box-shadow: 0 0 20px rgba(245,158,11,0.04);
  }
  .bs-search:focus {
    border-color: color-mix(in srgb, var(--cat-color) 50%, transparent);
    box-shadow: 0 0 40px color-mix(in srgb, var(--cat-color) 12%, transparent);
    background: rgba(245,158,11,0.05);
  }
  .bs-search::placeholder { color: #4A3D30; font-weight: 500; }

  /* Model grid */
  .bs-model-grid {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;
  }
  .bs-empty { color: #3A3530; text-align: center; font-size: 13px; padding: 40px 0; grid-column: 1/-1; }

  .bs-model-card {
    border-radius: 16px;
    background: linear-gradient(135deg, rgba(255,255,255,0.035), rgba(255,255,255,0.015));
    border: 1.5px solid rgba(255,255,255,0.08);
    backdrop-filter: blur(10px);
    padding: 20px; cursor: pointer; font-family: inherit;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    animation: bsCardSlide 0.4s ease both;
    display: flex; flex-direction: column; gap: 12px;
    position: relative; text-align: left; color: inherit;
  }
  @keyframes bsCardSlide { from { opacity: 0; transform: translateY(20px) scale(0.95); } to { opacity: 1; transform: translateY(0) scale(1); } }
  .bs-model-card:hover {
    transform: translateY(-6px) scale(1.02);
    border-color: color-mix(in srgb, var(--cat-color) 35%, transparent);
    box-shadow: 0 12px 40px color-mix(in srgb, var(--cat-color) 8%, transparent), 0 0 20px color-mix(in srgb, var(--cat-color) 5%, transparent);
  }
  .bs-selected {
    border-color: color-mix(in srgb, var(--cat-color) 50%, transparent);
    box-shadow: 0 0 30px color-mix(in srgb, var(--cat-color) 12%, transparent);
  }
  .bs-dim-vram { opacity: 0.35; pointer-events: none; }

  .bs-rec-badge {
    position: absolute; top: -6px; right: -6px;
    padding: 3px 10px; border-radius: 8px;
    font-size: 9px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px;
    background: linear-gradient(135deg, #D97706, #F59E0B);
    color: #0A0A0A;
    box-shadow: 0 2px 12px rgba(245,158,11,0.4);
    animation: bsRecPulse 2s ease-in-out infinite alternate;
  }
  @keyframes bsRecPulse { 0% { box-shadow: 0 2px 12px rgba(245,158,11,0.3); } 100% { box-shadow: 0 4px 20px rgba(245,158,11,0.6); } }

  .bs-mc-name { font-size: 15px; font-weight: 700; }
  .bs-mc-family { font-size: 11px; color: #5A4D40; }
  .bs-mc-badges { display: flex; gap: 6px; margin-top: 2px; }
  .bs-mc-badge {
    padding: 3px 8px; border-radius: 6px; font-size: 10px; font-weight: 700;
    color: #6A5A4A; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06);
  }
  .bs-mc-stats { display: flex; flex-direction: column; gap: 6px; margin-top: auto; }
  .bs-mc-stat { display: flex; align-items: center; gap: 6px; }
  .bs-mc-stat-label { font-size: 9px; font-weight: 700; color: #4A3D30; width: 16px; text-align: center; }
  .bs-mc-stat-bar { flex: 1; height: 5px; border-radius: 3px; background: rgba(255,255,255,0.04); overflow: hidden; }
  .bs-mc-stat-fill { height: 100%; border-radius: 3px; transition: width 0.6s ease; }
  .bs-fill-intel { background: linear-gradient(90deg, #DB2777, #F472B6); }
  .bs-fill-speed { background: linear-gradient(90deg, #10B981, #34D399); }
  .bs-fill-size { background: linear-gradient(90deg, #3B82F6, #60A5FA); }

  /* ═══ DETAIL PANEL ═══ */
  .bs-detail-overlay {
    position: fixed; inset: 0; z-index: 50;
    background: rgba(0,0,0,0.5); backdrop-filter: blur(4px);
    animation: bsFadeIn 0.2s ease;
  }
  .bs-detail-panel {
    position: fixed; top: 0; right: 0; bottom: 0; z-index: 51;
    width: 400px;
    background: linear-gradient(180deg, #0C0C14 0%, #080810 100%);
    border-left: 1.5px solid rgba(255,255,255,0.08);
    box-shadow: -20px 0 60px rgba(0,0,0,0.5);
    padding: 28px 24px; overflow-y: auto;
    animation: bsSlideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  }
  @keyframes bsSlideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }

  .bs-dp-close {
    position: absolute; top: 16px; right: 16px;
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px; padding: 6px 12px; color: #6A5A4A;
    font-size: 12px; cursor: pointer; font-family: inherit; transition: all 0.2s;
  }
  .bs-dp-close:hover { background: rgba(255,255,255,0.1); color: #F0DCC8; }

  .bs-dp-name { font-size: 22px; font-weight: 800; margin-bottom: 4px; }
  .bs-dp-family { font-size: 13px; color: #5A4D40; margin-bottom: 16px; }
  .bs-dp-tags { display: flex; gap: 6px; margin-bottom: 20px; flex-wrap: wrap; }
  .bs-dp-tag {
    padding: 4px 12px; border-radius: 6px; font-size: 10px;
    font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;
    color: var(--cat-color);
    background: color-mix(in srgb, var(--cat-color) 8%, transparent);
    border: 1px solid color-mix(in srgb, var(--cat-color) 15%, transparent);
  }
  .bs-dp-desc {
    font-size: 13px; color: #8A7A6A; line-height: 1.7; margin-bottom: 20px;
    padding: 14px 16px; border-radius: 12px;
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);
  }
  .bs-dp-section-title {
    font-size: 10px; font-weight: 700; color: #5A4D40;
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px;
  }
  .bs-dp-quant-pills { display: flex; gap: 6px; margin-bottom: 24px; }
  .bs-dp-qpill {
    flex: 1; padding: 10px 8px; border-radius: 12px; cursor: pointer;
    background: rgba(255,255,255,0.03); border: 1.5px solid rgba(255,255,255,0.08);
    color: #6A5A4A; font-family: inherit; font-size: 13px; font-weight: 700;
    display: flex; flex-direction: column; align-items: center; gap: 3px; transition: all 0.3s;
  }
  .bs-dp-qpill:hover { background: rgba(255,255,255,0.06); border-color: color-mix(in srgb, var(--cat-color) 30%, transparent); }
  .bs-dp-qpill-active {
    background: color-mix(in srgb, var(--cat-color) 15%, transparent);
    border-color: var(--cat-color); color: var(--cat-color);
    box-shadow: 0 0 25px color-mix(in srgb, var(--cat-color) 15%, transparent);
  }
  .bs-dp-qpill-bits { font-size: 10px; font-weight: 600; opacity: 0.5; }

  .bs-dp-stats { display: flex; flex-direction: column; gap: 14px; margin-bottom: 24px; }
  .bs-dp-stat-row { display: flex; align-items: center; gap: 10px; }
  .bs-dp-stat-icon { font-size: 15px; width: 22px; text-align: center; filter: saturate(1.4); }
  .bs-dp-stat-name { font-size: 11px; font-weight: 700; color: #6A5A4A; text-transform: uppercase; width: 85px; letter-spacing: 0.5px; }
  .bs-dp-stat-bar-bg {
    flex: 1; height: 12px; border-radius: 6px;
    background: rgba(255,255,255,0.04); overflow: hidden;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.4);
  }
  .bs-dp-stat-fill {
    height: 100%; border-radius: 6px; position: relative; overflow: hidden;
    transition: width 0.8s cubic-bezier(0.16, 1, 0.3, 1);
  }
  .bs-dp-stat-fill::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 50%;
    border-radius: 6px 6px 0 0;
    background: linear-gradient(180deg, rgba(255,255,255,0.3), transparent);
  }
  .bs-dp-stat-fill::after {
    content: ''; position: absolute; top: 0; left: -100%; width: 60%; height: 100%;
    border-radius: 6px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
    animation: bsBarShine 3s ease-in-out infinite;
  }
  @keyframes bsBarShine { 0% { left: -100%; } 50%, 100% { left: 200%; } }
  .bs-dp-intel { background: linear-gradient(90deg, #9D174D, #DB2777, #EC4899, #F472B6); box-shadow: 0 0 12px rgba(236,72,153,0.35); }
  .bs-dp-speed { background: linear-gradient(90deg, #047857, #059669, #10B981, #34D399); box-shadow: 0 0 12px rgba(16,185,129,0.35); }
  .bs-dp-size { background: linear-gradient(90deg, #1D4ED8, #2563EB, #3B82F6, #60A5FA); box-shadow: 0 0 12px rgba(59,130,246,0.35); }
  .bs-dp-stat-value { font-size: 11px; color: #6A5A4A; width: 65px; text-align: right; font-weight: 700; }

  .bs-dp-vram-warn {
    font-size: 11px; color: #EF4444; font-weight: 600;
    margin: 0 0 12px; padding: 8px 12px; border-radius: 8px;
    background: rgba(239,68,68,0.06); border: 1px solid rgba(239,68,68,0.15);
  }

  .bs-dp-qpill-fit {
    font-size: 9px; font-weight: 700; letter-spacing: 0.5px;
    padding: 2px 6px; border-radius: 4px; margin-left: 4px;
  }
  .bs-dp-fit-ok {
    color: #10B981; background: rgba(16,185,129,0.1);
  }
  .bs-dp-fit-warn {
    color: #F59E0B; background: rgba(245,158,11,0.1);
  }

  .bs-dp-select {
    width: 100%; padding: 16px; border-radius: 14px; border: none;
    cursor: pointer; font-family: inherit; font-size: 15px; font-weight: 800;
    background: linear-gradient(135deg, #D97706, #F59E0B);
    color: #0A0A0A; box-shadow: 0 4px 24px rgba(245,158,11,0.25);
    transition: all 0.3s;
  }
  .bs-dp-select:hover { transform: translateY(-2px); box-shadow: 0 8px 32px rgba(245,158,11,0.4); }

  /* ═══ MASCOT ═══ */
  .bs-mascot {
    position: fixed; bottom: 16px; left: 20px; z-index: 40;
    display: flex; align-items: flex-end; gap: 0;
    pointer-events: none;
  }
  .bs-mascot-img {
    width: 180px; height: 180px; object-fit: contain;
    filter: drop-shadow(0 4px 30px rgba(245,158,11,0.4));
    animation: bsMascotBob 4s ease-in-out infinite;
    mix-blend-mode: screen;
    -webkit-mask-image: radial-gradient(circle, white 30%, transparent 60%);
    mask-image: radial-gradient(circle, white 30%, transparent 60%);
  }
  @keyframes bsMascotBob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
  .bs-mascot-bubble {
    position: relative; bottom: 50px;
    background: rgba(20,18,28,0.92); border: 1.5px solid rgba(245,158,11,0.20);
    border-radius: 14px 14px 14px 4px;
    padding: 10px 14px; max-width: 220px;
    font-size: 12px; color: #C4A882; line-height: 1.5;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    pointer-events: auto;
  }

  /* ═══ Responsive ═══ */
  @media (max-width: 700px) {
    .bs-cat-grid { grid-template-columns: 1fr; max-width: 240px; }
    .bs-model-grid { grid-template-columns: 1fr; }
    .bs-detail-panel { width: 100%; }
    .bs-mascot { display: none; }
  }
`;
