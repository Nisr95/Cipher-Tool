from flask import Flask, render_template, request, jsonify, send_file
from io import BytesIO
import datetime


app = Flask(__name__)


ENGLISH_FREQ = [
    8.167,  # A
    1.492,  # B
    2.782,  # C
    4.253,  # D
    12.702, # E
    2.228,  # F
    2.015,  # G
    6.094,  # H
    6.966,  # I
    0.153,  # J
    0.772,  # K
    4.025,  # L
    2.406,  # M
    6.749,  # N
    7.507,  # O
    1.929,  # P
    0.095,  # Q
    5.987,  # R
    6.327,  # S
    9.056,  # T
    2.758,  # U
    0.978,  # V
    2.360,  # W
    0.150,  # X
    1.974,  # Y
    0.074,  # Z
]


def caesar_shift_char(ch: str, key: int, encrypt: bool = True) -> str:
    if not ch.isalpha():
        return ch
    base = ord("A") if ch.isupper() else ord("a")
    idx = ord(ch) - base
    if encrypt:
        new_idx = (idx + key) % 26
    else:
        new_idx = (idx - key) % 26
    return chr(base + new_idx)


def caesar_encrypt(text: str, key: int):
    result = []
    for ch in text:
        result.append(caesar_shift_char(ch, key, encrypt=True))
    return "".join(result)


def caesar_decrypt(text: str, key: int):
    result = []
    for ch in text:
        result.append(caesar_shift_char(ch, key, encrypt=False))
    return "".join(result)


def _letters_only_lower(text: str) -> str:
    """Extract only alphabetic characters and normalize to lowercase."""
    return "".join(ch.lower() for ch in text if ch.isalpha())


def _letter_counts_and_proportions(text: str):
    """Count A–Z in normalized letter-only text; return counts and proportions."""
    letters = _letters_only_lower(text)
    counts = [0] * 26
    for ch in letters:
        counts[ord(ch) - ord("a")] += 1
    total = sum(counts)
    if total == 0:
        proportions = [0.0] * 26
    else:
        proportions = [c / total for c in counts]
    return counts, proportions, total


def dot_product(a, b):
    return sum(x * y for x, y in zip(a, b))


def frequency_analysis(text: str):
    """
    Compute letter frequency distribution only. No cracking.
    Returns frequency_table (letter, count, frequency as proportion) and log.
    """
    counts, proportions, total = _letter_counts_and_proportions(text)
    log_entries = [f"Computed raw counts for A–Z over {total} letter(s)."]
    letters = [chr(ord("A") + i) for i in range(26)]
    freq_table = [
        {
            "letter": letters[i],
            "count": counts[i],
            "frequency": proportions[i],
        }
        for i in range(26)
    ]
    return {
        "frequency_table": freq_table,
        "log": log_entries,
    }


# English letter frequencies as percentages (A–Z); convert to proportions for scoring
ENGLISH_FREQ_PROPORTIONS = [x / 100.0 for x in ENGLISH_FREQ]


def score_english(text: str) -> float:
    """
    Score text using standard English letter frequency distribution.
    Returns dot product of (text letter proportions) with ENGLISH_FREQ_PROPORTIONS.
    Higher score = more English-like.
    """
    _, proportions, total = _letter_counts_and_proportions(text)
    if total == 0:
        return 0.0
    return dot_product(proportions, ENGLISH_FREQ_PROPORTIONS)


def detect_caesar_key(text: str):
    """
    Try all Caesar shifts 0–25; for each shift decrypt and score with score_english().
    Returns (best_key, best_decrypted_text, shift_scores) where shift_scores
    is a list of {"shift": int, "score": float} for the log panel.
    """
    shift_scores = []
    best_key = 0
    best_score = -1.0
    best_text = text

    for shift in range(26):
        decrypted = caesar_decrypt(text, shift)
        score = score_english(decrypted)
        shift_scores.append({"shift": shift, "score": score})
        if score > best_score:
            best_score = score
            best_key = shift
            best_text = decrypted

    return best_key, best_text, shift_scores


def crack_caesar_cipher(ciphertext: str):
    """
    Crack Caesar cipher by frequency analysis.
    - Normalize ciphertext to letters only for distribution.
    - Compare cipher frequency distribution to shifted English.
    - Best shift = argmax of dot_product(cipher_freq, shifted_english).
    Returns (best_shift, cracked_text).
    """
    if not ciphertext or not _letters_only_lower(ciphertext):
        return 0, ciphertext
    _, cipher_freq, _ = _letter_counts_and_proportions(ciphertext)
    english = ENGLISH_FREQ_PROPORTIONS
    best_shift = 0
    best_score = -1.0
    for shift in range(26):
        shifted = english[-shift:] + english[:-shift]
        score = dot_product(cipher_freq, shifted)
        if score > best_score:
            best_score = score
            best_shift = shift
    cracked_text = caesar_decrypt(ciphertext, best_shift)
    return best_shift, cracked_text


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process():
    data = request.get_json(silent=True) or {}
    mode = data.get("mode")
    algorithm = data.get("algorithm")
    key = data.get("key")
    text = data.get("text", "") or ""

    log = []

    if algorithm != "Caesar Cipher":
        return jsonify(
            {
                "success": False,
                "error": "Unsupported algorithm.",
                "log": ["Error: Unsupported algorithm selected."],
            }
        )

    if mode not in {
        "Encryption",
        "Decryption",
        "Frequency Analysis",
        "Crack",
        "Detect Key Automatically",
    }:
        return jsonify(
            {
                "success": False,
                "error": "Unsupported mode.",
                "log": ["Error: Unsupported process mode selected."],
            }
        )

    auto_detect_key = data.get("auto_detect_key") is True

    if not isinstance(text, str) or text == "":
        return jsonify(
            {
                "success": False,
                "error": "Input text is empty.",
                "log": ["Error: Input text is empty."],
            }
        )

    log.append(f"Mode: {mode}")
    log.append(f"Algorithm: {algorithm}")

    try:
        if mode in {"Encryption", "Decryption"}:
            # Decryption with auto_detect_key: run detection instead of using key
            if mode == "Decryption" and auto_detect_key:
                best_key, best_text, shift_scores = detect_caesar_key(text)
                log.append("Auto-detect key: trying all shifts 0–25.")
                for s in shift_scores:
                    log.append(f"  Shift {s['shift']:2d}: score = {s['score']:.6f}")
                log.append(f"Detected key: {best_key}")
                return jsonify(
                    {
                        "success": True,
                        "detected_key": best_key,
                        "result": best_text,
                        "shift_scores": shift_scores,
                        "log": log,
                    }
                )

            if key is None or key == "":
                return jsonify(
                    {
                        "success": False,
                        "error": "Security key is required.",
                        "log": log
                        + ["Error: Security key is required for this mode."],
                    }
                )
            try:
                key_int = int(key)
            except (TypeError, ValueError):
                return jsonify(
                    {
                        "success": False,
                        "error": "Security key must be an integer.",
                        "log": log
                        + ["Error: Security key must be a valid integer."],
                    }
                )

            key_int = key_int % 26
            log.append(f"Security key used: {key_int}")

            if mode == "Encryption":
                result = caesar_encrypt(text, key_int)
                log.append("Performed Caesar Cipher encryption.")
            else:
                result = caesar_decrypt(text, key_int)
                log.append("Performed Caesar Cipher decryption.")

            return jsonify(
                {
                    "success": True,
                    "result": result,
                    "log": log,
                }
            )

        if mode == "Detect Key Automatically":
            best_key, best_text, shift_scores = detect_caesar_key(text)
            log.append("Detect Key Automatically: trying all shifts 0–25.")
            for s in shift_scores:
                log.append(f"  Shift {s['shift']:2d}: score = {s['score']:.6f}")
            log.append(f"Detected key: {best_key}")
            return jsonify(
                {
                    "success": True,
                    "detected_key": best_key,
                    "result": best_text,
                    "shift_scores": shift_scores,
                    "log": log,
                }
            )

        if mode == "Frequency Analysis":
            analysis = frequency_analysis(text)
            log.extend(analysis["log"])
            table = analysis["frequency_table"]
            result_lines = ["Letter | Count | Frequency (proportion)"]
            for row in table:
                result_lines.append(
                    f"  {row['letter']}    | {row['count']:5d} | {row['frequency']:.6f}"
                )
            result_text = "\n".join(result_lines)
            return jsonify(
                {
                    "success": True,
                    "result": result_text,
                    "frequency_table": analysis["frequency_table"],
                    "log": log,
                }
            )

        # Crack
        if mode == "Crack":
            best_shift, cracked_text = crack_caesar_cipher(text)
            log.append("Ran crack_caesar_cipher (frequency-based).")
            log.append(f"Detected key: {best_shift}")
            return jsonify(
                {
                    "success": True,
                    "detected_key": best_shift,
                    "result": cracked_text,
                    "log": log,
                }
            )

    except Exception as exc:  # pragma: no cover - safeguard
        log.append(f"Unexpected error: {exc}")
        return jsonify(
            {
                "success": False,
                "error": "Unexpected server error.",
                "log": log,
            }
        )


@app.route("/download", methods=["POST"])
def download():
    data = request.get_json(silent=True) or {}
    content = data.get("content", "")
    if not isinstance(content, str):
        content = str(content)

    filename = data.get("filename") or f"cipher_output_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    mem = BytesIO()
    mem.write(content.encode("utf-8"))
    mem.seek(0)

    return send_file(
        mem,
        as_attachment=True,
        download_name=filename,
        mimetype="text/plain; charset=utf-8",
    )


if __name__ == "__main__":
    app.run(debug=True)

