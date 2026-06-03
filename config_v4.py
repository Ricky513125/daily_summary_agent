"""V4 专属配置：扩展查询关键词（新增量化相关），并定义领域排除规则。

与 config.py 解耦，避免影响 v1/v2/v3。所有项可通过环境变量覆盖：
- KEYWORDS_V4
- EXCLUDE_CATEGORIES_V4
- EXCLUDE_KEYWORDS_V4
"""
import os

# arXiv 检索建议使用英文（中文几乎检索不到论文）
_DEFAULT_KEYWORDS_V4 = (
    # 大模型 / 多模态 / 视觉
    "large language model,LLM,multimodal large language model,MLLM,"
    "vision language model,VLM,diffusion model,transformer,"
    # 训练 / 后训练 / 对齐 / 强化学习
    "post-training,supervised fine-tuning,instruction tuning,"
    "reinforcement learning from human feedback,RLHF,DPO,"
    "preference optimization,reasoning model,chain-of-thought,"
    # 量化（重点新增）
    "quantization,model quantization,low-bit quantization,"
    "INT4 quantization,INT8 quantization,FP8 quantization,"
    "weight-only quantization,activation quantization,"
    "GPTQ,AWQ,SmoothQuant,SpQR,QuIP,"
    "KV cache quantization,post-training quantization,"
    "quantization-aware training,mixed-precision inference,"
    # 推理加速 / 部署
    "LLM inference,LLM inference acceleration,LLM serving,"
    "speculative decoding,paged attention,FlashAttention"
)

# 领域排除：机器人硬件 / 医学 / 安全
# 命中任一 arXiv 分类（小写完整匹配或前缀 q-bio）即剔除
_DEFAULT_EXCLUDE_CATEGORIES_V4 = (
    # 机器人
    "cs.RO,"
    # 安全 / 密码
    "cs.CR,"
    # 生物医学
    "q-bio,q-bio.BM,q-bio.CB,q-bio.GN,q-bio.MN,q-bio.NC,"
    "q-bio.OT,q-bio.PE,q-bio.QM,q-bio.SC,q-bio.TO,"
    # 医学影像
    "eess.IV"
)

# 标题/摘要黑名单（大小写不敏感，子串匹配；尽量挑歧义少的词，避免误杀通用 ML 论文）
_DEFAULT_EXCLUDE_KEYWORDS_V4 = (
    # —— 机器人硬件 / 本体
    "robot,robotic,robotics,manipulator,robotic manipulation,"
    "gripper,humanoid,quadruped,legged locomotion,end-effector,"
    "teleoperation,SLAM,UAV,drone,autonomous driving,self-driving,"
    "robot arm,robot policy,robot learning,visuomotor,"
    # —— 医学 / 生物医学
    "medical,clinical,healthcare,health-care,patient,patients,hospital,"
    "radiology,radiograph,MRI,CT scan,X-ray,ultrasound,pathology,histology,"
    "electronic health record,EHR,EEG,ECG,fMRI,biomedical,biomarker,"
    "genomics,drug discovery,protein structure,molecular dynamics,"
    "diagnosis,diagnostic,disease,tumor,cancer,lesion,"
    # —— 安全 / 密码 / 攻击
    "malware,phishing,intrusion detection,cybersecurity,cyber-security,"
    "cryptography,cryptographic,vulnerability,exploit,side-channel,"
    "backdoor attack,trojan attack,jailbreak attack on,"
    "network attack,DDoS,fuzzing"
)


def _split_csv(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


KEYWORDS_V4: list[str] = _split_csv(os.getenv("KEYWORDS_V4") or _DEFAULT_KEYWORDS_V4)

EXCLUDE_CATEGORIES_V4: list[str] = [
    c.lower() for c in _split_csv(os.getenv("EXCLUDE_CATEGORIES_V4") or _DEFAULT_EXCLUDE_CATEGORIES_V4)
]

EXCLUDE_KEYWORDS_V4: list[str] = [
    k.lower() for k in _split_csv(os.getenv("EXCLUDE_KEYWORDS_V4") or _DEFAULT_EXCLUDE_KEYWORDS_V4)
]
