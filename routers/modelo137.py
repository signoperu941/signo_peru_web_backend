import os
import json
import numpy as np
import tensorflow as tf
import cv2

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"


# CONFIGURACION
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "..", "modelo_137_clases", "modelo_tf")
CLASS_MAPPING_PATH = os.path.join(BASE_DIR, "..", "class_mapping.json")

CLIP_LEN = 24
FRAME_SIZE = 192

# CARGA DEL MODELO
with open(CLASS_MAPPING_PATH, "r", encoding="utf-8") as f:
    idx_to_class = {v: k for k, v in json.load(f).items()}

print(f"[modelo-137] Clases cargadas: {len(idx_to_class)}")
print("[modelo-137] Cargando modelo...")

sign_model = tf.saved_model.load(MODEL_PATH)
infer_fn = sign_model.signatures["serving_default"]

INPUT_KEY = list(infer_fn.structured_input_signature[1].keys())[0]
OUTPUT_KEY = list(infer_fn.structured_outputs.keys())[0]
print(f"[modelo-137] Listo | Input: {INPUT_KEY} | Output: {OUTPUT_KEY}")


# FUNCIONES
def process_video(video_path):
    cap = cv2.VideoCapture(video_path)
    frames = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    cap.release()

    total = len(frames)
    if total == 0:
        return None

    if total >= CLIP_LEN:
        indices = np.linspace(0, total - 1, CLIP_LEN).astype(int)
    else:
        indices = np.concatenate(
            [np.arange(total), np.full(CLIP_LEN - total, total - 1, dtype=int)]
        )

    processed = []
    for i in indices:
        f = cv2.resize(
            frames[i], (FRAME_SIZE, FRAME_SIZE), interpolation=cv2.INTER_LINEAR
        )
        f = f.astype(np.float32) / 255.0
        processed.append(np.transpose(f, (2, 0, 1)))

    video_array = np.stack(processed, axis=0)
    video_array = np.transpose(video_array, (1, 0, 2, 3))
    return np.expand_dims(video_array, axis=0)


def predict(clip):
    logits = infer_fn(**{INPUT_KEY: tf.constant(clip, dtype=tf.float32)})[
        OUTPUT_KEY
    ].numpy()

    exp_logits = np.exp(logits - np.max(logits, axis=1, keepdims=True))
    probs = (exp_logits / np.sum(exp_logits, axis=1, keepdims=True))[0]

    # Top 5 con probabilidades crudas
    top5_indices = np.argsort(probs)[::-1][:5]
    top5_raw = [
        {"palabra": idx_to_class[int(i)], "confianza": float(probs[i])}
        for i in top5_indices
    ]

    # 1) conf_top5: renormalizar dentro del top5
    total = sum(p["confianza"] for p in top5_raw)
    conf_top5 = round(top5_raw[0]["confianza"] / total * 100, 2) if total > 0 else 0.0

    # 2) certeza: separacion entre p1 y p2 usando sigmoid
    p1 = top5_raw[0]["confianza"]
    p2 = top5_raw[1]["confianza"] if len(top5_raw) > 1 else p1
    ratio = p1 / p2 if p2 > 0 else 1.0
    certeza = round(100 / (1 + np.exp(-3.5 * np.log(ratio))), 2)

    # Top5 renormalizado para mostrar en UI
    top5_renorm = [
        {"palabra": p["palabra"], "confianza": round(p["confianza"] / total * 100, 2)}
        for p in top5_raw
    ]

    return {
        "top5": top5_renorm,
        "conf_top5": conf_top5,
        "certeza": certeza,
    }
