# Transformer Architecture Research

## Historical Development

### Pre-Transformer Era (2014-2016)
- 2014: Bahdanau et al. introduced attention mechanism for NMT
- 2015: Luong et al. proposed global attention
- 2014-2016: Sutskever et al. developed seq2seq encoder-decoder

### Foundational (2017-2018)
- 2017: Vaswani et al. published "Attention Is All You Need"
- 2018: Devlin et al. introduced BERT
- 2018: Radford et al. released GPT-1

### Scaling Era (2019-2020)
- 2019: Dai et al. introduced Transformer-XL
- 2019: Beltagy et al. proposed Longformer
- 2020: Brown et al. released GPT-3

### Efficiency & Specialization (2021-2022)
- 2021: Su et al. introduced RoFormer
- 2022: Touvron et al. released LLaMA
- 2022: Ouyang et al. introduced InstructGPT

### Emerging Trends (2022-Present)
- 2022: Dosovitskiy et al. introduced Vision Transformer
- 2023: Mamba introduced SSM-based modeling

## Core Components

### Attention Mechanism
- Scaled Dot-Product Attention: `Attention(Q,K,V)=softmax(QK^T/\sqrt{d_k})V`
- Multi-Head Attention with projection matrices
- FlashAttention for memory efficiency

### Positional Encoding
- Sinusoidal (Vaswani 2017)
- Learned embeddings
- RoPE, ALiBi, YaRN

### Normalization
- LayerNorm, RMSNorm, DeepNorm
- Pre-LN vs Post-LN

### Feed-Forward Networks
- 2-layer MLP with GELU/SwiGLU
- Mixture-of-Experts

## Key Variants

### Encoder-Only
- BERT (Devlin 2018)
- RoBERTa (Liu 2019)

### Decoder-Only
- GPT-1 (Radford 2018)
- GPT-2 (Child 2019)
- GPT-3 (Brown 2020)

### Hybrid/Advanced
- T5 (Raffel 2019)
- Switch Transformer (Fedus 2022)
- Mamba (Peng 2023)

## Key Papers
- Vaswani et al. 2017 - "Attention Is All You Need"
- Devlin et al. 2018 - "BERT"
- Brown et al. 2020 - "Language Models are Few-Shot Learners"
- Ouyang et al. 2022 - "InstructGPT"
- Peng et al. 2023 - "Mamba"