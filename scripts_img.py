# -*- coding: utf-8 -*-
# @Author: Cao Phi Ho
# @Date:   2026/04/08, 21:35
# @Last Modified by:   CPH
# @Last Modified time: 2026/05/26, 03:26
# @Last Modified time: 2026/04/08, 21:35 Create file


import os
import re
import asyncio
import aiohttp
import time
import sys
import requests
import glob
import shutil
from urllib.parse import quote
from PIL import Image # Thêm dòng này

import json
import mimetypes
from pathlib import Path

from google import genai
from google.genai import types

import subprocess

from scripts import get_scripts, get_searches


MODEL_NAME      = "gemini-2.5-pro"                          # "gemini-3.1-pro-preview" # "gemini-2.5-flash"
print(os.getenv("GEMINI_API_KEY"))


# ********************************************************************************
# CẤU HÌNH API MỚI - SERPER API
# ĐẢM BẢO BẠN ĐÃ THAY "YOUR_API_KEY" BẰNG KEY CỦA MÌNH HOẶC ĐẶT BIẾN MÔI TRƯỜNG
#SERPER_API_KEY = "a4687440bd9c99122679dc2d8143c04ad5a1dd42"
SERPER_API_KEY = "c32d6d164e061c7a6b5cd7f162e33c23c9eb7163"

BASE_URL = "https://google.serper.dev"
# ********************************************************************************


def check_genai():
    try:
        client = genai.Client()
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents="hello"
        )
        print("SUCCESS")
        print(response.text)
    except Exception as e:
        print("ERROR:")
        print(e)


def get_prompt_more(path="scripts.eze"):
    """Đọc biến prompt_more dạng triple-quote từ file scripts.eze nếu có."""
    if not os.path.exists(path):
        print(f"    WARNING: File {path} was not found. prompt_more will be empty.")
        return ""

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"    ERROR when reading file {path}: {e}")
        return ""

    #match = re.search(r'prompt_more\s*=\s*"""(.*?)"""', content, re.DOTALL)
    match = re.search( r'^[ \t]*prompt_more\s*=\s*"""(.*?)"""', content, re.DOTALL | re.MULTILINE )
    if match:
        return match.group(1)

    print(f"    WARNING: Structure prompt_more = \"\"\"...\"\"\" not found in {path}. prompt_more will be empty.")
    return ""


prompt_more = get_prompt_more()


def printf(*args):
    print("".join(map(str, args)))


def print_help():
    printf("HELP")


def get_title():
    z_list = glob.glob("z_list")
    if not z_list:
        print("    ERROR: File {z_list} was not found in the directory.")
        return ""

    file_path = z_list[0]
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Tìm nội dung nằm giữa TITLE = " và "
            # Sử dụng re.DOTALL để khớp cả xuống dòng
            match = re.search(r'TITLE\s*=\s*"(.*?)"', content, re.DOTALL)
            if match:
                return match.group(1).strip()
            else:
                print(f"    ERROR: Structure TITLE = \"...\" not found in {file_path}")
                return ""
    except Exception as e:
        print(f"    ERROR when reading file {file_path}: {e}")
        return ""


# Nạp nội dung kịch bản
scripts   = get_scripts()
searches  = get_searches()
fin_title = get_title()

printf("fin_title: ", fin_title)



last_call = 0

MAX_GAP = 10        # khoảng tối đa giữa start và end (giây)
FALLBACK_GAP = 15   # khi fuzzy thì nới nhẹ

SECTION_MAP = {
    "HOOK": 1,
    "INFO": 2,
    "MAIN": 3,
    "BYE" : 4
}


#=======================================================================================================================
#=======================================================================================================================
#=======================================================================================================================
#=======================================================================================================================
#=======================================================================================================================
def load_searches_from_file(path="./searches.yt"):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# =========================
# 1. PARSE INPUT (KEYWORDS ONLY + SECTION + INDEX)
# (GIỮ NGUYÊN)
# =========================
def parse_keywords_block(text):
    results = []
    section = None
    idx = 0

    stats = {"HOOK": 0, "INFO": 0, "MAIN": 0, "BYE": 0, "TOTAL": 0}

    for line in text.split("\n"):
        line = line.strip()

        # detect section
        if line in ["HOOK", "INFO", "MAIN", "BYE"]:
            section = line
            idx = 0
            continue

        # detect numbered line
        if re.match(r"^\d+\.", line):
            idx += 1

        # extract keywords
        if "Keywords:" in line:
            part = line.split("Keywords:")[1]
            items = [x.strip() for x in part.split("-") if x.strip()]

            for kw in items:
                results.append({
                    "section": section,
                    "index": idx,
                    "keyword": kw
                })

                if section in stats:
                    stats[section] += 1
                    stats["TOTAL"] += 1

    return results, stats


# =========================
# 2. SEARCH (SỬ DỤNG SERPER API MỚI)
# =========================

# Hàm gửi yêu cầu đến Serper API
def serper_request(endpoint, payload):
    url = f"{BASE_URL}/{endpoint}"
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    try:
        r = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30
        )
        if r.status_code != 200:
            print(f"    [API ERROR] Mã lỗi {r.status_code} từ Serper API: {r.text}")
            return None
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"    [REQUEST ERROR] Lỗi mạng hoặc kết nối Serper API: {e}")
        return None
    except Exception as e:
        print(f"    [GENERAL ERROR] Lỗi không xác định khi gọi Serper API: {e}")
        return None

# Hàm tìm kiếm ảnh dùng Serper API
def image_search_serper(query, limit=10, country="us"):
    payload = {
        "q": query,
        "gl": country
    }
    data = serper_request("images", payload)
    if not data:
        return []
    results = data.get("images", [])
    return results[:limit] # Trả về số lượng ảnh yêu cầu


semaphore = asyncio.Semaphore(3) # Giới hạn 3 yêu cầu đồng thời

async def search_async(query, num=10): # num mặc định là 10, limit cho Serper
    async with semaphore:
        loop = asyncio.get_event_loop()

        # Gọi hàm tìm kiếm ảnh mới dùng Serper API
        result = await loop.run_in_executor(None, image_search_serper, query, num)

        return result


# =========================
# 3. DETECT TYPE
# (GIỮ NGUYÊN)
# =========================
def detect_type(q):
    ql = q.lower()

    if any(x in ql for x in ["birol", "leader", "speech", "person", "man", "woman", "ceo", "director"]):
        return "PERSON"
    if any(x in ql for x in ["agency", "logo", "brand", "company", "organization", "firm"]):
        return "ORG"
    if any(x in ql for x in ["conference", "summit", "meeting", "event", "seminar", "forum"]):
        return "EVENT"
    return "GENERIC"


# =========================
# 4. SCORE (Cập nhật để hoạt động tốt với dữ liệu từ Serper)
# =========================
def score_image(img, qtype):
    score = 0

    # Serper API cung cấp nhiều thông tin hơn trong 'title' và 'snippet'
    title = img.get("title") or ""
    title = str(title).lower()

    snippet = img.get("snippet") or ""
    snippet = str(snippet).lower()

    # === Chấm điểm theo loại (qtype) ===
    # PERSON
    if qtype == "PERSON":
        if "portrait" in title or "portrait" in snippet: score += 5
        if "speech" in title or "speaker" in title: score += 3
        if "leader" in title or "ceo" in title or "director" in title: score += 2
        if "face" in title or "face" in snippet: score += 1 # Ảnh cận mặt

    # ORG
    elif qtype == "ORG":
        if "logo" in title or "logo" in snippet: score += 8 # Logo rất quan trọng
        if "headquarter" in title or "building" in title or "office" in title: score += 2
        if "brand" in title or "brand" in snippet: score += 1

    # EVENT
    elif qtype == "EVENT":
        if "conference" in title or "summit" in title or "meeting" in title or "forum" in title: score += 5
        if "event" in title or "keynote" in title or "presentation" in title: score += 3
        if "attendees" in title or "crowd" in title: score += 1 # Ảnh có đông người tham dự

    # === Lấy kích thước ảnh từ Serper API ===
    # Serper API dùng 'imageWidth' và 'imageHeight'
    w = 0
    h = 0
    try:
        if img.get("imageWidth") is not None:
            w = int(img["imageWidth"])
        if img.get("imageHeight") is not None:
            h = int(img["imageHeight"])
    except (TypeError, ValueError):
        w = 0
        h = 0

    # === Chấm điểm chất lượng dựa trên kích thước thực tế ===
    if w > 0 and h > 0: # Chỉ chấm điểm nếu có kích thước hợp lệ
        # Cộng điểm theo ngưỡng chất lượng
        if w >= 1920 and h >= 1080: # Full HD
            score += 10
        elif w >= 1280 and h >= 720: # HD
            score += 7
        elif w >= 800 and h >= 600:
            score += 4
        elif w >= 600 and h >= 400: # Kích thước tạm chấp nhận được
            score += 2
        else: # Nếu kích thước quá nhỏ (nhưng vẫn hợp lệ), vẫn cho một ít điểm để phân biệt với 0x0
            score += 1


        # Cộng điểm cho tỷ lệ khung hình gần 16:9 (phổ biến cho video/thuyết trình)
        if h > 0: # Tránh chia cho 0
            aspect_ratio = w / h
            if 1.7 <= aspect_ratio <= 1.8: # Khoảng 16:9 (1.777...)
                score += 3
            elif 1.3 <= aspect_ratio <= 1.4: # Khoảng 4:3 (1.333...)
                score += 1
            else: # Nếu không phải tỷ lệ phổ biến, vẫn cộng 0.5 điểm để ưu tiên ảnh có tỷ lệ hợp lý
                score += 0.5

    # Thêm điểm nếu có URL ảnh gốc (Serper thường dùng 'imageUrl')
    if img.get("imageUrl"):
        score += 1

    return score


def pick_best(images, qtype):
    if not images:
        return None, []

    scored = []
    for i, img in enumerate(images):
        s = score_image(img, qtype)

        # Lấy kích thước để in ra báo cáo từ Serper API
        w = 0
        h = 0
        try:
            if img.get("imageWidth") is not None:
                w = int(img["imageWidth"])
            if img.get("imageHeight") is not None:
                h = int(img["imageHeight"])
        except (TypeError, ValueError):
            w = 0
            h = 0

        scored.append((s, i, img, w, h)) # Thêm s, i, img, w, h vào tuple để dùng khi in báo cáo

    scored.sort(reverse=True, key=lambda x: x[0])

    return scored[0], scored # best là item đầu tiên của scored đã sắp xếp


# =========================
# 5. DOWNLOAD (Sử dụng hàm download_image_serper)
# =========================
async def download_image(session, url, path):
    # Hàm download_image_serper là hàm đồng bộ, cần chạy trong thread pool của asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, download_image_serper, url, path)

# =========================================================
# DOWNLOAD IMAGE (Đã cập nhật để trả về đường dẫn file)
# =========================================================
def download_image_serper(url, path):
    try:
        r = requests.get(
            url,
            timeout=30,
            stream=True,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        )

        if r.status_code == 200:
            # Kiểm tra Content-Type sơ bộ (tùy chọn nhưng hữu ích)
            content_type = r.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                print(f"    [DOWNLOAD ERROR] URL {url} is not an image format (Content-Type: {content_type}).")
                return False

            with open(path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            return True # Trả về True nếu tải thành công
        else:
            print(f"    [DOWNLOAD ERROR] HTTP error code {r.status_code} when loading image from {url}")
            return False

    except requests.exceptions.Timeout:
        print(f"   [DOWNLOAD ERROR] Timeout when loading image from {url}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"    [DOWNLOAD ERROR] Network or connection error when downloading images from {url}: {e}")
        return False
    except Exception as e:
        print(f"    [DOWNLOAD ERROR] Unknown error when loading image from {url}: {e}")
        return False


# =========================
# 6. PROCESS 1 ITEM (Cập nhật với kiểm tra chất lượng file sau khi tải)
# =========================
async def process_item(session, item, output_dir, num):
    section = item["section"]
    idx = item["index"]
    keyword = item["keyword"]

    qtype = detect_type(keyword)

    print(f"\nSEARCH: [{section}-{idx}] {keyword}")

    images = await search_async(keyword, num=num)

    if not images:
        print("    [ERROR] no images found")
        await asyncio.sleep(2)
        return

    best_picked, scored_list_with_dimensions = pick_best(images, qtype)

    if not best_picked:
        print("    [ERROR] scoring failed, no best image found.")
        await asyncio.sleep(2)
        return

    # ===== report =====
    print("  RANKING:")
    for s, i, img_data, w, h in scored_list_with_dimensions:
        flag = "⭐" if i == best_picked[1] else ""
        print(f"    #{i+1} score={s:.1f} ({w}x{h}) {flag}")

    # ===== Thử tải ảnh với cơ chế retry/fallback và kiểm tra chất lượng file =====
    max_download_attempts = 5 # Số lần thử tải ảnh khác nhau (bao gồm lần đầu tiên)
    min_file_size_kb = 10     # Kích thước tối thiểu chấp nhận được cho một file ảnh (KB)
                              # Tùy chỉnh nếu bạn thấy ảnh hợp lệ thường lớn hơn hoặc nhỏ hơn

    download_success = False
    saved_filepath = None

    for attempt_idx, (s, i, img_data, w, h) in enumerate(scored_list_with_dimensions):
        if attempt_idx >= max_download_attempts:
            print(f"    [WARNING] Tried {max_download_attempts} top image but failed. Skip this item.")
            break

        current_score = s
        current_img = img_data
        current_w = w
        current_h = h

        url = current_img.get("imageUrl")

        if not url:
            print(f"    [ERROR] Image #{i+1} does not have a valid URL. Try next photo.")
            continue

        # filename
        safe_kw = re.sub(r'[\\/*?:"<>|]', "", keyword)
        sec_id = SECTION_MAP.get(section, 0)
        # Thêm index ảnh và điểm số vào tên file để dễ kiểm tra
        filename = f"img_{sec_id}{section}_{idx:02d}_{safe_kw}_s{int(current_score)}_{i+1}.jpg"
        path = os.path.join(output_dir, filename)

        print(f"        Trying to load image #{i+1} (score={current_score:.1f}, {current_w}x{current_h})...")
        ok = await download_image(session, url, path)

        if ok:
            # === Bắt đầu kiểm tra chất lượng file sau khi tải ===
            file_size_kb = os.path.getsize(path) / 1024

            if file_size_kb < min_file_size_kb:
                print(f"        [CHECK FAILED] Image size ({file_size_kb:.1f}KB) is too small (< {min_file_size_kb}KB). Delete the file and try the next image.")
                os.remove(path)
                await asyncio.sleep(1)
                continue # Thử ảnh tiếp theo

            try:
                with Image.open(path) as img_check:
                    img_check.verify() # Kiểm tra xem đây có phải là file ảnh hợp lệ không
                    print(f"        [CHECK SUCCESS] The downloaded image is valid. File size: {file_size_kb:.1f}KB.")
                    download_success = True
                    saved_filepath = path
                    break # Tải và kiểm tra thành công, thoát vòng lặp
            except Exception as img_err:
                print(f"        [CHECK FAILED] The image file is corrupted or cannot be opened with Pillow: {img_err}. Delete the file and try the next image.")
                os.remove(path) # Xóa file lỗi
                await asyncio.sleep(1)
                continue # Thử ảnh tiếp theo
        else:
            print(f"   [ERROR] Image #{i+1} failed to load. Try next photo.")
            await asyncio.sleep(1) # Chờ 1 giây trước khi thử lại ảnh khác

    if not download_success:
        print(f"    [ERROR] Could not download any good quality images for keyword: {keyword}")

    # 🔥 Thêm thời gian chờ CỨ SAU MỖI ITEM (dù thành công hay thất bại)
    await asyncio.sleep(2)


#=======================================================================================================================
#=======================================================================================================================
#=======================================================================================================================
#=======================================================================================================================
#=======================================================================================================================
# =========================
# TIME UTILS
# (GIỮ NGUYÊN)
# =========================
def srt_time_to_sec(t):
    h, m, s = t.split(":")
    s, ms = s.split(",")
    return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000


def sec_to_srt(sec):
    h = int(sec // 3600)
    sec %= 3600
    m = int(sec // 60)
    sec %= 60
    s = int(sec)
    ms = int((sec - s) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# =========================
# TEXT UTILS
# (GIỮ NGUYÊN)
# =========================
def normalize_text(t):
    t = t.lower()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


# =========================
# PARSE SRT
# (GIỮ NGUYÊN)
# =========================
def parse_srt(path):
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        blocks = f.read().strip().split("\n\n")

    for b in blocks:
        lines = b.split("\n")
        if len(lines) >= 3:
            times = lines[1]
            text = " ".join(lines[2:]).strip()

            start, end = times.split(" --> ")
            entries.append({
                "start": start.strip(),
                "end": end.strip(),
                "text": text
            })
    return entries


# =========================
# EXTRACT SENTENCES
# (GIỮ NGUYÊN)
# =========================
def extract_sentences(searches):
    lines = []

    for line in searches.split("\n"):
        line = line.strip()
        m = re.match(r"^\d+\.\s+(.*)", line)
        if m:
            txt = m.group(1).strip()
            txt = re.sub(r"[?.!]+$", "", txt)
            lines.append(txt)

    return lines


# =========================
# FIND MATCH (ưu tiên câu dài)
# (GIỮ NGUYÊN)
# =========================
def find_sentence_match(sent_l, srt_main):
    words = sent_l.split()

    best_match = None
    best_sub = None
    best_len = 0

    for i in range(len(words)):
        sub = " ".join(words[i:])
        sub_norm = normalize_text(sub)

        # 🔥 bỏ cụm quá ngắn
        if len(sub_norm.split()) < 2:
            continue

        for e in srt_main:
            text_l = normalize_text(e["text"])

            if sub_norm in text_l:
                if len(sub_norm) > best_len:
                    best_len = len(sub_norm)
                    best_match = e
                    best_sub = sub_norm

    return best_match, best_sub


# =========================
# POSITION INTERPOLATION
# (GIỮ NGUYÊN)
# =========================
def estimate_start_by_position(matched_sub, full_text, start_time, end_time):
    full_norm = normalize_text(full_text)
    sub_norm = normalize_text(matched_sub)

    start_idx = full_norm.find(sub_norm)

    start_sec = srt_time_to_sec(start_time)
    end_sec = srt_time_to_sec(end_time)

    duration = end_sec - start_sec

    if start_idx == -1:
        return start_time, "[RATIO-FALLBACK]"

    ratio = start_idx / len(full_norm)

    est_start = start_sec + ratio * duration

    return sec_to_srt(est_start), "[RATIO]"


def detect_gender(text):
    if "\u200b" in text:
        return "man"
    if "\u200c" in text:
        return "woman"
    return "unknown"


# =========================
# MAIN (XỬ LÝ THỜI GIAN)
# (GIỮ NGUYÊN)
# =========================
def time_start_img(searches):
    srt_main = parse_srt("./audio_ffmpegs/fin_aud_0_cor.srt")

    sentences = extract_sentences(searches)
    images = sorted(glob.glob("./images/*.jpg"))

    if len(sentences) != len(images):
        print(f"[ERROR] sentences={len(sentences)} != images={len(images)}")
        return

    print("\nID              start         end            duration  gender")
    print("---------------------------------------------------------------")

    results = []

    for i, sent in enumerate(sentences):
        sent_l = normalize_text(sent)

        # ===== tìm câu trong SRT =====
        match, matched_sub = find_sentence_match(sent_l, srt_main)

        if not match:
            print(f"[ERROR] not found sentence: {sent}")
            continue

        gender = detect_gender(match["text"])

        if matched_sub != sent_l:
            print(f"    [FUZZY] '{sent_l}' → '{matched_sub}'")

        time_start_s = match["start"]
        time_end = match["end"]

        # ===== nội suy vị trí =====
        time_start, mode = estimate_start_by_position(
            matched_sub,
            match["text"],
            time_start_s,
            time_end
        )

        start_sec = srt_time_to_sec(time_start)
        end_sec = srt_time_to_sec(time_end)
        duration = end_sec - start_sec

        # ===== chặn lỗi =====
        if duration <= 0 or duration > 10:
            print(f"    [ERROR] bad duration: {duration:.1f}s → skip")
            continue

        # ===== ID =====
        img_name = os.path.basename(images[i])
        img_id = "_".join(img_name.split("_")[:3]) + "_"

        print(f"{img_id:<15} {time_start}  {time_end}   {duration:.1f}s      {gender}")

        results.append({
            "id": img_id,
            "start": time_start,
            "end": time_end,
            "duration": duration,
            "gender": gender
        })

    # ===== save =====
    with open("bk_img_time", "w", encoding="utf-8") as f:
        for r in results:
            f.write(f"{r['id']},{r['start']},{r['end']},{r['duration']:.2f},{r['gender']}\n")

    printf("\nSTEP 13 DONE\n")


# =========================
# 7. MAIN (TẢI ẢNH - CHẠY TUẦN TỰ AN TOÀN)
# (Cập nhật để dùng Serper API và quản lý độ trễ)
# =========================
async def main(searches):
    os.makedirs("images", exist_ok=True)

    items, stats = parse_keywords_block(searches)

    print("\n========== REPORT ==========")
    print(f"TOTAL: {stats['TOTAL']}")
    print(f"HOOK : {stats['HOOK']}")
    print(f"INFO : {stats['INFO']}")
    print(f"MAIN : {stats['MAIN']}")
    print(f"BYE  : {stats['BYE']}")
    print("============================\n")

    async with aiohttp.ClientSession() as session:
        # Chạy tuần tự từng item một (Xử lý xong cái này mới sang cái kia)
        for item in items:
            await process_item(session, item, "images", num=100) # num=15 là giới hạn tìm kiếm Serper

    # 🔥 cleanup
    await asyncio.sleep(0.1)


def bk_all_imgs():
    # INPUT / OUTPUT
    images = sorted(glob.glob("./images/*.jpg"))
    bk_dir = "./images/bk_imgs"

    # CREATE BACKUP DIR
    os.makedirs(bk_dir, exist_ok=True)

    # COPY ALL IMAGES
    for img in images:
        dst = os.path.join( bk_dir, os.path.basename(img) )
        try:
            #shutil.copy2(img, dst)
            shutil.move(img, dst)
            print(f"[MOVE] {img} -> {dst}")
        except Exception as e:
            print(f"[ERROR MOVE] {img}")
            print(e)

    print(f"[DONE] Backup {len(images)} images.")


def copy_all_sel_imgs():
    # INPUT / OUTPUT
    img_dir = "./images"
    best_dir = "./images/best_imgs"

    # =====================================================
    # 1. REMOVE ALL JPG IN ./images
    # old_imgs = sorted(glob.glob(os.path.join(img_dir, "*.jpg")))
    # for img in old_imgs:
    #     try:
    #         os.remove(img)
    #         print(f"[REMOVE] {img}")
    #     except Exception as e:
    #         print(f"[ERROR REMOVE] {img}")
    #         print(e)

    # =====================================================
    # 2. COPY ALL BEST IMAGES TO ./images
    best_imgs = sorted(glob.glob(os.path.join(best_dir, "*")))

    if not best_imgs:
        print("[ERROR] No images in ./images/best_imgs")
        return

    copy_count = 0

    for img in best_imgs:
        dst = os.path.join(
            img_dir,
            os.path.basename(img)
        )

        try:
            shutil.copy2(img, dst)
            print(f"[COPY] {img} -> {dst}")
            copy_count += 1
        except Exception as e:
            print(f"[ERROR COPY] {img}")
            print(e)

    print(f"[DONE] Restored {copy_count} selected images.")


def check_searchs_var(searches):
    # LOAD SRT
    srt_main = parse_srt("./audio_ffmpegs/fin_aud_0_cor.srt")

    # EXTRACT SENTENCES
    sentences = extract_sentences(searches)

    # CHECK
    print("\nCHECK SEARCH SENTENCES")
    print("------------------------------------------------------------")

    ok_count = 0
    fail_count = 0
    failed_sentences = []

    for i, sent in enumerate(sentences):
        sent_l = normalize_text(sent)
        # FIND MATCH
        match, matched_sub = find_sentence_match( sent_l, srt_main )

        # REPORT
        if match:
            print(f"[OK] #{i+1}")
            print(f"     SEARCH : {sent}")

            if matched_sub != sent_l:
                print(f"     MATCH  : {matched_sub}")
                print(f"     MODE   : FUZZY")
            else:
                print(f"     MODE   : EXACT")
            ok_count += 1
        else:
            print(f"[FAIL] #{i+1}")
            print(f"       SEARCH : {sent}")
            failed_sentences.append(sent)
            fail_count += 1
        print("------------------------------------------------------------")

    # SUMMARY
    print("\nSUMMARY")
    print("------------------------------------------------------------")
    print(f"[OK]   : {ok_count}")
    print(f"[FAIL] : {fail_count}")

    # FAILED LIST
    if failed_sentences:
        print("\nFAILED SENTENCES")
        print("------------------------------------------------------------")
        for i, s in enumerate(failed_sentences, start=1):
            print(f"{i}. {s}")
        print("------------------------------------------------------------\n")
    else:
        print("\n[ALL PASSED]")


def check_searchs_var_v1(searches):
    import re

    # LOAD ./scripts.yt
    with open("./scripts.yt", "r", encoding="utf-8") as f:
        content = f.read()

    # EXTRACT scripts = """ ... """
    m = re.search(r'scripts\s*=\s*"""(.*?)"""', content, re.DOTALL)

    if not m:
        print("[ERROR] Cannot find scripts = \"\"\" ... \"\"\" in ./scripts.yt")
        return

    scripts_text = m.group(1)

    # PARSE SENTENCES FROM scripts.yt
    # lấy phần text sau:
    # 0p5s_Man_Q: Hello world
    script_sentences = []

    for line in scripts_text.splitlines():
        line = line.strip()

        if not line:
            continue

        # bỏ section title
        if line in ["HOOK", "INFO", "START", "MAIN", "BYE"]:
            continue

        # match dialogue line
        m_line = re.match(r'^[^:]+:\s*(.+)$', line)

        if m_line:
            text = m_line.group(1).strip()

            if text:
                script_sentences.append(normalize_text(text))

    # EXTRACT SEARCH SENTENCES
    sentences = extract_sentences(searches)

    # CHECK
    print("\nCHECK SEARCH SENTENCES")
    print("------------------------------------------------------------")

    ok_count = 0
    fail_count = 0
    failed_sentences = []

    for i, sent in enumerate(sentences):
        sent_l = normalize_text(sent)

        # FIND MATCH
        match = False
        matched_line = None

        for line in script_sentences:
            if line == sent_l:
                match = True
                matched_line = line
                break

        # FUZZY
        if not match:
            for line in script_sentences:
                if sent_l in line or line in sent_l:
                    match = True
                    matched_line = line
                    break

        # REPORT
        if match:
            print(f"[OK] #{i+1}")
            print(f"     SEARCH : {sent}")

            if matched_line != sent_l:
                print(f"     MATCH  : {matched_line}")
                print(f"     MODE   : FUZZY")
            else:
                print(f"     MODE   : EXACT")

            ok_count += 1

        else:
            print(f"[FAIL] #{i+1}")
            print(f"       SEARCH : {sent}")

            failed_sentences.append(sent)
            fail_count += 1

        print("------------------------------------------------------------")

    # =========================================================
    # SUMMARY
    # =========================================================
    print("\nSUMMARY")
    print("------------------------------------------------------------")
    print(f"[OK]   : {ok_count}")
    print(f"[FAIL] : {fail_count}")

    # =========================================================
    # FAILED LIST
    # =========================================================
    if failed_sentences:
        print("\nFAILED SENTENCES")
        print("------------------------------------------------------------")

        for i, s in enumerate(failed_sentences, start=1):
            print(f"{i}. {s}")

        print("------------------------------------------------------------\n")

    else:
        print("\n[ALL PASSED]")


def choose_the_best_imgs():
    SEARCH_FILE     = "./searches.yt"
    IMG_DIR         = Path("./images/bk_imgs")
    BEST_DIR        = Path("./images/best_imgs")
    CACHE_FILE      = "./images/gemini_image_cache.json"
    MAX_WORKERS     = 5

    BEST_DIR.mkdir(exist_ok=True)

    # GEMINI CLIENT
    client = genai.Client()

    # ======================================================
    # TEST CONNECTION
    def test_gemini_connection(client):
        try:
            client.models.generate_content(
                model="gemini-2.0-flash",
                contents="ping",
                config=types.GenerateContentConfig(
                    max_output_tokens=1
                )
            )
            print("\n[INFO] Gemini API connection OK\n")
            return True
        except Exception as e:
            print("\n[ERROR] Gemini API connection failed\n")
            print(e)
            return False

    if not test_gemini_connection(client):
        exit("Stop: cannot connect to Gemini API")

    # ======================================================
    # CACHE
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            CACHE = json.load(f)
    else:
        CACHE = {}

    def save_cache():
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump( CACHE, f, ensure_ascii=False, indent=2 )

    # =========================================================
    # LOAD SEARCH FILE
    with open(SEARCH_FILE, "r", encoding="utf-8") as f:
        raw_text = f.read()

    # =========================================================
    # PARSE SEARCHES
    sections = ["HOOK", "INFO", "START", "MAIN", "BYE"]
    data = { "HOOK": [], "INFO": [], "MAIN": [], "BYE": [] }
    current_section = None
    lines = raw_text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if line in sections:
            current_section = line
            i += 1
            continue

        m = re.match(r"^(\d+)\.\s+(.*)", line)

        if m and current_section:
            idx = int(m.group(1))
            sentence = m.group(2).strip()
            image_desc = ""
            keywords = ""

            j = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if nxt in sections:
                    break
                if re.match(r"^\d+\.", nxt):
                    break
                if nxt.startswith("Hình:"):
                    image_desc = nxt.replace("Hình:", "").strip()
                if nxt.startswith("Keywords:"):
                    keywords = nxt.replace("Keywords:", "").strip()
                j += 1

            real_section = current_section

            # START => INFO
            if current_section == "START":
                real_section = "INFO"

            # AUTO CONTINUE INDEX
            new_idx = len(data[real_section]) + 1

            data[real_section].append({
                "idx": new_idx,
                "sentence": sentence,
                "image_desc": image_desc,
                "keywords": keywords,
            })

            i = j
            continue
        i += 1

    # DEBUG
    #with open("123.test", "w", encoding="utf-8") as f: f.write(str(data))

    # =========================================================
    # FIND CANDIDATE IMAGES
    def get_candidate_images(section, item):
        if section == "HOOK":
            pattern = f"img_1HOOK_{item['idx']:02d}_"
        elif section == "INFO":
            pattern = f"img_2INFO_{item['idx']:02d}_"
        elif section == "MAIN":
            pattern = f"img_3MAIN_{item['idx']:02d}_"
        elif section == "BYE":
            pattern = f"img_4BYE_{item['idx']:02d}_"
        else:
            return []
        files = []
        for f in IMG_DIR.glob("*"):
            if pattern in f.name:
                files.append(f)
        return sorted(files)

    # =========================================================
    # MIME TYPE
    def get_mime_type(path):
        mime, _ = mimetypes.guess_type(path)
        if mime is None:
            return "image/jpeg"
        return mime

    # =========================================================
    # BUILD CACHE KEY
    def build_cache_key(section, item, image_files):
        return json.dumps({
            "section": section,
            "idx": item["idx"],
            "sentence": item["sentence"],
            "image_desc": item["image_desc"],
            "keywords": item["keywords"],
            "images": [x.name for x in image_files]
        }, ensure_ascii=False)

    # =========================================================
    # GEMINI IMAGE SELECTOR
    def choose_best_image(section, item, image_files):
        image_name_map = build_image_name_map(image_files)
        cache_key = build_cache_key( section, item, image_files )
        if cache_key in CACHE:
            print(f"--> [CACHE HIT] {section} #{item['idx']}")
            return CACHE[cache_key]

        print("--> [ENTER GEMINI API]")
        prompt = f"""
You are an expert image selector.

TASK:
Analyze ALL images carefully and choose the BEST image.

TARGET INFORMATION:

SECTION:
{section}

SENTENCE:
{item['sentence']}

IMAGE DESCRIPTION:
{item['image_desc']}

KEYWORDS:
{item['keywords']}

IMPORTANT:
- Analyze every image
- Compare them carefully
- Choose ONLY ONE best image

OUTPUT FORMAT:
Return VALID JSON only.

Example:
{{
  "best_filename": "img_1HOOK_01_xx.jpg",
  "reasoning": "This image best matches the political discussion in London.",
  "scores": [
    {{
      "filename": "img_1HOOK_01_a.jpg",
      "score": 92,
      "reason": "Strong political context."
    }},
    {{
      "filename": "img_1HOOK_01_b.jpg",
      "score": 75,
      "reason": "Somewhat related."
    }}
  ]
}}

RULES:
- score range: 0-100
- no markdown
- no extra text
- JSON only

IMPORTANT:
When selecting best image:
- DO NOT return real filename
- ONLY return:
    image_1
    image_2
    image_3
"""
        prompt += "\n\nIMAGE ORDER:\n"
        for idx, img_path in enumerate(image_files):
            prompt += ( f"\nImage {idx+1}: {img_path.name}" )
        contents = [prompt]
        for img_path in image_files:
            with open(img_path, "rb") as f:
                img_bytes = f.read()
            contents.append(
                types.Part.from_bytes(
                    data=img_bytes,
                    mime_type=get_mime_type(img_path)
                )
            )
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=0,
                    max_output_tokens=2000,
                    response_mime_type="application/json",
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=1024
                    )
                )
            )
            text = response.text.strip()

            # DEBUG
            #with open("123.test", "w", encoding="utf-8") as f: f.write(str(text))

            # cleanup
            text = text.replace("```json", "")
            text = text.replace("```", "")
            text = text.strip()

            result = json.loads(text)
            best_raw = str( result.get("best_filename", "") ).strip().lower()

            # MAP BACK TO REAL FILENAME
            best_real = image_name_map.get(best_raw)

            # fallback
            if best_real is None:
                # thử remove extension
                best_raw_noext = os.path.splitext(best_raw)[0]
                best_real = image_name_map.get(best_raw_noext)

            # update result
            result["best_filename_raw"] = result.get("best_filename")
            result["best_filename"] = best_real

            CACHE[cache_key] = result

            # DEBUG
            #with open("123.test", "w", encoding="utf-8") as f: f.write(str(result))

            save_cache()
            return result
        except Exception as e:
            print("    [ERROR] Gemini parse failed")
            print(e)
            return {
                "best_filename": None,
                "reasoning": str(e),
                "scores": []
            }

    # =========================================================
    # BUILD IMAGE NAME MAP
    def build_image_name_map(image_files):
        image_name_map = {}
        for idx, img_path in enumerate(image_files):
            real_name = img_path.name
            n = idx + 1
            aliases = [
                str(n),
                f"image_{n}",
                f"image{n}",

                f"img_{n}",
                f"img{n}",

                f"photo_{n}",
                f"photo{n}",

                f"picture_{n}",
                f"picture{n}",
            ]
            # filename thật cũng map luôn
            aliases.append(real_name)
            for a in aliases:
                image_name_map[a.lower()] = real_name
        return image_name_map

    # =========================================================
    # COPY BEST IMAGE
    def copy_best_image(best_filename):
        if not best_filename:
            return
        src = IMG_DIR / best_filename
        if not src.exists():
            print(f"    [ERROR] Missing source image: {src}")
            return
        dst = BEST_DIR / best_filename
        shutil.copy(src, dst)

    # =========================================================
    # PROCESS ONE ITEM
    def process_item_img(section, item):
        candidates = get_candidate_images(section, item)

        print("\n===================================================")
        print(f"{section} #{item['idx']}")
        print(f"\nSentence : {item['sentence']}")
        print(f"Image Desc: {item['image_desc']}")
        print(f"Keywords : {item['keywords']}")

        print("\nCandidates:")

        for c in candidates:
            print("   ", c.name)

        if not candidates:
            return {
                "section": section,
                "idx": item["idx"],
                "best_filename": None,
                "reasoning": "No candidates"
            }

        # call GOOGLE AI
        result = choose_best_image( section, item, candidates )

        # DEBUG
        #with open("123.test", "w", encoding="utf-8") as f: f.write(str(result))

        best = result.get("best_filename")
        print("    [BEST] ", best)
        print("        [REASONING]")
        print(result.get("reasoning"))
        print("        [SCORES]")
        for s in result.get("scores", []):
            print(
                f"    {s['filename']:40} "
                f"score={s['score']:3} "
                f"reason={s['reason']}"
            )

        copy_best_image(best)

        return {
            "section": section,
            "idx": item["idx"],
            "best_filename": best,
            "reasoning": result.get("reasoning"),
            "scores": result.get("scores", [])
        }

    # =========================================================
    # BUILD TASKS
    tasks = []
    for section in ["HOOK", "INFO", "MAIN", "BYE"]:
        for item in data[section]:
            tasks.append((section, item))

    # =========================================================
    # MULTI THREAD RUN
    # results = []
    # start_time = time.time()
    # with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    #     futures = []
    #     for section, item in tasks:
    #         future = executor.submit( process_item_img, section, item )
    #         futures.append(future)

    #     for future in as_completed(futures):
    #         try:
    #             result = future.result()
    #             results.append(result)
    #         except Exception as e:
    #             print("    [ERROR] THREAD ERROR")
    #             print(e)

    # =========================================================
    # SEQUENTIAL RUN
    results = []
    start_time = time.time()
    for section, item in tasks:
        try:
            result = process_item_img( section, item )
            results.append(result)
        except Exception as e:
            print("    [ERROR] PROCESS ERROR")
            print(e)

    # =========================================================
    # SORT RESULTS
    section_order = { "HOOK": 0, "INFO": 1, "MAIN": 2, "BYE": 3 }

    results.sort(
        key=lambda x: (
            section_order[x["section"]],
            x["idx"]
        )
    )

    # =========================================================
    # FINAL OUTPUT
    print("\n\n")
    print("===================================================")
    print("FINAL SELECTED FILES")
    print("===================================================")

    for r in results:
        print(
            f"{r['section']:6} "
            f"{r['idx']:02} "
            f"-> {r['best_filename']}"
        )

    # =========================================================
    # SAVE FINAL REPORT
    report = { "results": results }

    with open( "./fin_sel_images.json", "w", encoding="utf-8" ) as f:
        json.dump( report, f, ensure_ascii=False, indent=2 )
    elapsed = time.time() - start_time

    print("\n===================================================")
    print("DONE")
    print("===================================================")

    print(f"Total tasks : {len(tasks)}")
    print(f"Elapsed time: {elapsed:.2f}s")
    print(f"Best images : {BEST_DIR}")
    print(f"JSON report : fin_sel_images.json")
    print(f"Cache file  : {CACHE_FILE}")

    printf("\nSTEP 12 DONE\n")


def create_thumb_wtext(num=6, _batch_mode=False):
    # Tự động dò thumb_logo_x.jpg (x < 100) và tạo batch ảnh kế tiếp
    if not _batch_mode:
        pattern = re.compile(r"^thumb_logo_(\d+)\.jpg$")
        existing_nums = []

        for name in os.listdir("."):
            m = pattern.match(name)
            if not m:
                continue
            idx = int(m.group(1))
            if idx < 100:
                existing_nums.append(idx)

        if not existing_nums:
            # Không có file nào thì tạo từ 1 -> num
            start_num = 1
            end_num = min(num, 99)
            print(f"[AUTO] No thumb_logo_x.jpg found. Generating from {start_num} to {end_num}...")

            for i in range(start_num, end_num + 1):
                create_thumb_wtext(num=i, _batch_mode=True)
            return f"./thumb_nologo_{end_num}.jpg"

        if existing_nums:
            last_num = max(existing_nums)
            seed_logo = f"./thumb_logo_{num}.jpg"

            # Chỉ chạy batch khi có sẵn thumb_logo_{num}.jpg
            if os.path.exists(seed_logo):
                start_num = last_num + 1
                end_num = min(start_num + 6 - 1, 99)

                print(f"[AUTO] Found {seed_logo}.")
                print(f"[AUTO] Existing max thumb_logo_x.jpg (x < 100): {last_num}")
                print(f"[AUTO] Generating thumb_nologo/thumb_logo from {start_num} to {end_num}...")

                for i in range(start_num, end_num + 1):
                    create_thumb_wtext(num=i, _batch_mode=True)
                return f"./thumb_nologo_{end_num}.jpg"

    # CONFIG
    MODEL_NAME  = "gemini-3.1-flash-image-preview"
    image_files = "./img1_HOOK.jpg"

    # LOAD IMAGE
    with open(image_files, "rb") as f:
        image_bytes = f.read()

    # PROMPT
    prompt = f"""
TITLE:
{fin_title}

CONTENT:
{scripts}

You are an expert YouTube thumbnail designer.

TASK:
1. Analyze the image carefully.
2. Choose the BEST thumbnail text.
3. Insert the text directly onto the image.

RULES:
- TEXT should supplement the image, not repeat the title.
- Use 3–5 words maximum.
- Bold sans-serif typography.
- High contrast text.
- Emotional and curiosity-driven wording.
- Professional YouTube thumbnail style.
- Perfect spelling.

TYPOGRAPHY:
- Màu text bạn chọn phù hợp để làm nổi bậc thu hút.
- Thick black shadow.
- Large readable font.
- Similar to news/political YouTube thumbnails.

OUTPUT:
Return the final edited thumbnail image.

TEXT LAYOUT:
- The text may use 1, 2, 3, or 4 lines.
- Prioritize positions that DO NOT cover faces, people, or important objects.
- Smart composition.
- Cinematic thumbnail style.
- Ảnh có 2 người thì cả 2 face là quan trọng, ưu tiên text không che 2 mặt người
- Sau mặt là tay với cử chỉ giao tiếp cũng quan trọng, text ko nên che.
- Ưu tiên chọn khoảng tróng giữa 2 người, hoặc khoảng tróng bên phải hay bên trái.

"""

    prompt = prompt + prompt_more

    # GEMINI CLIENT
    client = genai.Client()

    # GENERATE
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/jpeg",
            ),
            prompt,
        ],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"]
        ),
    )

    # SAVE OUTPUT
    out_file = f"./thumb_nologo_{num}.jpg"
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            with open(out_file, "wb") as f:
                f.write(part.inline_data.data)
            print(f"[OK] Saved: {out_file}")

    BG_IMG      = out_file
    LOGO_IMG    = "./img6_LOGO.png"
    OUTPUT      = f"./thumb_logo_{num}.jpg"

    LOGO        = "RIGHT"       # RIGHT or LEFT
    SIZE        = 100           # logo size 100x100

    # LOGO POSITION
    margin = 20

    if LOGO.upper() == "RIGHT":
        logo_x = f"W-w-{margin}"
    else:
        logo_x = f"{margin}"

    logo_y = f"{margin}"

    # FFMPEG FILTER FINAL OUTPUT = 1920x1080
    filter_complex = f"""
    [0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080[bg];
    [1:v]format=rgba,scale={SIZE}:{SIZE}[logo];
    [bg][logo]overlay={logo_x}:{logo_y}[out]
    """

    # CMD
    cmd = [
        "ffmpeg",
        "-y",
        "-i", BG_IMG,
        "-i", LOGO_IMG,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-frames:v", "1",
        "-q:v", "2",
        OUTPUT
    ]

    # RUN
    print("\nRUN FFMPEG:")
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"\n[OK] Saved: {OUTPUT}")

    return out_file
    print("[ERROR] No image returned")

    printf("\nSTEP 17 DONE\n")


def create_description():
    # CONFIG
    MODEL_NAME = "gemini-2.5-flash"

    # WARNING
    warning = f"""
⚠️ Viewer Notice

This video contains some images generated using artificial intelligence (AI). These visuals are used for illustrative purposes to enhance clarity and make the content more engaging.

Please note that AI-generated images may not fully reflect real-world accuracy and should be considered as visual representations only.

"""

    # PROMPT
    prompt = f"""
TITLE:
{fin_title}

CONTENT:
{scripts}

Write a summary of the main content of the video in 5 - 10 sentences.
"""

    # GEMINI CLIENT
    client = genai.Client()

    # GENERATE
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )

    # SAVE RESULT
    bk_description = "\n"+fin_title+"\n\n"+response.text+"\n"+warning

    # SAVE FILE
    with open("bk_description.txt", "w", encoding="utf-8") as f:
        f.write(bk_description)

    printf("\nSTEP 18 DONE\n")

    return bk_description


def rename_all_final_file():
    if not fin_title:
        print("    ERROR: fin_title is empty. Cannot rename final files.")
        return False

    rename_tasks = [
        ("build_video_final.mp4", f"{fin_title}.mp4"),
        ("build_video_final.srt", f"{fin_title}.srt"),
        ("bk_description.txt", f"{fin_title}.txt"),
    ]
    copy_tasks = [
        ("scripts.eze", f"{fin_title}.eze"),
    ]

    success = True

    for src, dst in rename_tasks:
        if not os.path.exists(src):
            print(f"    WARNING: File {src} was not found. Skip rename to {dst}.")
            success = False
            continue

        os.replace(src, dst)
        print(f"    RENAMED: {src} -> {dst}")

    for src, dst in copy_tasks:
        if not os.path.exists(src):
            print(f"    WARNING: File {src} was not found. Skip copy to {dst}.")
            success = False
            continue

        shutil.copy2(src, dst)
        print(f"    COPIED: {src} -> {dst}")

    printf("\nSTEP 18 RENAME DONE\n")

    return success


def copy_all_final_file(dir="0000"):
    if not fin_title:
        print("    ERROR: fin_title is empty. Cannot copy final files.")
        return False

    base_dir = r"D:\94_YT\EasyEnglish"
    target_dir = os.path.join(base_dir, dir)

    files_to_copy = [
        f"{fin_title}.mp4",
        f"{fin_title}.srt",
        f"{fin_title}.txt",
        f"{fin_title}.eze",
        f"{fin_title}.jpg",
    ]

    success = True

    # Create target directory if not exists
    os.makedirs(target_dir, exist_ok=True)
    print(f"    CREATED DIR: {target_dir}")

    # Copy files
    for file_name in files_to_copy:
        if not os.path.exists(file_name):
            print(f"    WARNING: File {file_name} was not found. Skip copy.")
            success = False
            continue

        dst_path = os.path.join(target_dir, file_name)

        shutil.copy2(file_name, dst_path)
        print(f"    COPIED: -> {dst_path}")

    printf("\nSTEP 19 COPY DONE\n")

    return success


# =========================
# RUN (GIỮ NGUYÊN)
# =========================
if __name__ == "__main__":
    searches = load_searches_from_file("./searches.yt")

    # Giá trị mặc định
    params = {"dir": "0000"}

    if len(sys.argv) < 2:
        print_help()
    else:
        mode = sys.argv[1].lower()
        if mode == "12":
            asyncio.run(main(searches))
            bk_all_imgs()
            choose_the_best_imgs()
            copy_all_sel_imgs()
        elif mode == "13":
            time_start_img(searches)
        elif mode == "sub1":
            check_searchs_var_v1(searches)

        elif mode == "test1":
            choose_the_best_imgs()
            copy_all_sel_imgs()
        elif mode == "test2":
            print_help()

        elif mode == "17":
            create_thumb_wtext(num=6)
        elif mode == "18":
            for arg in sys.argv[2:]:
                if arg.lower().startswith("dir="):
                    params["dir"] = arg.split("=")[1]
            create_description()
            rename_all_final_file()
            copy_all_final_file(dir=params["dir"])

        elif mode == "check_genai":
            check_genai()
