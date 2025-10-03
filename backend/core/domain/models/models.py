from enum import StrEnum


# All models that were supported at one point by WorkflowAI
# Some are deprecated an remapped.
#
# Notes:
# - DO NOT remove models from this list, only add new ones. If needed, add a replacement model
# in the model datas
# - the order is the same as will be displayed in the UI. If you need a model to be displayed
# higher, comment out the line where it should be in "natural" order, and add another one wherever
# needed for the order
class Model(StrEnum):
    # Default model order
    GPT_41_LATEST = "gpt-4.1-latest"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    CLAUDE_4_SONNET_LATEST = "claude-sonnet-4-latest"

    # --------------------------------------------------------------------------
    # OpenAI Models
    # --------------------------------------------------------------------------

    GPT_5_2025_08_07 = "gpt-5-2025-08-07"
    GPT_5_MINI_2025_08_07 = "gpt-5-mini-2025-08-07"
    GPT_5_NANO_2025_08_07 = "gpt-5-nano-2025-08-07"

    GPT_41_2025_04_14 = "gpt-4.1-2025-04-14"
    GPT_41_MINI_LATEST = "gpt-4.1-mini-latest"
    GPT_41_MINI_2025_04_14 = "gpt-4.1-mini-2025-04-14"
    GPT_41_NANO_LATEST = "gpt-4.1-nano-latest"
    GPT_41_NANO_2025_04_14 = "gpt-4.1-nano-2025-04-14"
    GPT_4O_LATEST = "gpt-4o-latest"
    GPT_4O_2024_11_20 = "gpt-4o-2024-11-20"
    GPT_4O_2024_08_06 = "gpt-4o-2024-08-06"
    GPT_4O_2024_05_13 = "gpt-4o-2024-05-13"
    GPT_4O_MINI_LATEST = "gpt-4o-mini-latest"
    GPT_4O_MINI_2024_07_18 = "gpt-4o-mini-2024-07-18"

    O1_2024_12_17 = "o1-2024-12-17"

    O3_LATEST = "o3-latest"
    O3_2025_04_16 = "o3-2025-04-16"

    O3_MINI_LATEST = "o3-mini-latest"
    O3_MINI_2025_01_31 = "o3-mini-2025-01-31"

    O4_MINI_LATEST = "o4-mini-latest"
    O4_MINI_2025_04_16 = "o4-mini-2025-04-16"

    GPT_4O_AUDIO_PREVIEW_2025_06_03 = "gpt-4o-audio-preview-2025-06-03"
    O1_PREVIEW_2024_09_12 = "o1-preview-2024-09-12"
    O1_MINI_LATEST = "o1-mini-latest"
    O1_MINI_2024_09_12 = "o1-mini-2024-09-12"

    GPT_45_PREVIEW_2025_02_27 = "gpt-4.5-preview-2025-02-27"

    GPT_4O_AUDIO_PREVIEW_2024_12_17 = "gpt-4o-audio-preview-2024-12-17"
    GPT_4O_AUDIO_PREVIEW_2024_10_01 = "gpt-4o-audio-preview-2024-10-01"

    GPT_4_TURBO_2024_04_09 = "gpt-4-turbo-2024-04-09"
    GPT_4_0125_PREVIEW = "gpt-4-0125-preview"
    GPT_4_1106_PREVIEW = "gpt-4-1106-preview"
    GPT_4_1106_VISION_PREVIEW = "gpt-4-1106-vision-preview"
    GPT_3_5_TURBO_0125 = "gpt-3.5-turbo-0125"
    GPT_3_5_TURBO_1106 = "gpt-3.5-turbo-1106"

    # --------------------------------------------------------------------------
    # OpenAI Open Models
    # --------------------------------------------------------------------------

    GPT_OSS_20B = "gpt-oss-20b"
    GPT_OSS_120B = "gpt-oss-120b"

    # --------------------------------------------------------------------------
    # Gemini Models
    # --------------------------------------------------------------------------

    GEMINI_2_5_PRO = "gemini-2.5-pro"
    # GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"
    GEMINI_2_5_FLASH_LITE_PREVIEW_0925 = "gemini-2.5-flash-lite-preview-09-2025"
    GEMINI_2_5_FLASH_PREVIEW_0925 = "gemini-2.5-flash-preview-09-2025"

    GEMINI_2_5_PRO_PREVIEW_0605 = "gemini-2.5-pro-preview-06-05"
    GEMINI_2_5_FLASH_PREVIEW_0520 = "gemini-2.5-flash-preview-05-20"
    GEMINI_2_5_FLASH_THINKING_PREVIEW_0520 = "gemini-2.5-flash-thinking-preview-05-20"
    GEMINI_2_5_PRO_PREVIEW_0506 = "gemini-2.5-pro-preview-05-06"
    GEMINI_2_5_FLASH_PREVIEW_0417 = "gemini-2.5-flash-preview-04-17"
    GEMINI_2_5_FLASH_THINKING_PREVIEW_0417 = "gemini-2.5-flash-thinking-preview-04-17"
    GEMINI_2_5_PRO_PREVIEW_0325 = "gemini-2.5-pro-preview-03-25"
    GEMINI_2_5_PRO_EXP_0325 = "gemini-2.5-pro-exp-03-25"
    GEMINI_2_5_FLASH_LITE_PREVIEW_0617 = "gemini-2.5-flash-lite-preview-06-17"
    GEMINI_2_0_FLASH_LATEST = "gemini-2.0-flash-latest"
    GEMINI_2_0_FLASH_001 = "gemini-2.0-flash-001"
    GEMINI_2_0_FLASH_LITE_001 = "gemini-2.0-flash-lite-001"
    GEMINI_2_0_FLASH_LITE_PREVIEW_2502 = "gemini-2.0-flash-lite-preview-02-05"
    GEMINI_2_0_PRO_EXP = "gemini-2.0-pro-exp-02-05"
    GEMINI_2_0_FLASH_EXP = "gemini-2.0-flash-exp"
    GEMINI_2_0_FLASH_THINKING_EXP_1219 = "gemini-2.0-flash-thinking-exp-1219"
    GEMINI_2_0_FLASH_THINKING_EXP_0121 = "gemini-2.0-flash-thinking-exp-01-21"
    GEMINI_1_5_PRO_LATEST = "gemini-1.5-pro-latest"
    GEMINI_1_5_PRO_002 = "gemini-1.5-pro-002"
    GEMINI_1_5_PRO_001 = "gemini-1.5-pro-001"
    GEMINI_1_5_PRO_PREVIEW_0514 = "gemini-1.5-pro-preview-0514"
    GEMINI_1_5_PRO_PREVIEW_0409 = "gemini-1.5-pro-preview-0409"
    GEMINI_1_5_FLASH_LATEST = "gemini-1.5-flash-latest"
    GEMINI_1_5_FLASH_002 = "gemini-1.5-flash-002"
    GEMINI_1_5_FLASH_001 = "gemini-1.5-flash-001"
    GEMINI_1_5_FLASH_8B = "gemini-1.5-flash-8b"
    GEMINI_1_5_FLASH_PREVIEW_0514 = "gemini-1.5-flash-preview-0514"
    GEMINI_EXP_1206 = "gemini-exp-1206"
    GEMINI_EXP_1121 = "gemini-exp-1121"
    GEMINI_1_0_PRO_002 = "gemini-1.0-pro-002"
    GEMINI_1_0_PRO_001 = "gemini-1.0-pro-001"
    GEMINI_1_0_PRO_VISION_001 = "gemini-1.0-pro-vision-001"

    # --------------------------------------------------------------------------
    # Claude Models
    # --------------------------------------------------------------------------
    CLAUDE_4_5_SONNET_20250929 = "claude-sonnet-4-5-20250929"
    CLAUDE_4_1_OPUS_20250805 = "claude-opus-4-1-20250805"
    # CLAUDE_4_SONNET_LATEST = "claude-sonnet-4-latest"
    CLAUDE_4_SONNET_20250514 = "claude-sonnet-4-20250514"
    CLAUDE_4_OPUS_LATEST = "claude-opus-4-latest"
    CLAUDE_4_OPUS_20250514 = "claude-opus-4-20250514"
    CLAUDE_3_7_SONNET_LATEST = "claude-3-7-sonnet-latest"
    CLAUDE_3_7_SONNET_20250219 = "claude-3-7-sonnet-20250219"
    CLAUDE_3_5_SONNET_LATEST = "claude-3-5-sonnet-latest"
    CLAUDE_3_5_SONNET_20241022 = "claude-3-5-sonnet-20241022"
    CLAUDE_3_5_SONNET_20240620 = "claude-3-5-sonnet-20240620"
    CLAUDE_3_5_HAIKU_LATEST = "claude-3-5-haiku-latest"
    CLAUDE_3_5_HAIKU_20241022 = "claude-3-5-haiku-20241022"
    CLAUDE_3_OPUS_20240229 = "claude-3-opus-20240229"
    CLAUDE_3_SONNET_20240229 = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU_20240307 = "claude-3-haiku-20240307"

    # --------------------------------------------------------------------------
    # Llama Models
    # --------------------------------------------------------------------------
    LLAMA_4_MAVERICK_FAST = "llama4-maverick-instruct-fast"
    LLAMA_4_SCOUT_FAST = "llama4-scout-instruct-fast"
    LLAMA_4_MAVERICK_BASIC = "llama4-maverick-instruct-basic"
    LLAMA_4_SCOUT_BASIC = "llama4-scout-instruct-basic"
    LLAMA_3_3_70B = "llama-3.3-70b"
    LLAMA_3_2_90B = "llama-3.2-90b"
    LLAMA_3_2_11B = "llama-3.2-11b"
    LLAMA_3_2_11B_VISION = "llama-3.2-11b-vision"
    LLAMA_3_2_3B = "llama-3.2-3b"
    LLAMA_3_2_1B = "llama-3.2-1b"
    LLAMA_3_2_90B_VISION_PREVIEW = "llama-3.2-90b-vision-preview"
    LLAMA_3_2_90B_TEXT_PREVIEW = "llama-3.2-90b-text-preview"
    LLAMA_3_2_11B_TEXT_PREVIEW = "llama-3.2-11b-text-preview"
    LLAMA_3_2_3B_PREVIEW = "llama-3.2-3b-preview"
    LLAMA_3_2_1B_PREVIEW = "llama-3.2-1b-preview"
    LLAMA_3_1_405B = "llama-3.1-405b"
    LLAMA_3_1_70B = "llama-3.1-70b"
    LLAMA_3_1_8B = "llama-3.1-8b"
    LLAMA3_70B_8192 = "llama3-70b-8192"
    LLAMA3_8B_8192 = "llama3-8b-8192"

    # --------------------------------------------------------------------------
    # Mistral AI Models
    # --------------------------------------------------------------------------
    MIXTRAL_8X7B_32768 = "mixtral-8x7b-32768"
    MISTRAL_LARGE_2_LATEST = "mistral-large-2-latest"
    MISTRAL_LARGE_2_2407 = "mistral-large-2-2407"
    MISTRAL_LARGE_LATEST = "mistral-large-latest"
    MISTRAL_LARGE_2411 = "mistral-large-2411"
    MISTRAL_MEDIUM_2505 = "mistral-medium-2505"
    MISTRAL_MEDIUM_2508 = "mistral-medium-2508"
    PIXTRAL_LARGE_LATEST = "pixtral-large-latest"
    PIXTRAL_LARGE_2411 = "pixtral-large-2411"
    PIXTRAL_12B_2409 = "pixtral-12b-2409"
    MINISTRAL_3B_2410 = "ministral-3b-2410"
    MINISTRAL_8B_2410 = "ministral-8b-2410"
    MISTRAL_SMALL_LATEST = "mistral-small-latest"
    MISTRAL_SMALL_2506 = "mistral-small-2506"
    MISTRAL_SMALL_2503 = "mistral-small-2503"
    MISTRAL_SMALL_2501 = "mistral-small-2501"
    MISTRAL_SMALL_2409 = "mistral-small-2409"
    MISTRAL_SABA_2502 = "mistral-saba-2502"
    MAGISTRAL_SMALL_2506 = "magistral-small-2506"
    MAGISTRAL_SMALL_2507 = "magistral-small-2507"
    MAGISTRAL_SMALL_2509 = "magistral-small-2509"
    MAGISTRAL_MEDIUM_2506 = "magistral-medium-2506"
    MAGISTRAL_MEDIUM_2507 = "magistral-medium-2507"
    MAGISTRAL_MEDIUM_2509 = "magistral-medium-2509"
    CODESTRAL_2501 = "codestral-2501"
    CODESTRAL_2508 = "codestral-2508"
    CODESTRAL_MAMBA_2407 = "codestral-mamba-2407"

    # --------------------------------------------------------------------------
    # Qwen Models
    # --------------------------------------------------------------------------
    QWEN_QWQ_32B = "qwen-qwq-32b"
    QWEN_QWQ_32B_PREVIEW = "qwen-v3p2-32b-instruct"
    QWEN3_235B_A22B = "qwen3-235b-a22b"
    QWEN3_30B_A3B = "qwen3-30b-a3b"
    QWEN3_32B = "qwen3-32b"

    # --------------------------------------------------------------------------
    # DeepSeek Models
    # --------------------------------------------------------------------------
    DEEPSEEK_V3_1_TERMINUS = "deepseek-v3.1-terminus"
    DEEPSEEK_V3_2412 = "deepseek-v3-2412"
    DEEPSEEK_V3_0324 = "deepseek-v3-0324"
    DEEPSEEK_V3_LATEST = "deepseek-v3-latest"
    DEEPSEEK_R1_2501 = "deepseek-r1-2501"
    DEEPSEEK_R1_2501_BASIC = "deepseek-r1-2501-basic"
    DEEPSEEK_R1_0528 = "deepseek-r1-0528"

    # --------------------------------------------------------------------------
    # XAI Models
    # --------------------------------------------------------------------------
    GROK_CODE_FAST_1 = "grok-code-fast-1"
    GROK_4_FAST = "grok-4-fast"
    GROK_4_0709 = "grok-4-0709"

    GROK_3_BETA = "grok-3-beta"
    GROK_3_FAST_BETA = "grok-3-fast-beta"

    GROK_3_MINI_BETA = "grok-3-mini-beta"
    GROK_3_MINI_FAST_BETA = "grok-3-mini-fast-beta"

    # --------------------------------------------------------------------------
    # MOONSHOT Models
    # --------------------------------------------------------------------------
    KIMI_K2_INSTRUCT_0905 = "kimi-k2-instruct-0905"
    KIMI_K2_INSTRUCT = "kimi-k2-instruct"
