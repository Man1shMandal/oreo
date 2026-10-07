"""Versioned message content keeps attachments and citations with saved turns."""

import json

PREFIX = "oreo-message-v1:"


def unpack(content):
    if content.startswith(PREFIX):
        try:
            value = json.loads(content[len(PREFIX):])
            if isinstance(value, dict) and isinstance(value.get("text"), str):
                return value
        except (ValueError, TypeError):
            pass
    return {"text": content}


def pack(text, **metadata):
    if not any(metadata.values()) and not text.startswith(PREFIX):
        return text
    return PREFIX + json.dumps({"text": text, **metadata}, separators=(",", ":"))


def prompt_content(content):
    value = unpack(content)
    text = value["text"]
    documents = value.get("documents", [])
    if documents:
        text += "\n\n" + "\n\n".join(documents)
    if value.get("images"):
        parts = [{"type": "text", "text": text or "Please read the attached image."}]
        parts.extend(value["images"])
        return parts
    return text


def estimate(content):
    if isinstance(content, str):
        return (len(content) + 3) // 4 + 8
    # PDFs can contain multiple scanned pages; estimate from their actual pages.
    return sum(estimate(p["text"]) if p.get("type") == "text" else image_cost(p) for p in content)


def image_cost(part):
    import base64
    import io
    from pypdf import PdfReader
    try:
        pages = len(PdfReader(io.BytesIO(base64.b64decode(part["file_data"]))).pages)
    except Exception:
        pages = 1
    return max(1, pages) * 1800


def file_metadata(uploads):
    """Store small image previews; full model files remain in the same owned turn."""
    import base64
    import io
    from pathlib import Path
    from PIL import Image
    result = []
    for upload in uploads:
        value = {"name": Path(upload.get("name") or "file").name, "type": upload.get("type", "")}
        if value["type"] in ("image/png", "image/jpeg", "image/webp", "image/gif"):
            try:
                image = Image.open(io.BytesIO(base64.b64decode(upload["data"]))).convert("RGB")
                image.thumbnail((320, 240))
                output = io.BytesIO(); image.save(output, "JPEG", quality=70)
                value["preview"] = "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode()
            except Exception:
                pass
        result.append(value)
    return result
