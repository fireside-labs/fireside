"""
brain-installer/registry.py — Curated model registry.

Each entry specifies: name, params, VRAM requirements, download sources,
estimated performance, and category for the consumer UI.

Users can also add custom models via add_custom_model().
"""
from __future__ import annotations

import json
from pathlib import Path

MODELS = [
    # ==========================================
    # LIGHTWEIGHT (3-4 GB VRAM)
    # ==========================================
    {
        "id": "phi-3-mini",
        "name": "Quick & Light",
        "family": "Phi",
        "params": "3.8B",
        "min_vram": 3,
        "recommended_vram": 4,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/Phi-3-mini-128k-instruct-GGUF/resolve/main/Phi-3-mini-128k-instruct-Q4_K_M.gguf",
        "omlx_id": "mlx-community/Phi-3-mini-128k-instruct-4bit",
        "tok_s_estimate": 65,
        "context": 128000,
        "tier": "free",
        "category": "general",
        "description": "Fast responses, good for chat and simple tasks. 128K context.",
    },
    {
        "id": "deepseek-r1-1.5b",
        "name": "DeepSeek Nano",
        "family": "DeepSeek",
        "params": "1.5B",
        "min_vram": 2,
        "recommended_vram": 3,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/DeepSeek-R1-Distill-Qwen-1.5B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf",
        "omlx_id": "mlx-community/DeepSeek-R1-Distill-Qwen-1.5B-4bit",
        "tok_s_estimate": 90,
        "context": 32768,
        "tier": "free",
        "category": "reasoning",
        "description": "Tiny reasoning model. Surprisingly good for its size.",
    },
    {
        "id": "gemma-3-4b",
        "name": "Gemma Lite",
        "family": "Gemma",
        "params": "4B",
        "min_vram": 3,
        "recommended_vram": 4,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/gemma-3-4b-it-GGUF/resolve/main/gemma-3-4b-it-Q4_K_M.gguf",
        "omlx_id": "mlx-community/gemma-3-4b-it-4bit",
        "tok_s_estimate": 70,
        "context": 32768,
        "tier": "free",
        "category": "general",
        "description": "Google's smallest Gemma 3. Fast and capable.",
    },

    # ==========================================
    # SMALL (6-8 GB VRAM)
    # ==========================================
    {
        "id": "llama-3.1-8b",
        "name": "Smart & Fast",
        "family": "Llama",
        "params": "8B",
        "min_vram": 6,
        "recommended_vram": 8,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "omlx_id": "mlx-community/Meta-Llama-3.1-8B-Instruct-4bit",
        "tok_s_estimate": 45,
        "context": 131072,
        "tier": "free",
        "category": "general",
        "description": "Great all-rounder — coding, writing, and reasoning. 128K context.",
    },
    {
        "id": "deepseek-r1-7b",
        "name": "DeepSeek Reason 7B",
        "family": "DeepSeek",
        "params": "7B",
        "min_vram": 5,
        "recommended_vram": 8,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/DeepSeek-R1-Distill-Qwen-7B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf",
        "omlx_id": "mlx-community/DeepSeek-R1-Distill-Qwen-7B-4bit",
        "tok_s_estimate": 50,
        "context": 32768,
        "tier": "free",
        "category": "reasoning",
        "description": "Chain-of-thought reasoning in a small package.",
    },
    {
        "id": "mistral-7b",
        "name": "Mistral 7B",
        "family": "Mistral",
        "params": "7B",
        "min_vram": 5,
        "recommended_vram": 8,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF/resolve/main/Mistral-7B-Instruct-v0.3-Q4_K_M.gguf",
        "omlx_id": "mlx-community/Mistral-7B-Instruct-v0.3-4bit",
        "tok_s_estimate": 50,
        "context": 32768,
        "tier": "free",
        "category": "general",
        "description": "Efficient European model. Good at following instructions.",
    },
    {
        "id": "qwen-3-8b",
        "name": "Qwen 3 8B",
        "family": "Qwen",
        "params": "8B",
        "min_vram": 6,
        "recommended_vram": 8,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/Qwen3-8B-GGUF/resolve/main/Qwen3-8B-Q4_K_M.gguf",
        "omlx_id": "mlx-community/Qwen3-8B-4bit",
        "tok_s_estimate": 45,
        "context": 32768,
        "tier": "free",
        "category": "general",
        "description": "Alibaba's latest. Strong multilingual + reasoning.",
    },
    {
        "id": "gemma-2-9b",
        "name": "Gemma 2 9B",
        "family": "Gemma",
        "params": "9B",
        "min_vram": 6,
        "recommended_vram": 8,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/gemma-2-9b-it-GGUF/resolve/main/gemma-2-9b-it-Q4_K_M.gguf",
        "omlx_id": "mlx-community/gemma-2-9b-it-4bit",
        "tok_s_estimate": 40,
        "context": 8192,
        "tier": "free",
        "category": "general",
        "description": "Google's Gemma 2. Strong reasoning.",
    },
    {
        "id": "qwen-2.5-coder-7b",
        "name": "Qwen Coder 7B",
        "family": "Qwen",
        "params": "7B",
        "min_vram": 5,
        "recommended_vram": 8,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/main/Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf",
        "omlx_id": "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
        "tok_s_estimate": 50,
        "context": 32768,
        "tier": "free",
        "category": "coding",
        "description": "Code-specialized. Best small coding model available.",
    },
    {
        "id": "deepseek-coder-v2-lite",
        "name": "DeepSeek Coder Lite",
        "family": "DeepSeek",
        "params": "7B",
        "min_vram": 5,
        "recommended_vram": 8,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF/resolve/main/DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf",
        "omlx_id": "mlx-community/DeepSeek-Coder-V2-Lite-Instruct-4bit",
        "tok_s_estimate": 45,
        "context": 32768,
        "tier": "free",
        "category": "coding",
        "description": "DeepSeek's code specialist. Great for generation and debugging.",
    },

    # ==========================================
    # MEDIUM (10-16 GB VRAM)
    # ==========================================
    {
        "id": "gemma-3-12b",
        "name": "Gemma 3 12B",
        "family": "Gemma",
        "params": "12B",
        "min_vram": 8,
        "recommended_vram": 12,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/gemma-3-12b-it-GGUF/resolve/main/gemma-3-12b-it-Q4_K_M.gguf",
        "omlx_id": "mlx-community/gemma-3-12b-it-4bit",
        "tok_s_estimate": 35,
        "context": 32768,
        "tier": "free",
        "category": "general",
        "description": "Google's mid-range Gemma 3. Strong instruction following.",
    },
    {
        "id": "mistral-nemo-12b",
        "name": "Mistral Nemo",
        "family": "Mistral",
        "params": "12B",
        "min_vram": 8,
        "recommended_vram": 12,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/Mistral-Nemo-Instruct-2407-GGUF/resolve/main/Mistral-Nemo-Instruct-2407-Q4_K_M.gguf",
        "omlx_id": "mlx-community/Mistral-Nemo-Instruct-2407-4bit",
        "tok_s_estimate": 35,
        "context": 128000,
        "tier": "free",
        "category": "general",
        "description": "Mistral + NVIDIA collab. 128K context, great reasoning.",
    },
    {
        "id": "phi-4-14b",
        "name": "Phi-4",
        "family": "Phi",
        "params": "14B",
        "min_vram": 10,
        "recommended_vram": 16,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/phi-4-GGUF/resolve/main/phi-4-Q4_K_M.gguf",
        "omlx_id": "mlx-community/phi-4-4bit",
        "tok_s_estimate": 30,
        "context": 16384,
        "tier": "free",
        "category": "reasoning",
        "description": "Microsoft's best small model. Exceptional at math and reasoning.",
    },
    {
        "id": "qwen-2.5-14b",
        "name": "Qwen 2.5 14B",
        "family": "Qwen",
        "params": "14B",
        "min_vram": 10,
        "recommended_vram": 16,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/Qwen2.5-14B-Instruct-GGUF/resolve/main/Qwen2.5-14B-Instruct-Q4_K_M.gguf",
        "omlx_id": "mlx-community/Qwen2.5-14B-Instruct-4bit",
        "tok_s_estimate": 30,
        "context": 32768,
        "tier": "free",
        "category": "general",
        "description": "More knowledge, better at complex tasks.",
    },
    {
        "id": "deepseek-r1-14b",
        "name": "DeepSeek Reason 14B",
        "family": "DeepSeek",
        "params": "14B",
        "min_vram": 10,
        "recommended_vram": 16,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/DeepSeek-R1-Distill-Qwen-14B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf",
        "omlx_id": "mlx-community/DeepSeek-R1-Distill-Qwen-14B-4bit",
        "tok_s_estimate": 28,
        "context": 32768,
        "tier": "free",
        "category": "reasoning",
        "description": "Serious chain-of-thought reasoning at 14B scale.",
    },
    {
        "id": "qwen-2.5-coder-14b",
        "name": "Qwen Coder 14B",
        "family": "Qwen",
        "params": "14B",
        "min_vram": 10,
        "recommended_vram": 16,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/Qwen2.5-Coder-14B-Instruct-GGUF/resolve/main/Qwen2.5-Coder-14B-Instruct-Q4_K_M.gguf",
        "omlx_id": "mlx-community/Qwen2.5-Coder-14B-Instruct-4bit",
        "tok_s_estimate": 28,
        "context": 32768,
        "tier": "free",
        "category": "coding",
        "description": "Best mid-range coding model. Understands complex codebases.",
    },

    # ==========================================
    # LARGE (24-48 GB VRAM)
    # ==========================================
    {
        "id": "mistral-small-24b",
        "name": "Mistral Small",
        "family": "Mistral",
        "params": "24B",
        "min_vram": 16,
        "recommended_vram": 24,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/Mistral-Small-24B-Instruct-2501-GGUF/resolve/main/Mistral-Small-24B-Instruct-2501-Q4_K_M.gguf",
        "omlx_id": "mlx-community/Mistral-Small-24B-Instruct-2501-4bit",
        "tok_s_estimate": 22,
        "context": 32768,
        "tier": "free",
        "category": "general",
        "description": "Mistral's mid-tier. Excellent instruction following.",
    },
    {
        "id": "gemma-3-27b",
        "name": "Gemma 3 27B",
        "family": "Gemma",
        "params": "27B",
        "min_vram": 18,
        "recommended_vram": 24,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/gemma-3-27b-it-GGUF/resolve/main/gemma-3-27b-it-Q4_K_M.gguf",
        "omlx_id": "mlx-community/gemma-3-27b-it-4bit",
        "tok_s_estimate": 20,
        "context": 32768,
        "tier": "free",
        "category": "general",
        "description": "Google's largest Gemma 3. Near-frontier quality.",
    },
    {
        "id": "qwen-3-32b",
        "name": "Qwen 3 32B",
        "family": "Qwen",
        "params": "32B",
        "min_vram": 20,
        "recommended_vram": 32,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/Qwen3-32B-GGUF/resolve/main/Qwen3-32B-Q4_K_M.gguf",
        "omlx_id": "mlx-community/Qwen3-32B-4bit",
        "tok_s_estimate": 18,
        "context": 32768,
        "tier": "free",
        "category": "general",
        "description": "Alibaba's powerhouse. Excellent at complex multi-step tasks.",
    },
    {
        "id": "deepseek-r1-32b",
        "name": "DeepSeek Reason 32B",
        "family": "DeepSeek",
        "params": "32B",
        "min_vram": 20,
        "recommended_vram": 32,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/DeepSeek-R1-Distill-Qwen-32B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-32B-Q4_K_M.gguf",
        "omlx_id": "mlx-community/DeepSeek-R1-Distill-Qwen-32B-4bit",
        "tok_s_estimate": 16,
        "context": 32768,
        "tier": "free",
        "category": "reasoning",
        "description": "Heavy-duty reasoning. Competes with GPT-4 on math/logic.",
    },
    {
        "id": "qwen-2.5-coder-32b",
        "name": "Qwen Coder 32B",
        "family": "Qwen",
        "params": "32B",
        "min_vram": 20,
        "recommended_vram": 32,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/Qwen2.5-Coder-32B-Instruct-GGUF/resolve/main/Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf",
        "omlx_id": "mlx-community/Qwen2.5-Coder-32B-Instruct-4bit",
        "tok_s_estimate": 16,
        "context": 32768,
        "tier": "free",
        "category": "coding",
        "description": "Best local coding model. Rivals Claude/GPT on code generation.",
    },
    {
        "id": "qwen-3.5-35b",
        "name": "Deep Thinker",
        "family": "Qwen",
        "params": "35B",
        "min_vram": 24,
        "recommended_vram": 32,
        "quant": "Q6_K",
        "gguf_url": "https://huggingface.co/bartowski/Qwen3.5-35B-GGUF/resolve/main/Qwen3.5-35B-Q6_K.gguf",
        "omlx_id": "mlx-community/Qwen3.5-35B-6bit",
        "tok_s_estimate": 18,
        "context": 32768,
        "tier": "free",
        "category": "general",
        "description": "Near-GPT-4 quality for complex reasoning. Higher quant for quality.",
    },

    # ==========================================
    # XL (48+ GB VRAM / 64+ GB unified)
    # ==========================================
    {
        "id": "llama-3.3-70b",
        "name": "Llama 3.3 70B",
        "family": "Llama",
        "params": "70B",
        "min_vram": 40,
        "recommended_vram": 48,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/Llama-3.3-70B-Instruct-GGUF/resolve/main/Llama-3.3-70B-Instruct-Q4_K_M.gguf",
        "omlx_id": "mlx-community/Llama-3.3-70B-Instruct-4bit",
        "tok_s_estimate": 10,
        "context": 131072,
        "tier": "free",
        "category": "general",
        "description": "Meta's flagship. 128K context, frontier-class reasoning.",
    },
    {
        "id": "deepseek-r1-70b",
        "name": "DeepSeek Reason 70B",
        "family": "DeepSeek",
        "params": "70B",
        "min_vram": 40,
        "recommended_vram": 48,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/DeepSeek-R1-Distill-Llama-70B-GGUF/resolve/main/DeepSeek-R1-Distill-Llama-70B-Q4_K_M.gguf",
        "omlx_id": "mlx-community/DeepSeek-R1-Distill-Llama-70B-4bit",
        "tok_s_estimate": 8,
        "context": 32768,
        "tier": "free",
        "category": "reasoning",
        "description": "Maximum local reasoning power. Needs 48GB+ VRAM.",
    },
    {
        "id": "qwen-3-235b-a22b",
        "name": "Qwen 3 MoE",
        "family": "Qwen",
        "params": "235B (22B active)",
        "min_vram": 48,
        "recommended_vram": 64,
        "quant": "Q4_K_M",
        "gguf_url": "https://huggingface.co/bartowski/Qwen3-235B-A22B-GGUF/resolve/main/Qwen3-235B-A22B-Q4_K_M.gguf",
        "omlx_id": "mlx-community/Qwen3-235B-A22B-4bit",
        "tok_s_estimate": 12,
        "context": 32768,
        "tier": "free",
        "category": "general",
        "description": "Mixture-of-Experts: 235B params, only 22B active. Near-GPT-4o.",
    },

    # ==========================================
    # CLOUD — OpenAI (bring your own key)
    # ==========================================
    {
        "id": "cloud-gpt-4o",
        "name": "GPT-4o",
        "family": "OpenAI",
        "params": "cloud",
        "min_vram": 0,
        "recommended_vram": 0,
        "provider": "openai",
        "model_id": "gpt-4o",
        "context": 128000,
        "tier": "paid",
        "category": "general",
        "description": "OpenAI's flagship multimodal. 128K context, vision, function calling.",
        "pricing": {"input_per_1m": 2.50, "output_per_1m": 10.00},
    },
    {
        "id": "cloud-gpt-4o-mini",
        "name": "GPT-4o Mini",
        "family": "OpenAI",
        "params": "cloud",
        "min_vram": 0,
        "recommended_vram": 0,
        "provider": "openai",
        "model_id": "gpt-4o-mini",
        "context": 128000,
        "tier": "paid",
        "category": "general",
        "description": "Fast and cheap. Great for simple tasks and high-volume use.",
        "pricing": {"input_per_1m": 0.15, "output_per_1m": 0.60},
    },
    {
        "id": "cloud-gpt-4-5",
        "name": "GPT-4.5 Preview",
        "family": "OpenAI",
        "params": "cloud",
        "min_vram": 0,
        "recommended_vram": 0,
        "provider": "openai",
        "model_id": "gpt-4.5-preview",
        "context": 128000,
        "tier": "paid",
        "category": "general",
        "description": "Largest GPT. Better creative writing and nuance than 4o. Expensive.",
        "pricing": {"input_per_1m": 75.00, "output_per_1m": 150.00},
    },
    {
        "id": "cloud-o1",
        "name": "o1",
        "family": "OpenAI",
        "params": "cloud",
        "min_vram": 0,
        "recommended_vram": 0,
        "provider": "openai",
        "model_id": "o1",
        "context": 200000,
        "tier": "paid",
        "category": "reasoning",
        "description": "Advanced reasoning. 200K context, chain-of-thought for hard problems.",
        "pricing": {"input_per_1m": 15.00, "output_per_1m": 60.00},
    },
    {
        "id": "cloud-o3-mini",
        "name": "o3-mini",
        "family": "OpenAI",
        "params": "cloud",
        "min_vram": 0,
        "recommended_vram": 0,
        "provider": "openai",
        "model_id": "o3-mini",
        "context": 200000,
        "tier": "paid",
        "category": "reasoning",
        "description": "Fast reasoning at low cost. Great for math, science, code.",
        "pricing": {"input_per_1m": 1.10, "output_per_1m": 4.40},
    },
    {
        "id": "cloud-o4-mini",
        "name": "o4-mini",
        "family": "OpenAI",
        "params": "cloud",
        "min_vram": 0,
        "recommended_vram": 0,
        "provider": "openai",
        "model_id": "o4-mini",
        "context": 200000,
        "tier": "paid",
        "category": "reasoning",
        "description": "Latest small reasoning model. Fast, smart, and affordable.",
        "pricing": {"input_per_1m": 1.10, "output_per_1m": 4.40},
    },

    # ==========================================
    # CLOUD — Anthropic (bring your own key)
    # ==========================================
    {
        "id": "cloud-claude-opus-4",
        "name": "Claude Opus 4",
        "family": "Anthropic",
        "params": "cloud",
        "min_vram": 0,
        "recommended_vram": 0,
        "provider": "anthropic",
        "model_id": "claude-opus-4-20250514",
        "context": 200000,
        "tier": "paid",
        "category": "reasoning",
        "description": "Anthropic's most powerful. Exceptional at complex analysis and coding.",
        "pricing": {"input_per_1m": 15.00, "output_per_1m": 75.00},
    },
    {
        "id": "cloud-claude-sonnet-4",
        "name": "Claude Sonnet 4",
        "family": "Anthropic",
        "params": "cloud",
        "min_vram": 0,
        "recommended_vram": 0,
        "provider": "anthropic",
        "model_id": "claude-sonnet-4-20250514",
        "context": 200000,
        "tier": "paid",
        "category": "general",
        "description": "Best balance of speed and intelligence. Excellent for coding.",
        "pricing": {"input_per_1m": 3.00, "output_per_1m": 15.00},
    },
    {
        "id": "cloud-claude-3-5-sonnet",
        "name": "Claude 3.5 Sonnet",
        "family": "Anthropic",
        "params": "cloud",
        "min_vram": 0,
        "recommended_vram": 0,
        "provider": "anthropic",
        "model_id": "claude-3-5-sonnet-20241022",
        "context": 200000,
        "tier": "paid",
        "category": "general",
        "description": "Previous-gen Sonnet. Still extremely capable, slightly cheaper.",
        "pricing": {"input_per_1m": 3.00, "output_per_1m": 15.00},
    },
    {
        "id": "cloud-claude-3-5-haiku",
        "name": "Claude 3.5 Haiku",
        "family": "Anthropic",
        "params": "cloud",
        "min_vram": 0,
        "recommended_vram": 0,
        "provider": "anthropic",
        "model_id": "claude-3-5-haiku-20241022",
        "context": 200000,
        "tier": "paid",
        "category": "general",
        "description": "Fastest Claude. Great for chat, lightweight tasks, and high volume.",
        "pricing": {"input_per_1m": 0.80, "output_per_1m": 4.00},
    },
    {
        "id": "cloud-claude-3-opus",
        "name": "Claude 3 Opus",
        "family": "Anthropic",
        "params": "cloud",
        "min_vram": 0,
        "recommended_vram": 0,
        "provider": "anthropic",
        "model_id": "claude-3-opus-20240229",
        "context": 200000,
        "tier": "paid",
        "category": "reasoning",
        "description": "Previous-gen flagship. Strong at complex reasoning and long documents.",
        "pricing": {"input_per_1m": 15.00, "output_per_1m": 75.00},
    },

    # ==========================================
    # CLOUD — Google (bring your own key)
    # ==========================================
    {
        "id": "cloud-gemini-2-5-pro",
        "name": "Gemini 2.5 Pro",
        "family": "Google",
        "params": "cloud",
        "min_vram": 0,
        "recommended_vram": 0,
        "provider": "google",
        "model_id": "gemini-2.5-pro",
        "context": 1000000,
        "tier": "paid",
        "category": "reasoning",
        "description": "Google's best. 1M context, multimodal, deep thinking mode.",
        "pricing": {"input_per_1m": 1.25, "output_per_1m": 10.00},
    },
    {
        "id": "cloud-gemini-2-5-flash",
        "name": "Gemini 2.5 Flash",
        "family": "Google",
        "params": "cloud",
        "min_vram": 0,
        "recommended_vram": 0,
        "provider": "google",
        "model_id": "gemini-2.5-flash",
        "context": 1000000,
        "tier": "paid",
        "category": "general",
        "description": "Fastest Gemini. 1M context, thinking mode, very cheap.",
        "pricing": {"input_per_1m": 0.15, "output_per_1m": 0.60},
    },
    {
        "id": "cloud-gemini-2-0-flash",
        "name": "Gemini 2.0 Flash",
        "family": "Google",
        "params": "cloud",
        "min_vram": 0,
        "recommended_vram": 0,
        "provider": "google",
        "model_id": "gemini-2.0-flash",
        "context": 1000000,
        "tier": "paid",
        "category": "general",
        "description": "Previous-gen Flash. Stable, reliable, 1M context.",
        "pricing": {"input_per_1m": 0.10, "output_per_1m": 0.40},
    },
    {
        "id": "cloud-gemini-1-5-pro",
        "name": "Gemini 1.5 Pro",
        "family": "Google",
        "params": "cloud",
        "min_vram": 0,
        "recommended_vram": 0,
        "provider": "google",
        "model_id": "gemini-1.5-pro",
        "context": 2000000,
        "tier": "paid",
        "category": "general",
        "description": "2M context window. Best for processing very long documents.",
        "pricing": {"input_per_1m": 1.25, "output_per_1m": 5.00},
    },
    {
        "id": "cloud-gemini-1-5-flash",
        "name": "Gemini 1.5 Flash",
        "family": "Google",
        "params": "cloud",
        "min_vram": 0,
        "recommended_vram": 0,
        "provider": "google",
        "model_id": "gemini-1.5-flash",
        "context": 1000000,
        "tier": "paid",
        "category": "general",
        "description": "1M context, very cheap. Good for simple tasks and batch processing.",
        "pricing": {"input_per_1m": 0.075, "output_per_1m": 0.30},
    },

    # ==========================================
    # CLOUD — NVIDIA NIM (Free Tier)
    # ==========================================
    {
        "id": "cloud-kimi-k2.5",
        "name": "Cloud: Kimi K2.5",
        "family": "Moonshot",
        "params": "cloud",
        "min_vram": 0,
        "recommended_vram": 0,
        "provider": "nvidia_nim",
        "model_id": "moonshotai/kimi-k2.5",
        "context": 131072,
        "tier": "free",
        "category": "general",
        "description": "128K context cloud model. Free on NVIDIA NIM.",
    },
    {
        "id": "cloud-glm5",
        "name": "Cloud: GLM-5",
        "family": "Zhipu",
        "params": "cloud",
        "min_vram": 0,
        "recommended_vram": 0,
        "provider": "nvidia_nim",
        "model_id": "z-ai/glm-5",
        "context": 32768,
        "tier": "free",
        "category": "general",
        "description": "Strong reasoning cloud model. Free on NVIDIA NIM.",
    },
    {
        "id": "cloud-deepseek-r1",
        "name": "Cloud: DeepSeek R1 (671B)",
        "family": "DeepSeek",
        "params": "cloud (671B)",
        "min_vram": 0,
        "recommended_vram": 0,
        "provider": "nvidia_nim",
        "model_id": "deepseek-ai/deepseek-r1",
        "context": 32768,
        "tier": "free",
        "category": "reasoning",
        "description": "Full 671B DeepSeek R1. Maximum reasoning power, cloud-only.",
    },
    {
        "id": "cloud-llama-3.3-70b",
        "name": "Cloud: Llama 3.3 70B",
        "family": "Llama",
        "params": "cloud (70B)",
        "min_vram": 0,
        "recommended_vram": 0,
        "provider": "nvidia_nim",
        "model_id": "meta/llama-3.3-70b-instruct",
        "context": 131072,
        "tier": "free",
        "category": "general",
        "description": "Meta's flagship in the cloud. 128K context. Free on NIM.",
    },
    {
        "id": "cloud-mistral-large",
        "name": "Cloud: Mistral Large",
        "family": "Mistral",
        "params": "cloud (123B)",
        "min_vram": 0,
        "recommended_vram": 0,
        "provider": "nvidia_nim",
        "model_id": "mistralai/mistral-large-2-instruct",
        "context": 32768,
        "tier": "free",
        "category": "general",
        "description": "Mistral's flagship 123B. Strong multilingual. Free on NIM.",
    },
    {
        "id": "cloud-qwen-3-235b",
        "name": "Cloud: Qwen 3 235B",
        "family": "Qwen",
        "params": "cloud (235B)",
        "min_vram": 0,
        "recommended_vram": 0,
        "provider": "nvidia_nim",
        "model_id": "qwen/qwen3-235b-a22b",
        "context": 32768,
        "tier": "free",
        "category": "general",
        "description": "Qwen 3 MoE in the cloud. No GPU needed. Free on NIM.",
    },
]

# ---------------------------------------------------------------------------
# Custom models (user-added GGUFs)
# ---------------------------------------------------------------------------

_CUSTOM_MODELS_FILE = Path.home() / ".valhalla" / "custom_models.json"


def _load_custom_models() -> list:
    """Load user-added custom models."""
    if _CUSTOM_MODELS_FILE.exists():
        try:
            return json.loads(_CUSTOM_MODELS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_custom_models(models: list) -> None:
    """Save custom models to disk."""
    _CUSTOM_MODELS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CUSTOM_MODELS_FILE.write_text(
        json.dumps(models, indent=2), encoding="utf-8"
    )


def add_custom_model(
    name: str,
    gguf_path: str,
    context: int = 4096,
    description: str = "",
) -> dict:
    """Add a custom model from a local GGUF file.

    User can drop a .gguf file and register it with a friendly name.
    """
    from pathlib import Path as P
    path = P(gguf_path)
    if not path.exists():
        return {"ok": False, "error": f"File not found: {gguf_path}"}
    if path.suffix.lower() != ".gguf":
        return {"ok": False, "error": "File must be a .gguf file"}

    size_gb = round(path.stat().st_size / (1024**3), 1)
    # Estimate VRAM: roughly 1.2x file size for Q4
    est_vram = round(size_gb * 1.2, 1)

    model_id = f"custom-{name.lower().replace(' ', '-')}"

    entry = {
        "id": model_id,
        "name": name,
        "family": "Custom",
        "params": f"~{size_gb}GB",
        "min_vram": est_vram,
        "recommended_vram": round(est_vram * 1.3, 1),
        "quant": "unknown",
        "gguf_path": str(path.resolve()),
        "context": context,
        "tier": "free",
        "category": "custom",
        "description": description or f"Custom model from {path.name}",
        "custom": True,
    }

    customs = _load_custom_models()
    # Replace if same ID exists
    customs = [m for m in customs if m["id"] != model_id]
    customs.append(entry)
    _save_custom_models(customs)

    return {"ok": True, "model": entry}


def remove_custom_model(model_id: str) -> dict:
    """Remove a custom model."""
    customs = _load_custom_models()
    before = len(customs)
    customs = [m for m in customs if m["id"] != model_id]
    if len(customs) == before:
        return {"ok": False, "error": "Model not found"}
    _save_custom_models(customs)
    return {"ok": True, "removed": model_id}


# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------

def get_all_models() -> list:
    """Return all models: curated + custom."""
    return MODELS + _load_custom_models()


def get_available(vram_gb: float) -> list:
    """Return models compatible with available VRAM, sorted by recommendation."""
    results = []
    for model in get_all_models():
        is_cloud = model.get("provider") is not None
        min_vram = model.get("min_vram", 0)
        rec_vram = model.get("recommended_vram", 0)

        if is_cloud:
            status = "☁️ Cloud (no GPU needed)"
            compatible = True
        elif vram_gb >= rec_vram:
            status = "✅ Recommended"
            compatible = True
        elif vram_gb >= min_vram:
            status = "⚠️ May be slow"
            compatible = True
        else:
            status = "❌ Not enough AI memory"
            compatible = False

        results.append({
            **model,
            "status": status,
            "compatible": compatible,
        })

    return sorted(results, key=lambda x: (not x["compatible"], x.get("min_vram", 0)))


def get_model(model_id: str) -> dict | None:
    """Look up a model by ID."""
    for m in get_all_models():
        if m["id"] == model_id:
            return m
    return None


def get_by_category(category: str) -> list:
    """Get models by category: general, coding, reasoning, custom."""
    return [m for m in get_all_models() if m.get("category") == category]


def get_by_family(family: str) -> list:
    """Get models by family: Llama, Qwen, DeepSeek, Gemma, Mistral, Phi, etc."""
    return [m for m in get_all_models() if m.get("family", "").lower() == family.lower()]
