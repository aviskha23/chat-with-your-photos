
from fastapi import FastAPI, Query, HTTPException
import faiss
import numpy as np
import json
import torch
from transformers import CLIPModel, CLIPProcessor
import os
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import UploadFile, File
from PIL import Image
import io

app = FastAPI(title="Chat With Your Photos")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Load saved data once when the application starts
index = faiss.read_index("clip.index")
embeddings = np.load("embeddings.npy")

with open("filenames.json", "r") as f:
    filenames = json.load(f)

with open("image_ids.json", "r") as f:
    image_ids = json.load(f)

# Load CLIP once, not for every search request
MODEL_NAME = "openai/clip-vit-base-patch32"

model = CLIPModel.from_pretrained(MODEL_NAME)
processor = CLIPProcessor.from_pretrained(MODEL_NAME)

model.eval()


@app.get("/")
def home():
    return {
        "message": "Chat With Your Photos API is running",
        "indexed_images": index.ntotal
    }


@app.get("/search-by-text")
def search_by_text(
    q: str = Query(..., min_length=1),
    top_k: int = Query(5, ge=1, le=50)
):
    if not q.strip():
        raise HTTPException(
            status_code=400,
            detail="Query cannot be empty"
        )

    # Convert the text query into model inputs
    inputs = processor(
        text=[q],
        return_tensors="pt",
        padding=True,
        truncation=True
    )

    # Generate the CLIP text embedding
    with torch.no_grad():
        text_output = model.text_model(**inputs)
        text_features = model.text_projection(
            text_output.pooler_output
        )

    # Normalize the embedding for cosine similarity
    text_features = text_features / text_features.norm(
        dim=-1, keepdim=True
    )

    # Convert to the format FAISS expects
    query_vector = text_features.cpu().numpy().astype("float32")

    # Search the index for the closest image embeddings
    k = min(top_k, index.ntotal)
    scores, indices = index.search(query_vector, k)

    results = []

    for rank, (i, score) in enumerate(
        zip(indices[0], scores[0]), start=1
    ):
        if i < 0:
            continue

        results.append({
            "rank": rank,
            "image_id": image_ids[i],
            "filename": filenames[i],
            "score": round(float(score), 4),
            "image_url": f"/image/{filenames[i]}"
        })

    return {
        "query": q,
        "results": results
    }


@app.post("/search-by-image")
async def search_by_image(
    file: UploadFile = File(...),
    top_k: int = Query(5, ge=1, le=50)
):
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Please upload an image file"
        )

    try:
        img = Image.open(
            io.BytesIO(await file.read())
        ).convert("RGB")
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Could not read that image"
        )

    inputs = processor(images=img, return_tensors="pt")

    with torch.no_grad():
        vision_out = model.vision_model(**inputs)
        feats = model.visual_projection(
            vision_out.pooler_output
        )

    feats = feats / feats.norm(dim=-1, keepdim=True)

    query_vector = feats.cpu().numpy().astype("float32")

    k = min(top_k, index.ntotal)
    scores, indices = index.search(query_vector, k)

    results = []

    for rank, (i, score) in enumerate(
        zip(indices[0], scores[0]), start=1
    ):
        if i < 0:
            continue

        results.append({
            "rank": rank,
            "image_id": image_ids[i],
            "filename": filenames[i],
            "score": round(float(score), 4),
            "image_url": f"/image/{filenames[i]}"
        })

    return {
        "query": file.filename,
        "results": results
    }


@app.get("/image/{filename}")
def get_image(filename: str):
    import os
    from fastapi import HTTPException
    from fastapi.responses import FileResponse

    image_folder = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "images",
        "images"
    )

    safe_filename = os.path.basename(filename)
    image_path = os.path.join(image_folder, safe_filename)

    if not os.path.isfile(image_path):
        raise HTTPException(
            status_code=404,
            detail="Image not found"
        )

    return FileResponse(image_path)

@app.get("/ui")
def frontend():
    return FileResponse("static/index.html")