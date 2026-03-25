export const TOPIC_CATALOG = [
  {
    key: 'Agent',
    labelCn: '智能体',
    labelEn: 'Agents',
    descriptionCn: '工具使用、任务规划、自动执行与多智能体协作。',
    descriptionEn: 'Tool use, planning, autonomous workflows, and multi-agent systems.'
  },
  {
    key: 'Reasoning',
    labelCn: '推理',
    labelEn: 'Reasoning',
    descriptionCn: '数学、逻辑、链式思维与复杂问题求解。',
    descriptionEn: 'Math, logic, chain-of-thought, and complex problem solving.'
  },
  {
    key: 'Training_Opt',
    labelCn: '训练优化',
    labelEn: 'Training Optimization',
    descriptionCn: '量化、蒸馏、LoRA、分布式训练与效率优化。',
    descriptionEn: 'Quantization, distillation, LoRA, distributed training, and efficiency gains.'
  },
  {
    key: 'RAG',
    labelCn: '检索增强',
    labelEn: 'RAG',
    descriptionCn: '检索增强生成、知识库、长上下文与信息融合。',
    descriptionEn: 'Retrieval-augmented generation, knowledge bases, long context, and retrieval systems.'
  },
  {
    key: 'Multimodal',
    labelCn: '多模态',
    labelEn: 'Multimodal',
    descriptionCn: '视觉语言、跨模态理解与统一多模态模型。',
    descriptionEn: 'Vision-language systems, cross-modal understanding, and unified multimodal models.'
  },
  {
    key: 'Code_Intelligence',
    labelCn: '代码智能',
    labelEn: 'Code Intelligence',
    descriptionCn: '代码生成、补全、调试与软件工程智能体。',
    descriptionEn: 'Code generation, completion, debugging, and software engineering agents.'
  },
  {
    key: 'Vision_Image',
    labelCn: '视觉图像',
    labelEn: 'Vision & Image',
    descriptionCn: '图像生成、视觉理解、分割与扩散模型。',
    descriptionEn: 'Image generation, visual understanding, segmentation, and diffusion models.'
  },
  {
    key: 'Video',
    labelCn: '视频',
    labelEn: 'Video',
    descriptionCn: '视频生成、视频理解与时序建模。',
    descriptionEn: 'Video generation, video understanding, and temporal modeling.'
  },
  {
    key: 'Safety_Alignment',
    labelCn: '安全对齐',
    labelEn: 'Safety & Alignment',
    descriptionCn: '对齐、红队、越狱防护与安全评估。',
    descriptionEn: 'Alignment, red teaming, jailbreak defense, and safety evaluation.'
  },
  {
    key: 'Robotics',
    labelCn: '机器人',
    labelEn: 'Robotics',
    descriptionCn: '具身智能、操作、导航与真实世界执行。',
    descriptionEn: 'Embodied AI, manipulation, navigation, and real-world execution.'
  },
  {
    key: 'Audio',
    labelCn: '音频语音',
    labelEn: 'Audio',
    descriptionCn: '语音识别、语音合成、音频理解与生成。',
    descriptionEn: 'Speech recognition, speech synthesis, and audio understanding/generation.'
  },
  {
    key: 'Interpretability',
    labelCn: '可解释性',
    labelEn: 'Interpretability',
    descriptionCn: '机制解释、注意力分析与模型内部机理研究。',
    descriptionEn: 'Mechanistic interpretability, attention analysis, and model internals.'
  },
  {
    key: 'Benchmarking',
    labelCn: '评测基准',
    labelEn: 'Benchmarking',
    descriptionCn: '评测集、指标体系、基准构建与系统评估。',
    descriptionEn: 'Benchmarks, metrics, evaluation suites, and dataset-driven assessment.'
  },
  {
    key: 'Data_Engineering',
    labelCn: '数据工程',
    labelEn: 'Data Engineering',
    descriptionCn: '合成数据、数据清洗、数据管线与预训练数据。',
    descriptionEn: 'Synthetic data, data curation, pipelines, and pretraining corpora.'
  },
  {
    key: 'Industry_Trends',
    labelCn: '行业趋势',
    labelEn: 'Industry Trends',
    descriptionCn: '综述、路线图、产业观察与长期判断。',
    descriptionEn: 'Surveys, roadmaps, industry observations, and long-term trends.'
  }
]

export function getTopicMeta(topicKey) {
  return TOPIC_CATALOG.find((item) => item.key === topicKey) || null
}
