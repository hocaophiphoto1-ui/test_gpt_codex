# -*- coding: utf-8 -*-
# ANKI REVIEWER CONTROLLER
# Works with filtered decks
# Review cards using Python

import requests
import time
import html
import re
import unicodedata


def printf(*args):
    print("".join(map(str, args)))


ANKI_URL = "http://localhost:8765"


# =========================================================
# BASIC API
# =========================================================

def invoke(action, **params):
    payload = {
        "action": action,
        "version": 6,
        "params": params
    }
    response = requests.post(ANKI_URL, json=payload).json()

    if response["error"]:
        raise Exception(response["error"])

    return response["result"]


# =========================================================
# HTML CLEANER
# =========================================================
def clean_html(raw_html):
    if raw_html is None:
        return ""

    text = raw_html

    # remove style/script blocks
    text = re.sub(r"<style.*?>.*?</style>", "", text, flags=re.S)
    text = re.sub(r"<script.*?>.*?</script>", "", text, flags=re.S)

    # remove all html tags
    text = re.sub(r"<.*?>", "", text)

    # remove anki audio tags
    text = re.sub(r"\[anki:play:.*?\]", "", text)

    # decode html
    text = html.unescape(text)

    # normalize empty lines
    lines = []

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # remove useless deck title
        if line == "4000 Essential English Words":
            continue
        # remove IPA line
        if re.match(r"^[a-zɪəɛɔʊæθðŋʃʒˈˌ\s\*\-/\.]+$", line.lower()):
            continue
        lines.append(line)
    return "\n\n".join(lines)


# =========================================================
# PARSE MEANING & EXAMPLE FROM ANSWER
# =========================================================
def parse_meaning_example(answer_text):
    """
    Parse answer text to extract Meaning and Example.
    Expected format:
        Meaning: <meaning text>
        → Example: <example text>
    Returns (meaning_str, example_str) or ("", "") if not found.
    """
    meaning = ""
    example = ""

    for line in answer_text.splitlines():
        line = line.strip()
        # Match "Meaning: ..."
        m = re.match(r"^Meaning[:\s]+(.+)$", line, re.IGNORECASE)
        if m:
            meaning = m.group(1).strip()
            continue
        # Match "→ Example: ..." or "Example: ..."
        m = re.match(r"^[→>*\-]?\s*Example[:\s]+(.+)$", line, re.IGNORECASE)
        if m:
            example = m.group(1).strip()
            continue

    return meaning, example


# =========================================================
# GET CURRENT CARD
# =========================================================
def get_learning_note():
    card = invoke("guiCurrentCard")
    if not card:
        return None

    answer = clean_html(card.get("answer", ""))
    fields = card.get("fields", {}) or {}

    word_field_obj = fields.get("Word", {}) if isinstance(fields, dict) else {}
    word_value = ""
    if isinstance(word_field_obj, dict):
        word_value = word_field_obj.get("value", "")
    if not word_value:
        word_value = card.get("Word", "")
    Word = word_value

    question_field_obj = fields.get("IPA", {}) if isinstance(fields, dict) else {}
    question_value = ""
    if isinstance(word_field_obj, dict):
        question_value = question_field_obj.get("value", "")
    if not question_value:
        question_value = card.get("IPA", "")
    question = question_value

    meaning, example = parse_meaning_example(answer)

    data = {
        "card_id": card.get("cardId"),
        "note_id": card.get("noteId"),
        "question": question,
        "answer": answer,
        "word": Word,
        "meaning": meaning,
        "example": example,
    }

    return data


# =========================================================
# ANSWER CARD
# =========================================================
def answer_easy():
    invoke("guiAnswerCard", ease=4)

def answer_good():
    invoke("guiAnswerCard", ease=3)

def answer_hard():
    invoke("guiAnswerCard", ease=2)

def answer_again():
    invoke("guiAnswerCard", ease=1)

def show_answer():
    invoke("guiShowAnswer")


# =========================================================
# PRINT CARD
# =========================================================

def print_card(card):
    print()
    print("-" * 8)
    print("IPA    :", card["question"])
    print("ANSWER :", card["answer"])


# =========================================================
# NORMALIZE FOR COMPARISON
# (case-insensitive, strip punctuation, collapse whitespace)
# =========================================================
def normalize_input(text):
    if text is None:
        return ""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    # remove punctuation: keep only letters, digits, spaces
    text = re.sub(r"[^a-z0-9\s]", "", text)
    # collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_word_text(text):
    if text is None:
        return ""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()
    tokens = re.findall(r"[a-z]+", text)
    return " ".join(tokens)


def _extract_target_word(card_question, card_answer="", card_word=""):
    normalized_word_field = _normalize_word_text(card_word)
    if normalized_word_field:
        return normalized_word_field

    if card_answer:
        first_line = _normalize_word_text(card_answer.splitlines()[0])
        m = re.match(r"^([a-z][a-z\s\-']*)\s+la\s+tu\s+dung$", first_line)
        if m:
            return _normalize_word_text(m.group(1))

    if card_question:
        first_line = _normalize_word_text(card_question.splitlines()[0])
        if first_line:
            return first_line

    return ""


# =========================================================
# 3-STEP REVIEW LOOP FOR ONE CARD
# Returns: "answered" | "quit" | "next"
# =========================================================
def review_card_steps(card):
    """
    Step1 – type the WORD
    Step2 – type the MEANING sentence
    Step3 – type the EXAMPLE sentence
    'r' at any step resets to step1.
    1/2/3/4 at any step go directly to answer_* and move on.
    q quits the program.
    """

    word_target    = normalize_input(card.get("word", ""))
    meaning_target = normalize_input(card.get("meaning", ""))
    example_target = normalize_input(card.get("example", ""))

    step = 1

    step_labels = {
        1: ("WORD",    word_target,    card.get("word", "?")),
        2: ("MEANING", meaning_target, card.get("meaning", "?")),
        3: ("EXAMPLE", example_target, card.get("example", "?")),
    }

    while True:
        label, target, display = step_labels[step]
        prompt = f"Step{step} [{label}]: "

        try:
            cmd = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            return "quit"

        # --- global commands ---
        if cmd.lower() == "q":
            return "quit"
        if cmd.lower() == "r":
            print("  ↩ Reset về Step1")
            step = 1
            continue
        if cmd == "1":
            answer_again();  return "answered"
        if cmd == "2":
            answer_hard();   return "answered"
        if cmd == "3":
            answer_good();   return "answered"
        if cmd == "4":
            answer_easy();   return "answered"

        # --- check answer ---
        user = normalize_input(cmd)

        if user == "" :
            continue

        if user == target:
            print(f"  ✓ Correct!")
            if step < 3:
                step += 1
            else:
                # Completed all 3 steps → easy
                answer_easy()
                return "answered"
        else:
            print(f"  ✗ False!")
            print(f"       Bạn nhập : {cmd}")
            print(f"       Đúng là  : {display}")


# =========================================================
# MAIN LOOP
# =========================================================
def reviewer_loop():
    print()
    print("ANKI REVIEWER STARTED")
    print("    Open Anki reviewer first")
    print("    r = reset về step1 | q = quit | 1-4 = rate trực tiếp")

    last_card_id = None

    while True:
        try:
            card = get_learning_note()
            if card is None:
                print("    No reviewer card opened...")
                time.sleep(2)
                continue

            # avoid duplicate print
            if card["card_id"] != last_card_id:
                last_card_id = card["card_id"]
                print_card(card)
                show_answer()
                print()
                print(f"Word: ???     Meaning: ???    Example: ???")

            result = review_card_steps(card)

            if result == "quit":
                break

            time.sleep(0.3)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print("ERROR:", e)
            time.sleep(1)

    print("Bye!")


# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    reviewer_loop()
