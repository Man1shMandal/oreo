"""Bounded conversation context without an extra summarization model call."""

import re

from api.messages import unpack
from api.preferences import HISTORY, history_content

ATTACHMENTS = {"efficient": 2400, "balanced": 6000, "extended": 16000}


def excerpt(text, limit):
    if len(text) <= limit:
        return text
    marker = '\n[Earlier message shortened.]\n'
    space = max(0, limit - len(marker))
    head = space * 2 // 3
    return text[:head] + marker + text[len(text) - (space - head):]


def select_history(rows, question, preferences, reuse):
    # Rows arrive newest first. Keep whole turns so a long answer cannot erase
    # its question or leave an orphan assistant message at the start.
    turns = []
    for row in reversed(rows):
        if row['role'] == 'user':
            turns.append([])
        if turns and row['role'] in ('user', 'assistant'):
            turns[-1].append(row)
    if not turns:
        return []
    budget = HISTORY[preferences['context']]
    recent_budget = budget * 3 // 4
    chosen, used = {}, 0
    for index in range(len(turns) - 1, -1, -1):
        turn = turns[index]
        texts = [history_content(row['content'], question, False, 0) for row in turn]
        remaining = recent_budget - used
        cost = sum(map(len, texts))
        reserve = recent_budget // 3 * max(0, min(2 - len(chosen), index))
        allowance = remaining - reserve
        if cost > allowance:
            if len(chosen) >= 3:
                break
            # Always retain the three most recent turns, even after long output.
            texts = [excerpt(text, allowance // len(texts)) for text in texts]
        chosen[index] = [{'role': row['role'], 'content': text} for row, text in zip(turn, texts)]
        used += sum(map(len, texts))
        if used >= recent_budget:
            break

    # Earlier user details and relevant turns remain available in a small budget.
    # They stay user/assistant messages, never promoted to system instructions.
    words = set(re.findall(r'\w{3,}', question.lower())) - {'the', 'and', 'what', 'was', 'that', 'this', 'you', 'for', 'with'}
    older = [i for i in range(len(turns)) if i not in chosen]
    def score(i):
        text = ' '.join(unpack(row['content'])['text'] for row in turns[i]).lower()
        return sum(word in text for word in words)
    ranked = sorted(older, key=lambda i: (score(i), i == 0, i), reverse=True)
    memory = budget - used
    for index in ranked:
        if memory < 200:
            break
        turn = turns[index]
        allowance = min(memory, 1200)
        texts = [excerpt(history_content(row['content'], question, False, 0), allowance // len(turn)) for row in turn]
        chosen[index] = [{'role': row['role'], 'content': text} for row, text in zip(turn, texts)]
        memory -= sum(map(len, texts))

    # Locate the most recent attachment independently of the recent text window.
    if reuse:
        for index in range(len(turns) - 1, -1, -1):
            value = unpack(turns[index][0]['content'])
            if value.get('documents') or value.get('images'):
                content = history_content(turns[index][0]['content'], question, True, ATTACHMENTS[preferences['context']])
                # Bound the message's prose separately from the attachment excerpt.
                if isinstance(content, str):
                    content = excerpt(value['text'], 1200) + content[len(value['text']):]
                else:
                    content[0]['text'] = excerpt(value['text'], 1200) + content[0]['text'][len(value['text']):]
                if index not in chosen:
                    chosen[index] = [{'role': 'user', 'content': content}]
                else:
                    chosen[index][0]['content'] = content
                break
    return [row for index in sorted(chosen) for row in chosen[index]]
