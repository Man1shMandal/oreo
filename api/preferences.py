"""Small request settings and inexpensive context selection."""

import re
from api.messages import unpack

DEFAULTS = {"instructions": "", "reply_style": "brief", "context": "efficient", "temperature": 0.7, "reuse_files": True}
HISTORY = {"efficient": 12000, "balanced": 24000, "extended": 64000}
STYLE = {"brief": "Use short, direct answers. Expand when the task needs detail.", "balanced": "Give enough detail to explain the answer clearly.", "thorough": "Give a thorough answer when useful. Include relevant reasoning and examples."}


def validate(value):
    if value is None:
        return dict(DEFAULTS)
    if not isinstance(value, dict):
        raise ValueError("Send valid chat settings.")
    out = {**DEFAULTS, **{k: v for k, v in value.items() if k in DEFAULTS}}
    if not isinstance(out['instructions'], str) or len(out['instructions']) > 20000:
        raise ValueError("Keep custom instructions under 20,000 characters.")
    if not isinstance(out['context'], str) or not isinstance(out['reply_style'], str) or out['context'] not in HISTORY or out['reply_style'] not in STYLE:
        raise ValueError("Choose a valid history depth and reply style.")
    if isinstance(out['temperature'], bool) or not isinstance(out['temperature'], (int, float)) or not 0 <= out['temperature'] <= 1:
        raise ValueError("Choose creativity between 0 and 1.")
    if not isinstance(out['reuse_files'], bool):
        raise ValueError("Choose a valid attachment setting.")
    return out


def history_content(content, question, reuse, attachment_chars):
    value = unpack(content)
    text = value['text']
    documents = value.get('documents', [])
    images = value.get('images', [])
    if not reuse:
        names = [f.get('name', 'file') for f in value.get('files', [])]
        return text + ('\n[Earlier attachments: ' + ', '.join(names) + ']' if names else '')
    words = set(re.findall(r'\w{3,}', question.lower()))
    attachment_chars = max(1, attachment_chars // max(1, len(documents)))
    for document in documents:
        if len(document) <= attachment_chars:
            excerpt = document
        else:
            paragraphs = [piece[i:i + 800] for piece in re.split(r'(?<=[.!?])\s+|\n', document) for i in range(0, len(piece), 800)]
            ranked = sorted(range(len(paragraphs)), key=lambda i: -sum(w in paragraphs[i].lower() for w in words))
            chosen, size = set(), 0
            for i in ranked:
                if size + len(paragraphs[i]) <= attachment_chars:
                    chosen.add(i); size += len(paragraphs[i])
            excerpt = '\n'.join(paragraphs[i] for i in sorted(chosen)) or document[:attachment_chars]
            excerpt += '\n[Selected excerpts from the earlier attachment.]'
        text += '\n\n' + excerpt
    if images:
        return [{"type": "text", "text": text or "Please refer to the earlier attachment."}, *images]
    return text
