"""Compact key matcher adapted from OpenAssess's parseAnswerKey.

Upstream: collinsherriff/openassess, commit 35b5346895e390481aff47a1c37ff76a1be05b2b
File: js/lib/textparse.js, parseAnswerKey. Copyright (c) 2026 Collin Sherriff.
MIT license, retained in third_party/openassess-LICENSE.txt.
GMF changes: retain conflicting duplicate rows, reject embedded decimal metadata,
return pairs rather than overwriting a map. Detailed alignment tables use a separate parser.
"""
import re


def compact_answer_pairs(text):
    matches=re.findall(r"(?<![\w.])(\d{1,3})\s*[.):\-]?\s*([A-Ha-h])\b",text)
    return [(str(int(n)),label.upper()) for n,label in matches] if len(matches)>=2 else []
