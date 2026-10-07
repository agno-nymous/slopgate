import importlib.util
import os
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace

MODEL = "nomic-ai/CodeRankEmbed"
PREFIX = "Represent this query for searching relevant code: "
COMPILED = Path.home() / ".cache" / "slopgate" / "coderank-int8.onnx"
TOKENIZER = COMPILED.with_name("tokenizer.json")
MAX_TOKENS = 512
model = None
lock = threading.Lock()


def encode(texts: list[str], query: bool = False) -> list[list[float]]:
    load()
    if query:
        texts = [PREFIX + text for text in texts]
    return model.encode(texts, normalize_embeddings=True).tolist()


def preload() -> None:
    threading.Thread(target=load, daemon=True).start()


def load() -> None:
    global model
    with lock:
        if model is None:
            onnx = COMPILED.exists() and importlib.util.find_spec("onnxruntime")
            model = onnx_model() if onnx else torch_model()


def torch_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL, trust_remote_code=True)


def onnx_model():
    import numpy
    import onnxruntime
    from tokenizers import Tokenizer

    options = onnxruntime.SessionOptions()
    options.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_DISABLE_ALL
    session = onnxruntime.InferenceSession(str(COMPILED), options, providers=["CPUExecutionProvider"])
    tokenizer = Tokenizer.from_file(str(TOKENIZER))
    tokenizer.enable_truncation(MAX_TOKENS)

    def vector(text):
        ids = numpy.array([tokenizer.encode(text).ids])
        cls = session.run(None, {"input_ids": ids, "attention_mask": numpy.ones_like(ids)})[0][0, 0]
        return cls / numpy.linalg.norm(cls)

    return SimpleNamespace(encode=lambda texts, normalize_embeddings: numpy.array([vector(text) for text in texts]))


def compile_model() -> bool:
    if COMPILED.exists():
        return True
    try:
        import onnxruntime
        from onnxruntime.quantization import QuantType, quantize_dynamic
    except ImportError:
        return False
    import torch

    st = torch_model()
    sample = st.tokenizer(["def f(x):\n    return x + 1"], return_tensors="pt")
    axes = {0: "batch", 1: "tokens"}
    COMPILED.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=COMPILED.parent) as tmp:
        fp32, int8, optimized = (os.path.join(tmp, name) for name in ("fp32.onnx", "int8.onnx", "optimized.onnx"))
        torch.onnx.export(
            st[0].auto_model.cpu().eval(),
            (sample["input_ids"], sample["attention_mask"]),
            fp32,
            input_names=["input_ids", "attention_mask"],
            output_names=["hidden"],
            dynamic_axes={"input_ids": axes, "attention_mask": axes},
            opset_version=17,
            dynamo=False,
        )
        quantize_dynamic(fp32, int8, weight_type=QuantType.QInt8)
        options = onnxruntime.SessionOptions()
        options.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_EXTENDED
        options.optimized_model_filepath = optimized
        onnxruntime.InferenceSession(int8, options, providers=["CPUExecutionProvider"])
        st.tokenizer.backend_tokenizer.save(str(TOKENIZER))
        os.replace(optimized, COMPILED)
    return True
