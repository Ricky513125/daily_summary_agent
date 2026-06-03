"""V5 专属配置：关键词、排除分类、排除关键词。

所有项可通过环境变量覆盖：
- KEYWORDS_V5
- EXCLUDE_CATEGORIES_V5
- EXCLUDE_KEYWORDS_V5
"""
import os

# arXiv 检索建议使用英文（中文几乎检索不到论文）
_DEFAULT_KEYWORDS_V5 = (
    # 大模型 / 多模态 / 视觉
    "large language model,LLM,multimodal large language model,MLLM,"
    "vision language model,VLM,diffusion model,transformer,"
    # 训练 / 后训练 / 对齐 / 强化学习
    "post-training,supervised fine-tuning,instruction tuning,"
    "reinforcement learning from human feedback,RLHF,DPO,"
    "preference optimization,reasoning model,chain-of-thought,"
    # 量化
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

_DEFAULT_EXCLUDE_CATEGORIES_V5 = (
    "cs.RO,"
    "cs.CR,"
    "q-bio,q-bio.BM,q-bio.CB,q-bio.GN,q-bio.MN,q-bio.NC,"
    "q-bio.OT,q-bio.PE,q-bio.QM,q-bio.SC,q-bio.TO,"
    "eess.IV"
)

_DEFAULT_EXCLUDE_KEYWORDS_V5 = (
    # 机器人硬件 / 本体
    "robot,robotic,robotics,manipulator,robotic manipulation,"
    "gripper,humanoid,quadruped,legged locomotion,end-effector,"
    "teleoperation,SLAM,UAV,drone,autonomous driving,self-driving,"
    "robot arm,robot policy,robot learning,visuomotor,"
    # 医学 / 生物医学
    "medical,clinical,healthcare,health-care,patient,patients,hospital,"
    "radiology,radiograph,MRI,CT scan,X-ray,ultrasound,pathology,histology,"
    "electronic health record,EHR,EEG,ECG,fMRI,biomedical,biomarker,"
    "genomics,drug discovery,protein structure,molecular dynamics,"
    "diagnosis,diagnostic,disease,tumor,cancer,lesion,"
    # 安全 / 密码 / 攻击
    "malware,phishing,intrusion detection,cybersecurity,cyber-security,"
    "cryptography,cryptographic,vulnerability,exploit,side-channel,"
    "backdoor attack,trojan attack,jailbreak attack on,"
    "network attack,DDoS,fuzzing"
)


def _split_csv(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


KEYWORDS_V5: list[str] = _split_csv(os.getenv("KEYWORDS_V5") or _DEFAULT_KEYWORDS_V5)

EXCLUDE_CATEGORIES_V5: list[str] = [
    c.lower() for c in _split_csv(os.getenv("EXCLUDE_CATEGORIES_V5") or _DEFAULT_EXCLUDE_CATEGORIES_V5)
]

EXCLUDE_KEYWORDS_V5: list[str] = [
    k.lower() for k in _split_csv(os.getenv("EXCLUDE_KEYWORDS_V5") or _DEFAULT_EXCLUDE_KEYWORDS_V5)
]
