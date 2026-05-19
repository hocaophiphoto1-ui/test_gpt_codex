# -*- coding: utf-8 -*-
# ANKI REVIEWER CONTROLLER
# Works with filtered decks
# Review cards using Python

import requests
import time
import html
import re

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

    question = clean_html(card.get("question", ""))
    answer = clean_html(card.get("answer", ""))

    data = {
        "card_id": card.get("cardId"),
        "note_id": card.get("noteId"),
        "question": question,
        "answer": answer
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
    print("-" * 60)

    #print("CARD ID :", card["card_id"])
    #print("NOTE ID :", card["note_id"])

    #print("-" * 60)

    print("WORD:")
    print(card["question"])

    #print("-" * 60)

    print("MEANING:")
    print(card["answer"])

    #print("=" * 60)
    #print()


def is_easy_by_word_input(user_input, card_question):
    user_text = user_input.strip().lower()
    question_text = card_question.splitlines()[0].strip().lower() if card_question else ""
    return user_text != "" and user_text == question_text


# =========================================================
# MAIN LOOP
# =========================================================
def reviewer_loop():
    print()
    print("ANKI REVIEWER STARTED")
    print("Open Anki reviewer first")

    last_card_id = None

    while True:
        try:
            card = get_learning_note()
            if card is None:
                print("No reviewer card opened...")
                time.sleep(2)
                continue

            # avoid duplicate print
            if card["card_id"] != last_card_id:
                last_card_id = card["card_id"]
                print_card(card)
                show_answer()
                print("1 = AGAIN; 2 = HARD; 3 = GOOD; 4 = EASY; q = QUIT")

            cmd = input("Select: ").strip()
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
            elif is_easy_by_word_input(cmd, card["question"]):
                answer_easy()
            else:
                print("NOT YET CORRECT")
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
