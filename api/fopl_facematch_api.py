"""FOPL Face Match API — Gemini Vision celebrity look-alike."""
import json
import re
import unicodedata
import requests as http
from urllib.parse import quote
from flask import Blueprint, request, current_app
from flask_restful import Api, Resource

from api.fopl_ai_service import call_ai_vision

fopl_facematch_api = Blueprint('fopl_facematch_api', __name__, url_prefix='/api/fopl/face-match')
api = Api(fopl_facematch_api)

PROMPT = """You are analyzing a photo for a fun library website feature.

STEP 1 — If there is NO clearly visible human face, respond with exactly: {"no_face": true}

STEP 2 — Look carefully at the face. Note:
- Apparent gender (male/female)
- Approximate age range
- Skin tone and ethnicity
- Distinctive features: face shape, eyes, nose, jaw, forehead, facial hair

STEP 3 — Choose ONE famous author or writer whose face genuinely resembles this person based on actual facial features. The match MUST share the same gender and similar ethnicity. Draw from any era or genre — fiction, non-fiction, science, poetry, journalism.

STEP 4 — Respond with ONLY valid JSON, no markdown:
{
  "name": "Author Full Name",
  "similarity": 78,
  "reason": "One specific sentence naming 2-3 concrete facial features unique to this match (e.g. jaw shape, eye spacing, brow ridge, cheekbone height) — never use generic phrases.",
  "known_for": "One sentence about their most famous works.",
  "book": "Their single most famous book title",
  "book_author": "Author Full Name"
}

Similarity must be between 65 and 94. Do not repeat the same author for different people."""

# Fallback list — famous authors, used only when AI is unavailable.
FALLBACK_CELEBS = [
    {
        "name": "Stephen King",
        "wiki_slug": "Stephen_King",
        "similarity_range": (69, 86),
        "reason": "Rectangular face, strong jaw, and deep-set eyes behind distinctive glasses.",
        "known_for": "Prolific master of horror and suspense, author of The Shining and It.",
        "book": "The Shining",
        "book_author": "Stephen King",
    },
    {
        "name": "J.K. Rowling",
        "wiki_slug": "J._K._Rowling",
        "similarity_range": (70, 88),
        "reason": "Oval face, warm expressive eyes, and a gentle symmetrical smile.",
        "known_for": "Author of the Harry Potter series, one of the best-selling book series in history.",
        "book": "Harry Potter and the Sorcerer's Stone",
        "book_author": "J.K. Rowling",
    },
    {
        "name": "Malcolm Gladwell",
        "wiki_slug": "Malcolm_Gladwell",
        "similarity_range": (71, 89),
        "reason": "Round face, warm wide-set eyes, and a broad forehead.",
        "known_for": "Author of Outliers, The Tipping Point, and Blink.",
        "book": "Outliers",
        "book_author": "Malcolm Gladwell",
    },
    {
        "name": "Toni Morrison",
        "wiki_slug": "Toni_Morrison",
        "similarity_range": (72, 90),
        "reason": "High cheekbones, deep expressive eyes, and a strong dignified face.",
        "known_for": "Nobel Prize-winning author of Beloved and Song of Solomon.",
        "book": "Beloved",
        "book_author": "Toni Morrison",
    },
    {
        "name": "Neil Gaiman",
        "wiki_slug": "Neil_Gaiman",
        "similarity_range": (68, 86),
        "reason": "Angular face, dark intense eyes, and a sharp prominent nose.",
        "known_for": "Author of American Gods, Good Omens, and the Sandman comic series.",
        "book": "American Gods",
        "book_author": "Neil Gaiman",
    },
    {
        "name": "Chimamanda Ngozi Adichie",
        "wiki_slug": "Chimamanda_Ngozi_Adichie",
        "similarity_range": (73, 91),
        "reason": "Defined cheekbones, almond-shaped eyes, and a graceful oval face.",
        "known_for": "Author of Purple Hibiscus, Half of a Yellow Sun, and Americanah.",
        "book": "Americanah",
        "book_author": "Chimamanda Ngozi Adichie",
    },
    {
        "name": "Ta-Nehisi Coates",
        "wiki_slug": "Ta-Nehisi_Coates",
        "similarity_range": (70, 88),
        "reason": "Broad forehead, strong cheekbones, and deep thoughtful eyes.",
        "known_for": "Author of Between the World and Me and The Beautiful Struggle.",
        "book": "Between the World and Me",
        "book_author": "Ta-Nehisi Coates",
    },
    {
        "name": "Haruki Murakami",
        "wiki_slug": "Haruki_Murakami",
        "similarity_range": (69, 87),
        "reason": "Soft oval face, calm deep-set eyes, and a gentle expression.",
        "known_for": "Japanese author of Norwegian Wood and Kafka on the Shore.",
        "book": "Norwegian Wood",
        "book_author": "Haruki Murakami",
    },
    {
        "name": "Roxane Gay",
        "wiki_slug": "Roxane_Gay",
        "similarity_range": (71, 89),
        "reason": "Full round face, warm wide-set eyes, and strong symmetrical features.",
        "known_for": "Author of Bad Feminist and Hunger, cultural critic and essayist.",
        "book": "Bad Feminist",
        "book_author": "Roxane Gay",
    },
    {
        "name": "David Sedaris",
        "wiki_slug": "David_Sedaris",
        "similarity_range": (67, 84),
        "reason": "Narrow angular face, sharp nose, and expressive close-set eyes.",
        "known_for": "Beloved humorist and essayist, author of Me Talk Pretty One Day.",
        "book": "Me Talk Pretty One Day",
        "book_author": "David Sedaris",
    },
    {
        "name": "James Baldwin",
        "wiki_slug": "James_Baldwin",
        "similarity_range": (71, 89),
        "reason": "Distinctive wide-set eyes, high forehead, and an expressive angular face.",
        "known_for": "Author of Go Tell It on the Mountain and The Fire Next Time.",
        "book": "The Fire Next Time",
        "book_author": "James Baldwin",
    },
    {
        "name": "Zadie Smith",
        "wiki_slug": "Zadie_Smith",
        "similarity_range": (72, 90),
        "reason": "High cheekbones, warm almond eyes, and a graceful symmetrical face.",
        "known_for": "Author of White Teeth and On Beauty.",
        "book": "White Teeth",
        "book_author": "Zadie Smith",
    },
]


class _FaceMatch(Resource):
    def post(self):
        body = request.get_json() or {}
        image_b64 = body.get('image')
        mime_type  = body.get('mime', 'image/jpeg')

        if not image_b64:
            return {'message': 'image field required (base64)'}, 400

        # Try Gemini Vision first
        ai_result = None
        _last_ai_error = None
        try:
            raw = call_ai_vision(PROMPT, image_b64, mime_type=mime_type, timeout=25)
            ai_result = _extract_best_json(raw)
        except Exception as e:
            _last_ai_error = str(e)
            current_app.logger.warning(f'Face match AI unavailable: {e}')

        # If AI returned no_face, respect it
        if ai_result and ai_result.get('no_face'):
            return {'no_face': True}

        # If AI gave a valid result, use it
        if ai_result and ai_result.get('name'):
            name = ai_result['name']
            ai_result['wiki_image'] = _fetch_wiki_image(name)
            return ai_result

        # AI unavailable — tell the user rather than give a random wrong answer
        return {'message': _last_ai_error or 'Face analysis unavailable right now — please try again later.'}, 503


def _extract_best_json(raw):
    """Extract the most useful JSON object from an AI response string.
    Prefers objects with a 'name' key over bare {'no_face': true}."""
    clean = re.sub(r'```[a-z]*\n?', '', raw).strip()

    # Find all JSON objects in the text
    candidates = []
    for m in re.finditer(r'\{[^{}]*\}', clean, re.DOTALL):
        try:
            obj = json.loads(m.group())
            candidates.append(obj)
        except Exception:
            pass

    if not candidates:
        # Try the whole string as one object
        try:
            return json.loads(clean)
        except Exception:
            return None

    # Prefer the object that has a 'name' field (actual match result)
    for obj in candidates:
        if obj.get('name'):
            return obj

    # Fall back to first candidate (might be no_face)
    return candidates[0]


def _fetch_wiki_image(name):
    """Try Wikipedia REST summary for a celebrity name, return thumbnail URL or None."""
    if not name:
        return None
    candidates = [name]
    ascii_name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    if ascii_name != name:
        candidates.append(ascii_name)

    headers = {'User-Agent': 'FOPL-FaceMatch/1.0'}
    for n in candidates:
        slug = quote(n.replace(' ', '_'), safe='_()')
        try:
            r = http.get(
                f'https://en.wikipedia.org/api/rest_v1/page/summary/{slug}',
                timeout=5, headers=headers
            )
            if r.status_code == 200:
                data = r.json()
                img = (data.get('thumbnail') or {}).get('source') or \
                      (data.get('originalimage') or {}).get('source')
                if img:
                    return img
        except Exception:
            pass
    return None


api.add_resource(_FaceMatch, '')
