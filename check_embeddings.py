
import json
import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

MODEL_NAME = "openai/clip-vit-base-patch32"

model = CLIPModel.from_pretrained(MODEL_NAME).eval()
processor = CLIPProcessor.from_pretrained(MODEL_NAME)

with open("filenames.json", "r") as f:
    filenames = json.load(f)

embeddings = np.load("embeddings.npy")

for k in [0, 123, 499]:
    image_path = f"images/images/{filenames[k]}"
    image = Image.open(image_path).convert("RGB")

    inputs = processor(images=image, return_tensors="pt")

    with torch.no_grad():
        output = model.vision_model(**inputs)
        vector = model.visual_projection(output.pooler_output)

    vector = vector / vector.norm(dim=-1, keepdim=True)
    vector = vector.cpu().numpy()[0]

    similarity = float(vector @ embeddings[k])

    print(
        f"Index: {k} | "
        f"Filename: {filenames[k]} | "
        f"Cosine similarity: {similarity:.6f}"
    )
