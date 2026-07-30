# Transformer Architecture

- **Scaled Dot‑Product Attention**: `Attention(Q,K,V)=softmax(QK^T/√d_k)V`.
- **Multi‑Head Attention**: parallel heads with projection matrices `W^Q,W^K,W^V,W^O`.
- **Positional Encoding**: sinusoidal (Vaswani 2017), learned, rotary (RoPE), ALiBi, YaRN.
- **Normalization**: LayerNorm, RMSNorm, DeepNorm, Pre‑LN vs Post‑LN.
- **Feed‑Forward**: 2‑layer MLP with GELU, SwiGLU, Mixture‑of‑Experts.
- **Variants**: Reversible blocks, Compressive Transformers, Cross‑Attention‑only encoder‑decoder.
- **Efficiency**: Reformer (LSH), Performer (kernel), FlashAttention, Mamba (SSM).