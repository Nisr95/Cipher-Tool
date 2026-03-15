from flask import Flask, render_template, request, jsonify, send_file
from io import BytesIO
import math
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


def compute_letter_frequencies(text: str):
    counts = [0] * 26
    total = 0
    for ch in text:
        if ch.isalpha():
            idx = ord(ch.upper()) - ord("A")
            counts[idx] += 1
            total += 1
    if total == 0:
        freqs = [0.0] * 26
    else:
        freqs = [c * 100.0 / total for c in counts]
    return counts, freqs, total


def dot_product(a, b):
    return sum(x * y for x, y in zip(a, b))


def magnitude(a):
    return math.sqrt(sum(x * x for x in a))


def rotate_list(lst, shift):
    shift = shift % len(lst)
    return lst[-shift:] + lst[:-shift]


def frequency_analysis(text: str):
    counts, freqs, total = compute_letter_frequencies(text)
    log_entries = []

    log_entries.append(
        f"Computed raw counts for A–Z over {total} letter(s)."
    )

    # Normalize English frequency so it behaves like a vector
    english = ENGLISH_FREQ
    eng_mag = magnitude(english)

    correlations = []
    best_shift = None
    best_corr = -1.0

    for shift in range(1, 26):  # 1 → 25 as requested
        rotated = rotate_list(freqs, shift)
        dp = dot_product(rotated, english)
        vec_mag = magnitude(rotated)
        if eng_mag == 0 or vec_mag == 0:
            corr = 0.0
        else:
            corr = dp / (eng_mag * vec_mag)
        correlations.append(
            {
                "shift": shift,
                "correlation": corr,
            }
        )
        log_entries.append(
            f"Shift {shift:2d}: correlation = {corr:.6f}"
        )
        if corr > best_corr:
            best_corr = corr
            best_shift = shift

    detected_key = best_shift if best_shift is not None else 0
    auto_decrypted = caesar_decrypt(text, detected_key) if detected_key else text

    letters = [chr(ord("A") + i) for i in range(26)]
    freq_table = [
        {
            "letter": letters[i],
            "count": counts[i],
            "frequency": freqs[i],
        }
        for i in range(26)
    ]

    log_entries.append(f"Detected key (best shift) = {detected_key}")

    return {
        "detected_key": detected_key,
        "auto_decrypted": auto_decrypted,
        "correlations": correlations,
        "frequency_table": freq_table,
        "log": log_entries,
    }


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

    if mode not in {"Encryption", "Decryption", "Frequency Analysis"}:
        return jsonify(
            {
                "success": False,
                "error": "Unsupported mode.",
                "log": ["Error: Unsupported process mode selected."],
            }
        )

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

        # Frequency Analysis
        analysis = frequency_analysis(text)
        log.extend(analysis["log"])
        result_text_lines = [
            f"Detected key (best shift): {analysis['detected_key']}",
            "",
            "Auto-decrypted text:",
            analysis["auto_decrypted"],
        ]
        result_text = "\n".join(result_text_lines)
        return jsonify(
            {
                "success": True,
                "result": result_text,
                "detected_key": analysis["detected_key"],
                "correlations": analysis["correlations"],
                "frequency_table": analysis["frequency_table"],
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

