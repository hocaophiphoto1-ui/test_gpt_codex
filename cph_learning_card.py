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
# GET CURRENT CARD
# =========================================================
def get_learning_note():
    card = invoke("guiCurrentCard")
    if not card:
        return None

    answer = clean_html(card.get("answer", ""))
    # Word field from guiCurrentCard is usually nested under:
    # card["fields"]["Word"]["value"]
    # Keep backward-compatibility with older shapes.
    fields = card.get("fields", {}) or {}
    word_field_obj = fields.get("Word", {}) if isinstance(fields, dict) else {}
    word_value = ""
    if isinstance(word_field_obj, dict):
        word_value = word_field_obj.get("value", "")
    if not word_value:
        word_value = card.get("Word", "")
    Word = word_value

    #question = clean_html(card.get("question", ""))
    question_field_obj = fields.get("IPA", {}) if isinstance(fields, dict) else {}
    question_value = ""
    if isinstance(word_field_obj, dict):
        question_value = question_field_obj.get("value", "")
    if not question_value:
        question_value = card.get("IPA", "")
    question = question_value

    # DEBUG
    #with open("123.test", "w", encoding="utf-8") as f: f.write(str(card))
    #printf ("word_field_obj: ", word_field_obj)
    #printf ("word_value: ", word_value)
    #printf ("Word: ", Word)

    data = {
        "card_id": card.get("cardId"),
        "note_id": card.get("noteId"),
        "question": question,
        "answer": answer,
        "word": Word
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

    print("WORD:")
    print(card["question"])

    print("MEANING:")
    print(card["answer"])


def _normalize_word_text(text):
    if text is None:
        return ""

    # strip accents/diacritics for tolerant matching
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()

    # keep letters only, collapse separators
    tokens = re.findall(r"[a-z]+", text)
    return " ".join(tokens)


def _extract_target_word(card_question, card_answer="", card_word=""):
    # Best source: exact "Word" field from note
    normalized_word_field = _normalize_word_text(card_word)
    if normalized_word_field:
        return normalized_word_field

    # Fallback: explicit answer line like "elementary la tu dung"
    if card_answer:
        first_line = _normalize_word_text(card_answer.splitlines()[0])
        m = re.match(r"^([a-z][a-z\s\-']*)\s+la\s+tu\s+dung$", first_line)
        if m:
            return _normalize_word_text(m.group(1))

    # Last fallback: best effort from question (often IPA/noisy)
    if card_question:
        first_line = _normalize_word_text(card_question.splitlines()[0])
        if first_line:
            return first_line

    return ""


def is_easy_by_word_input(user_input, card_question, card_answer="", card_word=""):
    user_text = _normalize_word_text(user_input)
    target_word = _extract_target_word(card_question, card_answer, card_word)
    return user_text != "" and user_text == target_word


# =========================================================
# MAIN LOOP
# =========================================================
def reviewer_loop():
    print()
    print("ANKI REVIEWER STARTED")
    print("    Open Anki reviewer first")

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
                print("1 = AGAIN; 2 = HARD; 3 = GOOD; 4 = EASY; q = QUIT")

            cmd = input("Select: ").strip()

            # DEBUG
            #with open("123.test", "w", encoding="utf-8") as f: f.write(str(card))
            if cmd == "1":
                answer_again()
            elif cmd == "2":
                answer_hard()
            elif cmd == "3":
                answer_good()
            elif cmd == "4":
                answer_easy()
            elif cmd.lower() == "q":
                break
            elif is_easy_by_word_input(cmd, card["question"], card["answer"], card.get("word", "")):
                answer_easy()
            else:
                print("NOT_YET_CORRECT")
                printf ("    --> Word: ", card.get("word", ""))
                continue

            time.sleep(0.3)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print("ERROR:", e)
            time.sleep(1)


# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    reviewer_loop()
