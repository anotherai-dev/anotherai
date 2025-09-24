from core.domain.models import Model, Provider
from core.providers.google.google_provider_domain import GOOGLE_CHARS_PER_TOKEN

from .model_provider_data import (
    AudioPricePerToken,
    ModelDataSupportsOverride,
    ModelProviderData,
    TextPricePerToken,
    ThresholdedTextPricePerToken,
)

ProviderDataByModel = dict[Model, ModelProviderData]
ONE_MILLION_TH = 0.000_001


GOOGLE_PROVIDER_DATA: ProviderDataByModel = {
    Model.GEMINI_2_5_FLASH: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.30 * ONE_MILLION_TH,
            completion_cost_per_token=2.50 * ONE_MILLION_TH,
            source="https://ai.google.dev/gemini-api/docs/pricing#gemini-2.5-flash",
            prompt_cached_tokens_discount=0.75,
        ),
        audio_price=AudioPricePerToken(
            audio_input_cost_per_token=1.0 * ONE_MILLION_TH,
        ),
    ),
    Model.GEMINI_2_5_PRO: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=1.25 * ONE_MILLION_TH,
            completion_cost_per_token=10 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.75,
            source="https://cloud.google.com/vertex-ai/generative-ai/pricing",
            thresholded_prices=[
                ThresholdedTextPricePerToken(
                    threshold=200_000,
                    prompt_cost_per_token_over_threshold=2.5 * ONE_MILLION_TH,
                    completion_cost_per_token_over_threshold=15 * ONE_MILLION_TH,
                ),
            ],
        ),
    ),
    Model.GEMINI_2_5_FLASH_LITE: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.1 * ONE_MILLION_TH,
            completion_cost_per_token=0.40 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.75,
            source="https://ai.google.dev/gemini-api/docs/pricing#gemini-2.5-flash-lite",
        ),
        audio_price=AudioPricePerToken(
            audio_input_cost_per_token=0.3 * ONE_MILLION_TH,
        ),
    ),
    Model.GEMINI_2_0_FLASH_001: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.0375 * ONE_MILLION_TH * GOOGLE_CHARS_PER_TOKEN,
            completion_cost_per_token=0.15 * ONE_MILLION_TH * GOOGLE_CHARS_PER_TOKEN,
            source="https://cloud.google.com/vertex-ai/generative-ai/pricing",
            prompt_cached_tokens_discount=0.75,
        ),
        audio_price=AudioPricePerToken(
            audio_input_cost_per_token=1 * ONE_MILLION_TH,
        ),
    ),
    Model.GEMINI_2_0_FLASH_LITE_001: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.01875 * ONE_MILLION_TH * GOOGLE_CHARS_PER_TOKEN,
            completion_cost_per_token=0.075 * ONE_MILLION_TH * GOOGLE_CHARS_PER_TOKEN,
            source="https://cloud.google.com/vertex-ai/generative-ai/pricing",
            prompt_cached_tokens_discount=0.75,
        ),
        audio_price=AudioPricePerToken(
            audio_input_cost_per_token=0.075 * ONE_MILLION_TH,
        ),
    ),
    Model.LLAMA_3_1_405B: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.000_005,
            completion_cost_per_token=0.000_016,
            source="https://cloud.google.com/vertex-ai/generative-ai/pricing#meta-models",
        ),
    ),
}


OPENAI_PROVIDER_DATA: ProviderDataByModel = {
    Model.O3_MINI_2025_01_31: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=1.10 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.5,
            completion_cost_per_token=4.40 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
    ),
    Model.O3_2025_04_16: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=2 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.75,
            completion_cost_per_token=8 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
    ),
    Model.O4_MINI_2025_04_16: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=1.1 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.75,
            completion_cost_per_token=4.4 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
    ),
    Model.O1_2024_12_17: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=15 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.5,
            completion_cost_per_token=60 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
    ),
    Model.GPT_4O_2024_11_20: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=2.5 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.5,
            completion_cost_per_token=10 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
    ),
    Model.GPT_4O_2024_08_06: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=2.5 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.5,
            completion_cost_per_token=10 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
    ),
    Model.GPT_41_2025_04_14: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=2 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.75,
            completion_cost_per_token=8 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
    ),
    Model.GPT_41_MINI_2025_04_14: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.4 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.75,
            completion_cost_per_token=1.6 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
    ),
    Model.GPT_41_NANO_2025_04_14: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.1 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.75,
            completion_cost_per_token=0.4 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
    ),
    Model.GPT_4O_MINI_2024_07_18: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.15 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.5,
            completion_cost_per_token=0.6 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
    ),
    Model.GPT_4O_AUDIO_PREVIEW_2024_12_17: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=2.5 * ONE_MILLION_TH,
            completion_cost_per_token=10 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
        audio_price=AudioPricePerToken(
            audio_input_cost_per_token=40 * ONE_MILLION_TH,
        ),
    ),
    Model.GPT_4O_AUDIO_PREVIEW_2025_06_03: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=2.5 * ONE_MILLION_TH,
            completion_cost_per_token=10 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
        audio_price=AudioPricePerToken(
            audio_input_cost_per_token=40 * ONE_MILLION_TH,
        ),
    ),
    Model.GPT_5_2025_08_07: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=1.25 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.9,
            completion_cost_per_token=10 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
    ),
    Model.GPT_5_MINI_2025_08_07: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.25 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.9,
            completion_cost_per_token=2 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
    ),
    Model.GPT_5_NANO_2025_08_07: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.05 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.9,
            completion_cost_per_token=0.4 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
    ),
}


AMAZON_BEDROCK_PROVIDER_DATA: ProviderDataByModel = {
    Model.CLAUDE_4_OPUS_20250514: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=15 * ONE_MILLION_TH,
            completion_cost_per_token=75 * ONE_MILLION_TH,
            source="https://aws.amazon.com/bedrock/pricing/",
        ),
        supports_override=ModelDataSupportsOverride(
            supports_input_pdf=False,
        ),
    ),
    Model.CLAUDE_4_SONNET_20250514: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=3 * ONE_MILLION_TH,
            completion_cost_per_token=15 * ONE_MILLION_TH,
            source="https://aws.amazon.com/bedrock/pricing/",
        ),
        supports_override=ModelDataSupportsOverride(
            supports_input_pdf=False,
        ),
    ),
    Model.CLAUDE_3_7_SONNET_20250219: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=3 * ONE_MILLION_TH,
            completion_cost_per_token=15 * ONE_MILLION_TH,
            source="https://aws.amazon.com/bedrock/pricing/",
        ),
        supports_override=ModelDataSupportsOverride(
            supports_input_pdf=False,
        ),
    ),
    Model.CLAUDE_3_5_SONNET_20241022: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=3 * ONE_MILLION_TH,
            completion_cost_per_token=15 * ONE_MILLION_TH,
            source="https://aws.amazon.com/bedrock/pricing/",
        ),
        supports_override=ModelDataSupportsOverride(
            supports_input_pdf=False,
        ),
    ),
    Model.CLAUDE_3_5_SONNET_20240620: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=3 * ONE_MILLION_TH,
            completion_cost_per_token=15 * ONE_MILLION_TH,
            source="https://aws.amazon.com/bedrock/pricing/",
        ),
    ),
    Model.CLAUDE_3_OPUS_20240229: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=15 * ONE_MILLION_TH,
            completion_cost_per_token=75 * ONE_MILLION_TH,
            source="https://aws.amazon.com/bedrock/pricing/",
        ),
    ),
    # Model.CLAUDE_3_SONNET_20240229: ModelProviderData(
    #     text_price=TextPricePerToken(
    #         prompt_cost_per_token=3 * ONE_MILLION_TH,
    #         completion_cost_per_token=15 * ONE_MILLION_TH,
    #         source="https://aws.amazon.com/bedrock/pricing/",
    #     ),
    #     lifecycle_data=LifecycleData(
    #         sunset_date=datetime.date(year=2025, month=7, day=20),
    #         source="https://aws.amazon.com/bedrock/pricing/",
    #         post_sunset_replacement_model=Model.CLAUDE_3_5_SONNET_20241022,
    #     ),
    # ),
    Model.CLAUDE_3_HAIKU_20240307: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.25 * ONE_MILLION_TH,
            completion_cost_per_token=1.25 * ONE_MILLION_TH,
            source="https://aws.amazon.com/bedrock/pricing/",
        ),
    ),
    Model.CLAUDE_3_5_HAIKU_20241022: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.8 * ONE_MILLION_TH,
            completion_cost_per_token=4 * ONE_MILLION_TH,
            source="https://aws.amazon.com/bedrock/pricing/",
        ),
    ),
    Model.LLAMA_3_1_405B: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=2.4 * ONE_MILLION_TH,
            completion_cost_per_token=2.4 * ONE_MILLION_TH,
            source="https://aws.amazon.com/bedrock/pricing/",
        ),
    ),
    Model.LLAMA_3_1_70B: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.72 * ONE_MILLION_TH,
            completion_cost_per_token=0.72 * ONE_MILLION_TH,
            source="https://aws.amazon.com/bedrock/pricing/",
        ),
    ),
    Model.LLAMA_3_1_8B: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.22 * ONE_MILLION_TH,
            completion_cost_per_token=0.22 * ONE_MILLION_TH,
            source="https://aws.amazon.com/bedrock/pricing/",
        ),
    ),
    Model.MISTRAL_LARGE_2_2407: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=2 * ONE_MILLION_TH,
            completion_cost_per_token=6 * ONE_MILLION_TH,
            source="https://aws.amazon.com/bedrock/pricing/",
        ),
    ),
    # Model.LLAMA_3_2_90B: ModelProviderData(
    #     text_price=TextPricePerToken(
    #         prompt_cost_per_token=0.000_000_72,
    #         completion_cost_per_token=0.000_000_72,
    #         source="https://aws.amazon.com/bedrock/pricing/",
    #     ),
    # ),
    # Model.LLAMA_3_2_11B: ModelProviderData(
    #     text_price=TextPricePerToken(
    #         prompt_cost_per_token=0.000_000_16,
    #         completion_cost_per_token=0.000_000_16,
    #         source="https://aws.amazon.com/bedrock/pricing/",
    #     ),
    # ),
    # Model.LLAMA_3_2_3B: ModelProviderData(
    #     text_price=TextPricePerToken(
    #         prompt_cost_per_token=0.15 * ONE_MILLION_TH,
    #         completion_cost_per_token=0.15 * ONE_MILLION_TH,
    #         source="https://aws.amazon.com/bedrock/pricing/",
    #     ),
    # ),
    Model.LLAMA_3_3_70B: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.72 * ONE_MILLION_TH,
            completion_cost_per_token=0.72 * ONE_MILLION_TH,
            source="https://aws.amazon.com/bedrock/pricing/",
        ),
    ),
    # Model.LLAMA_3_2_1B: ModelProviderData(
    #     text_price=TextPricePerToken(
    #         prompt_cost_per_token=0.000_000_1,
    #         completion_cost_per_token=0.000_000_1,
    #         source="https://aws.amazon.com/bedrock/pricing/",
    #     ),
    # ),
}

GROQ_PROVIDER_DATA: ProviderDataByModel = {
    Model.LLAMA_3_1_8B: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.05 * ONE_MILLION_TH,
            completion_cost_per_token=0.08 * ONE_MILLION_TH,
            source="https://console.groq.com/settings/billing",
        ),
        # native tools calls are not implemented on Groq for now as we will decommssion the provider for now.
        # see [WOR-1968: Disable `Groq` ?](https://linear.app/workflowai/issue/WOR-1968/disable-groq)
    ),
    Model.LLAMA_3_3_70B: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.59 * ONE_MILLION_TH,
            completion_cost_per_token=0.79 * ONE_MILLION_TH,
            source="https://console.groq.com/settings/billing",
        ),
        # native tools calls are not implemented on Groq for now as we will decommssion the provider for now.
        # see [WOR-1968: Disable `Groq` ?](https://linear.app/workflowai/issue/WOR-1968/disable-groq)
    ),
    Model.LLAMA_4_MAVERICK_FAST: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.20 * ONE_MILLION_TH,
            completion_cost_per_token=0.60 * ONE_MILLION_TH,
            source="https://groq.com/pricing/",
        ),
    ),
    Model.LLAMA_4_SCOUT_FAST: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.11 * ONE_MILLION_TH,
            completion_cost_per_token=0.34 * ONE_MILLION_TH,
            source="https://groq.com/pricing/",
        ),
    ),
    Model.QWEN3_32B: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.29 * ONE_MILLION_TH,
            completion_cost_per_token=0.59 * ONE_MILLION_TH,
            source="https://groq.com/pricing/",
        ),
    ),
    Model.GPT_OSS_20B: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.10 * ONE_MILLION_TH,
            completion_cost_per_token=0.50 * ONE_MILLION_TH,
            source="https://console.groq.com/docs/model/openai/gpt-oss-20b",
        ),
    ),
    Model.GPT_OSS_120B: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.15 * ONE_MILLION_TH,
            completion_cost_per_token=0.75 * ONE_MILLION_TH,
            source="https://console.groq.com/docs/model/openai/gpt-oss-120b",
        ),
    ),
    Model.KIMI_K2_INSTRUCT: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=1 * ONE_MILLION_TH,
            completion_cost_per_token=3 * ONE_MILLION_TH,
            source="https://console.groq.com/docs/model/moonshotai/kimi-k2-instruct",
        ),
    ),
    Model.KIMI_K2_INSTRUCT_0905: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=1 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.5,
            completion_cost_per_token=3 * ONE_MILLION_TH,
            source="https://console.groq.com/docs/model/moonshotai/kimi-k2-instruct-0905",
        ),
    ),
}

MISTRAL_PROVIDER_DATA: ProviderDataByModel = {
    Model.PIXTRAL_12B_2409: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.15 * ONE_MILLION_TH,
            completion_cost_per_token=0.15 * ONE_MILLION_TH,
            source="https://mistral.ai/products/la-plateforme#pricing",
        ),
    ),
    Model.MINISTRAL_3B_2410: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.04 * ONE_MILLION_TH,
            completion_cost_per_token=0.04 * ONE_MILLION_TH,
            source="https://mistral.ai/products/la-plateforme#pricing",
        ),
    ),
    Model.MINISTRAL_8B_2410: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.1 * ONE_MILLION_TH,
            completion_cost_per_token=0.1 * ONE_MILLION_TH,
            source="https://mistral.ai/products/la-plateforme#pricing",
        ),
    ),
    Model.MISTRAL_SMALL_2409: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.1 * ONE_MILLION_TH,
            completion_cost_per_token=0.3 * ONE_MILLION_TH,
            source="https://mistral.ai/products/la-plateforme#pricing",
        ),
    ),
    Model.MISTRAL_SMALL_2501: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.1 * ONE_MILLION_TH,
            completion_cost_per_token=0.3 * ONE_MILLION_TH,
            source="https://mistral.ai/products/la-plateforme#pricing",
        ),
    ),
    Model.MISTRAL_SMALL_2503: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.1 * ONE_MILLION_TH,
            completion_cost_per_token=0.3 * ONE_MILLION_TH,
            source="https://mistral.ai/products/la-plateforme#pricing",
        ),
    ),
    Model.MISTRAL_LARGE_2_2407: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=2.0 * ONE_MILLION_TH,
            completion_cost_per_token=6.0 * ONE_MILLION_TH,
            source="https://mistral.ai/products/la-plateforme#pricing",
        ),
    ),
    Model.PIXTRAL_LARGE_2411: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=2.0 * ONE_MILLION_TH,
            completion_cost_per_token=6.0 * ONE_MILLION_TH,
            source="https://mistral.ai/products/la-plateforme#pricing",
        ),
    ),
    Model.MISTRAL_LARGE_2411: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=2.0 * ONE_MILLION_TH,
            completion_cost_per_token=6.0 * ONE_MILLION_TH,
            source="https://mistral.ai/products/la-plateforme#pricing",
        ),
    ),
    Model.CODESTRAL_2501: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.3 * ONE_MILLION_TH,
            completion_cost_per_token=0.9 * ONE_MILLION_TH,
            source="https://mistral.ai/products/la-plateforme#pricing",
        ),
    ),
    Model.MISTRAL_MEDIUM_2505: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.4 * ONE_MILLION_TH,
            completion_cost_per_token=2 * ONE_MILLION_TH,
            source="https://mistral.ai/products/la-plateforme#pricing",
        ),
    ),
    Model.MAGISTRAL_SMALL_2506: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.5 * ONE_MILLION_TH,
            completion_cost_per_token=1.5 * ONE_MILLION_TH,
            source="https://mistral.ai/pricing#api-pricing",
        ),
    ),
    Model.MAGISTRAL_MEDIUM_2506: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=2.0 * ONE_MILLION_TH,
            completion_cost_per_token=5.0 * ONE_MILLION_TH,
            source="https://mistral.ai/pricing#api-pricing",
        ),
    ),
}

ANTHROPIC_PROVIDER_DATA: ProviderDataByModel = {
    Model.CLAUDE_3_5_HAIKU_20241022: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.80 * ONE_MILLION_TH,
            completion_cost_per_token=4.00 * ONE_MILLION_TH,
            source="https://docs.anthropic.com/en/docs/about-claude/models/all-models#model-comparison-table",
        ),
    ),
    Model.CLAUDE_3_5_SONNET_20241022: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=3.0 * ONE_MILLION_TH,
            completion_cost_per_token=15 * ONE_MILLION_TH,
            source="https://docs.anthropic.com/en/docs/about-claude/models/all-models#model-comparison-table",
        ),
    ),
    Model.CLAUDE_3_5_SONNET_20240620: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=3.00 * ONE_MILLION_TH,
            completion_cost_per_token=15.00 * ONE_MILLION_TH,
            source="https://docs.anthropic.com/en/docs/about-claude/models/all-models#model-comparison-table",
        ),
    ),
    Model.CLAUDE_3_7_SONNET_20250219: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=3.00 * ONE_MILLION_TH,
            completion_cost_per_token=15.00 * ONE_MILLION_TH,
            source="https://docs.anthropic.com/en/docs/about-claude/models/all-models#model-comparison-table",
        ),
    ),
    Model.CLAUDE_4_OPUS_20250514: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=15 * ONE_MILLION_TH,
            completion_cost_per_token=75 * ONE_MILLION_TH,
            source="https://docs.anthropic.com/en/docs/about-claude/models/all-models#model-comparison-table",
        ),
    ),
    Model.CLAUDE_4_SONNET_20250514: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=3 * ONE_MILLION_TH,
            completion_cost_per_token=15 * ONE_MILLION_TH,
            source="https://docs.anthropic.com/en/docs/about-claude/models/all-models#model-comparison-table",
        ),
    ),
    Model.CLAUDE_3_OPUS_20240229: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=15 * ONE_MILLION_TH,
            completion_cost_per_token=15 * ONE_MILLION_TH,
            source="https://docs.anthropic.com/en/docs/about-claude/models/all-models#model-comparison-table",
        ),
    ),
    Model.CLAUDE_3_HAIKU_20240307: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.25 * ONE_MILLION_TH,
            completion_cost_per_token=1.25 * ONE_MILLION_TH,
            source="https://docs.anthropic.com/en/docs/about-claude/models/all-models#model-comparison-table",
        ),
    ),
    Model.CLAUDE_4_1_OPUS_20250805: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=15 * ONE_MILLION_TH,
            completion_cost_per_token=75 * ONE_MILLION_TH,
            source="https://www.anthropic.com/pricing#api",
        ),
    ),
}

AZURE_PROVIDER_DATA: ProviderDataByModel = {
    Model.GPT_4O_2024_11_20: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=2.5 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.5,
            completion_cost_per_token=10 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
    ),
    Model.GPT_4O_2024_08_06: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=2.5 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.5,
            completion_cost_per_token=10 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
    ),
    Model.O3_MINI_2025_01_31: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=1.10 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.5,
            completion_cost_per_token=4.40 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
    ),
    Model.GPT_4O_MINI_2024_07_18: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.15 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.5,
            completion_cost_per_token=0.6 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
    ),
    Model.O1_2024_12_17: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=15 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.5,
            completion_cost_per_token=60 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
    ),
    Model.GPT_41_2025_04_14: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=2 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.75,
            completion_cost_per_token=8 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
    ),
    Model.GPT_41_MINI_2025_04_14: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.4 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.75,
            completion_cost_per_token=1.6 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
    ),
    Model.GPT_41_NANO_2025_04_14: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.1 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.75,
            completion_cost_per_token=0.4 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
    ),
    Model.O4_MINI_2025_04_16: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=1.1 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.75,
            completion_cost_per_token=4.4 * ONE_MILLION_TH,
            source="https://openai.com/api/pricing/",
        ),
    ),
}

GOOGLE_GEMINI_API_PROVIDER_DATA: ProviderDataByModel = {
    Model.GEMINI_2_5_FLASH: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.30 * ONE_MILLION_TH,
            completion_cost_per_token=2.50 * ONE_MILLION_TH,
            source="https://ai.google.dev/gemini-api/docs/pricing#gemini-2.5-flash",
            prompt_cached_tokens_discount=0.75,
        ),
        audio_price=AudioPricePerToken(
            audio_input_cost_per_token=1.0 * ONE_MILLION_TH,
        ),
    ),
    Model.GEMINI_2_5_PRO: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=1.25 * ONE_MILLION_TH,
            completion_cost_per_token=10 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.75,
            source="https://cloud.google.com/vertex-ai/generative-ai/pricing",
            thresholded_prices=[
                ThresholdedTextPricePerToken(
                    threshold=200_000,
                    prompt_cost_per_token_over_threshold=2.5 * ONE_MILLION_TH,
                    completion_cost_per_token_over_threshold=15 * ONE_MILLION_TH,
                ),
            ],
        ),
    ),
    Model.GEMINI_2_5_FLASH_LITE: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.1 * ONE_MILLION_TH,
            completion_cost_per_token=0.40 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.75,
            source="https://ai.google.dev/gemini-api/docs/pricing#gemini-2.5-flash-lite",
        ),
        audio_price=AudioPricePerToken(
            audio_input_cost_per_token=0.3 * ONE_MILLION_TH,
        ),
    ),
    Model.GEMINI_2_0_FLASH_LITE_001: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.075 * ONE_MILLION_TH,
            completion_cost_per_token=0.30 * ONE_MILLION_TH,
            source="https://ai.google.dev/gemini-api/docs/pricing#2_0flash_lite",
            prompt_cached_tokens_discount=0.75,
        ),
    ),
    Model.GEMINI_2_0_FLASH_001: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.10 * ONE_MILLION_TH,
            completion_cost_per_token=0.40 * ONE_MILLION_TH,
            source="https://ai.google.dev/pricing#2_0flash-001",
            prompt_cached_tokens_discount=0.75,
        ),
        audio_price=AudioPricePerToken(
            audio_input_cost_per_token=0.70 * ONE_MILLION_TH,
        ),
    ),
}

FIREWORKS_PROVIDER_DATA: ProviderDataByModel = {
    # Model.LLAMA3_70B_8192: ModelProviderData(
    #     text_price=TextPricePerToken(
    #         prompt_cost_per_token=0.90 * ONE_MILLION_TH,
    #         completion_cost_per_token=0.90 * ONE_MILLION_TH,
    #         source="https://fireworks.ai/pricing",
    #     ),
    #     # see: https://docs.fireworks.ai/guides/function-calling#supported-models
    # ),
    # Model.LLAMA3_8B_8192: ModelProviderData(
    #     text_price=TextPricePerToken(
    #         prompt_cost_per_token=0.20 * ONE_MILLION_TH,
    #         completion_cost_per_token=0.20 * ONE_MILLION_TH,
    #         source="https://fireworks.ai/pricing",
    #     ),
    #     # see: https://docs.fireworks.ai/guides/function-calling#supported-models
    # ),
    Model.LLAMA_3_1_8B: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.20 * ONE_MILLION_TH,
            completion_cost_per_token=0.20 * ONE_MILLION_TH,
            source="https://fireworks.ai/pricing",
        ),
        # see: https://docs.fireworks.ai/guides/function-calling#supported-models
    ),
    Model.LLAMA_3_1_70B: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.90 * ONE_MILLION_TH,
            completion_cost_per_token=0.90 * ONE_MILLION_TH,
            source="https://fireworks.ai/pricing",
        ),
    ),
    Model.LLAMA_3_1_405B: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=3.0 * ONE_MILLION_TH,
            completion_cost_per_token=3.0 * ONE_MILLION_TH,
            source="https://fireworks.ai/pricing",
        ),
    ),
    Model.LLAMA_3_3_70B: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.90 * ONE_MILLION_TH,
            completion_cost_per_token=0.90 * ONE_MILLION_TH,
            source="https://fireworks.ai/pricing",
            # LLAMA_3_3_70B is not a MoE model, so in 16.1B+ category
        ),
        # see: https://docs.fireworks.ai/guides/function-calling#supported-models
    ),
    Model.DEEPSEEK_V3_1_TERMINUS: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=1.2 * ONE_MILLION_TH,
            completion_cost_per_token=1.2 * ONE_MILLION_TH,
            source="https://fireworks.ai/pricing",
        ),
    ),
    Model.DEEPSEEK_R1_0528: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=3.0 * ONE_MILLION_TH,
            completion_cost_per_token=3.0 * ONE_MILLION_TH,
            source="https://app.fireworks.ai/models/fireworks/deepseek-r1-0528",
        ),
    ),
    Model.DEEPSEEK_V3_0324: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=1.20 * ONE_MILLION_TH,
            completion_cost_per_token=1.20 * ONE_MILLION_TH,
            source="https://fireworks.ai/pricing",
        ),
    ),
    Model.LLAMA_4_MAVERICK_BASIC: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.22 * ONE_MILLION_TH,
            completion_cost_per_token=0.88 * ONE_MILLION_TH,
            source="https://fireworks.ai/pricing",
        ),
    ),
    Model.LLAMA_4_SCOUT_BASIC: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.15 * ONE_MILLION_TH,
            completion_cost_per_token=0.60 * ONE_MILLION_TH,
            source="https://fireworks.ai/pricing",
        ),
    ),
    # Fall back for the fast groq version
    Model.LLAMA_4_MAVERICK_FAST: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.22 * ONE_MILLION_TH,
            completion_cost_per_token=0.88 * ONE_MILLION_TH,
            source="https://fireworks.ai/pricing",
        ),
    ),
    Model.LLAMA_4_SCOUT_FAST: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.15 * ONE_MILLION_TH,
            completion_cost_per_token=0.60 * ONE_MILLION_TH,
            source="https://fireworks.ai/pricing",
        ),
    ),
    Model.QWEN3_235B_A22B: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.22 * ONE_MILLION_TH,
            completion_cost_per_token=0.88 * ONE_MILLION_TH,
            source="https://app.fireworks.ai/models/fireworks/qwen3-235b-a22b",
        ),
    ),
    Model.QWEN3_30B_A3B: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.15 * ONE_MILLION_TH,
            completion_cost_per_token=0.60 * ONE_MILLION_TH,
            source="https://app.fireworks.ai/models/fireworks/qwen3-30b-a3b",
        ),
    ),
    Model.GPT_OSS_20B: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.07 * ONE_MILLION_TH,
            completion_cost_per_token=0.3 * ONE_MILLION_TH,
            source="https://app.fireworks.ai/models/fireworks/gpt-oss-20b",
        ),
    ),
    Model.GPT_OSS_120B: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.15 * ONE_MILLION_TH,
            completion_cost_per_token=0.6 * ONE_MILLION_TH,
            source="https://app.fireworks.ai/models/fireworks/gpt-oss-120b",
        ),
    ),
    Model.KIMI_K2_INSTRUCT: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.6 * ONE_MILLION_TH,
            completion_cost_per_token=2.5 * ONE_MILLION_TH,
            source="https://app.fireworks.ai/models/fireworks/kimi-k2-instruct",
        ),
    ),
    Model.KIMI_K2_INSTRUCT_0905: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.6 * ONE_MILLION_TH,
            completion_cost_per_token=2.5 * ONE_MILLION_TH,
            source="https://app.fireworks.ai/models/fireworks/kimi-k2-instruct-0905",
        ),
    ),
}

XAI_PROVIDER_DATA: ProviderDataByModel = {
    Model.GROK_CODE_FAST_1: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.2 * ONE_MILLION_TH,
            completion_cost_per_token=1.5 * ONE_MILLION_TH,
            prompt_cached_tokens_discount=0.9,
            source="https://docs.x.ai/docs/models/grok-code-fast-1",
        ),
    ),
    Model.GROK_4_FAST: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.2 * ONE_MILLION_TH,
            completion_cost_per_token=0.5 * ONE_MILLION_TH,
            source="https://docs.x.ai/docs/models/grok-4-fast",
            prompt_cached_tokens_discount=0.75,
            thresholded_prices=[
                ThresholdedTextPricePerToken(
                    threshold=128_000,
                    prompt_cost_per_token_over_threshold=0.4 * ONE_MILLION_TH,
                    completion_cost_per_token_over_threshold=1 * ONE_MILLION_TH,
                ),
            ],
        ),
    ),
    Model.GROK_4_0709: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=3 * ONE_MILLION_TH,
            completion_cost_per_token=15 * ONE_MILLION_TH,
            source="https://docs.x.ai/docs/models/grok-4-0709",
        ),
    ),
    Model.GROK_3_BETA: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=3 * ONE_MILLION_TH,
            completion_cost_per_token=15 * ONE_MILLION_TH,
            source="https://docs.x.ai/docs/models#models-and-pricing",
        ),
    ),
    Model.GROK_3_FAST_BETA: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=5 * ONE_MILLION_TH,
            completion_cost_per_token=25 * ONE_MILLION_TH,
            source="https://docs.x.ai/docs/models#models-and-pricing",
        ),
    ),
    Model.GROK_3_MINI_BETA: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.3 * ONE_MILLION_TH,
            completion_cost_per_token=0.5 * ONE_MILLION_TH,
            source="https://docs.x.ai/docs/models#models-and-pricing",
        ),
    ),
    Model.GROK_3_MINI_FAST_BETA: ModelProviderData(
        text_price=TextPricePerToken(
            prompt_cost_per_token=0.6 * ONE_MILLION_TH,
            completion_cost_per_token=4 * ONE_MILLION_TH,
            source="https://docs.x.ai/docs/models#models-and-pricing",
        ),
    ),
}


type ProviderModelDataMapping = dict[Provider, ProviderDataByModel]

# Pricing and lifecycle data for each model / provider couple
MODEL_PROVIDER_DATAS: ProviderModelDataMapping = {
    # ------------------------------------------------------------------------------------------------
    # Google Vertex AI
    Provider.GOOGLE: GOOGLE_PROVIDER_DATA,
    # ------------------------------------------------------------------------------------------------
    # OpenAI
    Provider.OPEN_AI: OPENAI_PROVIDER_DATA,
    # ------------------------------------------------------------------------------------------------
    # Amazon Bedrock
    Provider.AMAZON_BEDROCK: AMAZON_BEDROCK_PROVIDER_DATA,
    # ------------------------------------------------------------------------------------------------
    # Groq
    Provider.GROQ: GROQ_PROVIDER_DATA,
    # ------------------------------------------------------------------------------------------------
    # MistralAI
    Provider.MISTRAL_AI: MISTRAL_PROVIDER_DATA,
    # ------------------------------------------------------------------------------------------------
    # Anthropic
    Provider.ANTHROPIC: ANTHROPIC_PROVIDER_DATA,
    # ------------------------------------------------------------------------------------------------
    # Azure
    Provider.AZURE_OPEN_AI: AZURE_PROVIDER_DATA,
    # ------------------------------------------------------------------------------------------------
    # Google Gemini
    Provider.GOOGLE_GEMINI: GOOGLE_GEMINI_API_PROVIDER_DATA,
    # ------------------------------------------------------------------------------------------------
    # Fireworks
    Provider.FIREWORKS: FIREWORKS_PROVIDER_DATA,
    # ------------------------------------------------------------------------------------------------
    # XAI
    Provider.X_AI: XAI_PROVIDER_DATA,
}
