import re

FOCUS_THRESHOLD = 80
WATCHING_THRESHOLD = 50

FOCUS_CAPACITY = 5
WATCHING_CAPACITY = 12

SUMMARY_CATEGORIES = ("focus", "watching", "candidate")
CANDIDATE_REASONS = ("low_score", "capacity_overflow", "reviewer_rejected")
TASK_STATUSES = ("RUNNING", "SUCCESS", "FAILED")
AI_TRACE_STAGES = ("editor", "writer", "reviewer")
AI_TRACE_STATUSES = ("generated", "accepted", "rejected", "invalid")

DIRECTIONS = (
    "Agent",
    "Reasoning",
    "Training_Opt",
    "RAG",
    "Multimodal",
    "Code_Intelligence",
    "Vision_Image",
    "Video",
    "Safety_Alignment",
    "Robotics",
    "Audio",
    "Interpretability",
    "Benchmarking",
    "Data_Engineering",
    "Industry_Trends",
)

TOP_INSTITUTIONS = (
    "Google",
    "DeepMind",
    "OpenAI",
    "Meta",
    "FAIR",
    "Microsoft",
    "Anthropic",
    "NVIDIA",
    "Stanford",
    "MIT",
    "UC Berkeley",
    "Carnegie Mellon",
    "CMU",
    "Harvard",
    "Oxford",
    "Cambridge",
    "Princeton",
    "ETH Zurich",
    "Tsinghua University",
    "Peking University",
    "THU",
    "PKU",
    "Shanghai Jiao Tong",
    "SJTU",
    "Fudan University",
    "Zhejiang University",
    "ZJU",
    "Huawei",
    "Noah's Ark",
    "Baidu",
    "Tencent",
    "Alibaba",
    "DAMO Academy",
    "ByteDance",
    "TikTok",
    "Kuaishou",
    "SenseTime",
    "MEGVII",
    "IBM Research",
    "Amazon",
    "Salesforce",
    "Apple AI",
    "Hugging Face",
    "Allen Institute",
    "AI21",
)

TOP_CONFERENCES = ("ICLR", "NeurIPS", "CVPR", "ICML", "ACL", "EMNLP")
PRACTITIONER_KEYWORDS = ("Deploy", "Quantization", "RAG", "Inference", "Agent")

TAXONOMY_RULES = (
    ("Agent", ("agent", "tool use", "autonomous", "planning")),
    ("Reasoning", ("reasoning", "chain-of-thought", "cot", "math", "theorem")),
    (
        "Training_Opt",
        ("quantization", "lora", "peft", "distributed training", "optimization", "memory-efficient"),
    ),
    ("RAG", ("rag", "retrieval-augmented", "vector database", "long-context")),
    ("Multimodal", ("multimodal", "vision-language", "vlm", "cross-modal")),
    ("Code_Intelligence", ("code generation", "code completion", "program synthesis")),
    ("Vision_Image", ("diffusion", "image generation", "segmentation", "stable diffusion")),
    ("Video", ("video generation", "video understanding", "sora", "temporal consistency")),
    ("Safety_Alignment", ("rlhf", "alignment", "red teaming", "jailbreak", "safety", "toxicity")),
    ("Robotics", ("robotics", "embodied ai", "manipulation", "navigation")),
    ("Audio", ("audio generation", "speech recognition", "tts", "asr")),
    ("Interpretability", ("interpretability", "mechanistic", "attention map", "explainable")),
    ("Benchmarking", ("benchmark", "evaluation", "dataset", "metric")),
    ("Data_Engineering", ("synthetic data", "data curation", "data pipeline", "pre-training data")),
    ("Industry_Trends", ("survey", "review", "perspective", "roadmap")),
)


def build_literal_boundary_pattern(keyword: str) -> re.Pattern[str]:
    escaped = re.escape(keyword)
    return re.compile(rf"\b(?:{escaped})\b", re.IGNORECASE)
