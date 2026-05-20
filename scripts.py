# -*- coding: utf-8 -*-
# @Author: Cao Phi Ho
# @Date:   2026/04/08, 21:35
# @Last Modified by:   CPH
# @Last Modified time: 2026/05/21, 04:34
# @Last Modified time: 2026/04/08, 21:35 Create file

from elevenlabs.client import ElevenLabs
import os
import random
import re
import sys
import subprocess
import glob
from datetime import timedelta
import shutil
import difflib
import wave
import struct
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import string
import srt
import shlex
import unicodedata
import threading

import warnings

print(sys.executable)

#===============================================================================
QUALITY=0

# INITIALIZE ELEVENLABS CLIENT
#client = ElevenLabs(api_key="sk_bc2c0a1aab3d539f699c44d906a88e577b16ce04c39f09d9") # ho.caophi.photo1@gmail.com
client = ElevenLabs(api_key="sk_8758751e8f4c3a384f8a9395bef9d1bcb71f2b6068559b40") # vitaly128@jualakunfb.co pass: Muabantool.com@123

# CAPCUT (https://www.capcut.com/ai-creator-home)
# goa250enhancei9241@gmail.com 260508_1900  remove_260518_0310
# goa260enhancei9241@gmail.com 260518_0315
# goa270enhancei9241@gmail.com 260520_0320

# https://serper.dev/
# ho.caophi.photo1@gmail.com 260506_1900

#   git checkout main; git pull origin main
#   git merge dev; git push origin main
#   git switch dev

#   pip freeze | Out-File -Encoding utf8 z_requirements
#   python -m pip install --upgrade pip
#   pip install -r z_requirements
#===============================================================================

def printf(*args):
    print("".join(map(str, args)))

def test_encoder(codec):
    import subprocess
    result = subprocess.run(
        [
            "ffmpeg", "-f", "lavfi", "-i", "color=size=128x128:rate=1",
            "-t", "1",
            "-c:v", codec,
            "-f", "null", "-"
        ],
        capture_output=True,
        text=True
    )
    print(f"{codec} -> returncode:", result.returncode)
    return result.returncode == 0

def detect_gpu():
    if test_encoder("h264_amf"):
        return 1, 1
    elif test_encoder("h264_qsv"):
        return 1, 0
    elif test_encoder("h264_nvenc"):
        return 1, 0
    else:
        return 0, 0

GPU, AMD = detect_gpu()
printf("GPU: ", GPU,"; ", "AMD: ", AMD)

if QUALITY==1:
    if GPU == 1 and AMD == 1:
        # HWGPU = "-c:v h264_amf -quality quality"+" "
        HWGPU = (
            "-c:v h264_amf "
            "-quality quality "
            "-rc cqp "
            "-qp_i 26 "
            "-qp_p 28 "
            "-qp_b 30 "
        )
    elif GPU == 1:
        HWGPU = "-c:v h264_qsv -preset fast"+" "
    else:
        HWGPU = "-c:v libx264 -preset medium -crf 18"+" "
else:
    if GPU == 1 and AMD == 1:
        # HWGPU = "-c:v h264_amf -quality speed -usage transcoding -rc cqp -qp_i 24 -qp_p 26 -qp_b 28"+" "
        HWGPU = (
            "-c:v hevc_amf "
            "-quality speed "
            "-rc cqp "
            "-qp_i 28 "
            "-qp_p 30 "
        )
    elif GPU == 1:
        HWGPU = "-c:v h264_qsv -preset veryfast"+" "
    else:
        HWGPU = "-c:v libx264 -preset medium -crf 18"+" "

# Phân tách chuỗi HWGPU thành danh sách các đối số
# shlex.split sẽ xử lý đúng các chuỗi có dấu nháy nếu có (ví dụ: "some_value with space")
hwgpu_args = shlex.split(HWGPU)

# 1. Tắt cảnh báo từ module warnings của Python (cho pkg_resources)
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

# 2. Tắt log của thư viện Torch (cho torchvision và torchaudio)
os.environ["TORCH_CPP_LOG_LEVEL"] = "ERROR"

# 3. Chặn các thông báo in trực tiếp ra stderr/stdout khi import các thư viện nặng
# (Đặc biệt là thông báo "The torchaudio backend is switched...")
class SuppressStd:
    def __enter__(self):
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr

# Thực hiện import các thư viện gây ồn ào trong block này
# with SuppressStd():
#     try:
#         import stable_whisper
#         import whisperx
#         import torch
#         import torchvision
#         import torchaudio
#         import pytorch_lightning
#     except ImportError:
#         pass
import stable_whisper
import whisperx
import torch
import torchvision
import torchaudio
import pytorch_lightning

#===============================================================================
# 1. LOGIC ĐỌC BIẾN scripts TỪ FILE .eze (CHẤP NHẬN FILE CÓ TEXT LẠ)
#===============================================================================
def get_scripts():
    scripts_files = glob.glob("scripts.yt")
    if not scripts_files:
        print("    ERROR: File {scripts_files} was not found in the directory.")
        return ""

    file_path = scripts_files[0]
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Tìm nội dung nằm giữa scripts = """ và """
            # Sử dụng re.DOTALL để khớp cả xuống dòng
            match = re.search(r'scripts\s*=\s*"""(.*?)"""', content, re.DOTALL)
            if match:
                return match.group(1).strip()
            else:
                print(f"    ERROR: Structure scripts = \"\"\"...\"\"\" not found in {file_path}")
                return ""
    except Exception as e:
        print(f"    ERROR when reading file {file_path}: {e}")
        return ""

def get_searches():
    searches_files = glob.glob("searches.yt")
    if not searches_files:
        print("    ERROR: The file {searches_files} was not found in the directory.")
        return ""

    file_path = searches_files[0]
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Tìm nội dung nằm giữa searches = """ và #end_searches
            # Sử dụng re.DOTALL để khớp cả xuống dòng
            match = re.search(r'searches\s*=\s*"""(.*?)#end_searches', content, re.DOTALL)
            if match:
                return match.group(1).strip()
            else:
                print(f"    ERROR: Search structure = \"\"\"...#end_searches not found in {file_path}")
                return ""
    except Exception as e:
        print(f"    ERROR when reading file {file_path}: {e}")
        return ""

# Nạp nội dung kịch bản
scripts  = get_scripts()
searches = get_searches()

#===============================================================================
# mapping voice
VOICE_MAP = {
    "Man1":     {"voice_id": "ktkP7Nsj67dw2zcplQYt"}, # Lawrence - Bright and Informative
    "Man2":     {"voice_id": "5PEXwsADjqmz7GO58o3B"}, # Julian - Raspy, Dramatic and Well-spoken
    "Woman1":   {"voice_id": "QtY3JBOUKEB5xzrRfOKc"}, # Maisie - Friendly Casual Neighbor
    "Woman2":   {"voice_id": "g7LVvkPWALzPxOQbF6OE"}  # Jade - Upbeat and Natural
}

#    "Man2":     {"voice_id": "pVnrL6sighQX7hVz89cp"}, # Henry
#    "Man1":     {"voice_id": "VCgLBmBjldJmfphyB8sZ"}, # Liam
#    "Woman1":   {"voice_id": "QtY3JBOUKEB5xzrRfOKc"}, # Rachel
#    "Woman2":   {"voice_id": "EXAVITQu4vr4xnSDxMaL"}  # Bella

# mapping stability theo loại câu
STABILITY_MAP = {"Q": (0.35, 0.45), "E": (0.48, 0.55), "R": (0.30, 0.40), "S": (0.55, 0.60), "N": (0.38, 0.45)}

# Emotion boost theo loại câu
STYLE_MAP = {"Q": 0.2, "E": 0.1, "R": 0.3, "S": 0.15, "N": 0.1}

# tạo folder output
output_dir    = "audio_elabs"
processed_dir = "audio_ffmpeg"
silent_dir    = "audio_ffmpegs"

#===============================================================================       █
#===============================================================================      ██
#===============================================================================███    █
#===============================================================================       █
#===============================================================================    ██████
def step_pass_large():
    print("THIS STEP IS PASS")
    print("===================================================")
    print("|||||||||||      ||||        |||||||      |||||||  ")
    print("||         ||   ||  ||     ||      ||   ||      || ")
    print("||         ||  ||    ||    ||           ||         ")
    print("||         || ||      ||   ||           ||         ")
    print("|||||||||||   ||||||||||     ||||||       ||||||   ")
    print("||            ||      ||           ||           || ")
    print("||            ||      ||           ||           || ")
    print("||            ||      ||   ||      ||    ||     || ")
    print("||            ||      ||    |||||||       ||||||   ")
    print("=====================PASSED========================")

def step_fail_large():
    print("THIS STEP IS FAIL")
    print("===================================================")
    print("|||||||||||||    ||||      ||||||||||   ||         ")
    print("||              ||  ||         ||       ||         ")
    print("||             ||    ||        ||       ||         ")
    print("||            ||      ||       ||       ||         ")
    print("||||||||||||  ||||||||||       ||       ||         ")
    print("||            ||      ||       ||       ||         ")
    print("||            ||      ||       ||       ||         ")
    print("||            ||      ||       ||       ||         ")
    print("||            ||      ||   ||||||||||   |||||||||| ")
    print("=====================FAILED========================")

def step_pass_small():
    print("THIS STEP IS PASS")
    print("===================================================")
    print("|||||||||||      ||||        |||||||      |||||||  ")
    print("||         ||  ||    ||    ||           ||         ")
    print("|||||||||||   ||||||||||     ||||||       ||||||   ")
    print("||            ||      ||           ||           || ")
    print("||            ||      ||   ||      ||    ||     || ")
    print("=====================PASSED========================")

def step_fail_small():
    print("THIS STEP IS FAIL")
    print("===================================================")
    print("|||||||||||||    ||||      ||||||||||   ||         ")
    print("||             ||    ||        ||       ||         ")
    print("||||||||||||  ||||||||||       ||       ||         ")
    print("||            ||      ||       ||       ||         ")
    print("||            ||      ||   ||||||||||   |||||||    ")
    print("=====================FAILED========================")

def step_pass_small_2l():
    print("========== PASSED ==========")
    print("██████  PASS  ██████")

def step_fail_small_2l():
    print("========== FAILED ==========")
    print("██████  FAIL  ██████")

FPS = 30.0
FRAME = 1.0 / FPS
WHIS_DB = "bk_database.whis"

first_sound_time = 0.5
activity = []
total_samples_processed = 0

def parse_to_ms(time_str):
    """Chuyển 0p6s thành 600 (miliseconds) cho filter adelay"""
    if not time_str: return 500
    match = re.search(r"(\d+)p(\d+)s", time_str)
    if match:
        return int(match.group(1)) * 1000 + int(match.group(2)) * 100
    return 500

def is_sentence_end(word):
    return re.search(r"[.!?]$", word.strip()) is not None

def is_comma(word):
    return re.search(r",$", word.strip()) is not None

def format_timestamp(seconds):
    """FORMAT CHUẨN - dùng ROUND thay vì INT"""
    td = timedelta(seconds=float(seconds))
    total_seconds = int(td.total_seconds())

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    millis = round((float(seconds) - total_seconds) * 1000)

    # tránh case 1000ms
    if millis == 1000:
        millis = 0
        secs += 1

    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

def get_audio_activity(audio_path, frame_ms=10.0, threshold=1500):
    global activity, total_samples_processed

    """Sử dụng năng lượng RMS thay vì Peak để tránh nhiễu trắng gây detect sai"""
    SAMPLE_RATE = 16000
    cmd = ['ffmpeg', '-i', audio_path, '-f', 's16le', '-ac', '1', '-ar', str(SAMPLE_RATE), '-']
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    samples_per_chunk = int(SAMPLE_RATE * (frame_ms / 1000.0))
    bytes_per_chunk = samples_per_chunk * 2

    while True:
        raw_data = process.stdout.read(bytes_per_chunk)
        if not raw_data or len(raw_data) < bytes_per_chunk:
            break

        samples = struct.unpack(f"<{samples_per_chunk}h", raw_data)

        # TÍNH RMS: Trung bình năng lượng (Chống nhiễu cực tốt)
        sum_sq = sum(s**2 for s in samples)
        rms = math.sqrt(sum_sq / len(samples))

        current_time = total_samples_processed / SAMPLE_RATE
        activity.append({'time': current_time, 'active': 1 if rms > threshold else 0})
        total_samples_processed += samples_per_chunk

    process.terminate()
    return activity

def get_audio_hash_fast(filepath):
    h = hashlib.md5()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def load_whis_db():
    if not os.path.exists(WHIS_DB):
        return {}

    try:
        with open(WHIS_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("    WARNING: bk_database.whis bị lỗi → reset cache")
        return {}

def save_whis_db(db):
    tmp_file = WHIS_DB + ".tmp"

    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    os.replace(tmp_file, WHIS_DB)  # atomic write

def get_whisper_result(audio_path, run_whisper_func):
    db = load_whis_db()
    key = os.path.basename(audio_path)
    audio_hash = get_audio_hash_fast(audio_path)

    # LOAD CACHE
    if key in db:
        if db[key]["hash"] == audio_hash:
            print(f"    LOAD CACHE: {key}")
            cached = db[key]["segments"]
            return stable_whisper.result.WhisperResult(cached)  # ✅ FIX

    # RUN WHISPER
    print(f"    RUN WHISPER: {key}")
    segments_dict = run_whisper_func(audio_path)

    db[key] = {
        "hash": audio_hash,
        "segments": segments_dict
    }
    save_whis_db(db)

    return stable_whisper.result.WhisperResult(segments_dict)  # ✅ FIX

def smart_chunk_sentence(sent, n):
    """
    Chia câu ưu tiên dấu phẩy, nhưng CẤM cắt vụn thành block 1-2 từ.
    """
    if not sent:
        return []

    # 1. Nếu Câu <= n thì không quan tâm ",", trả về luôn
    if len(sent) <= n:
        return [sent]

    # 2. Nếu Câu > n thì chia câu thành nhiều đoạn theo dấu ","
    segments = []
    curr_seg = []
    MIN_WORDS_TO_SPLIT = 3 # Phải có ít nhất 3 từ mới được phép cắt tại dấu phẩy

    for w in sent:
        curr_seg.append(w)
        # Chỉ tách nếu gặp dấu phẩy VÀ đoạn hiện tại đã gom đủ số từ tối thiểu
        if is_comma(w["word"]) and len(curr_seg) >= MIN_WORDS_TO_SPLIT:
            segments.append(curr_seg)
            curr_seg = []

    if curr_seg:
        # Nếu đoạn cuối cùng bị lẻ (quá ngắn), ghép ngược nó vào đoạn trước đó
        if len(curr_seg) < MIN_WORDS_TO_SPLIT and len(segments) > 0:
            segments[-1].extend(curr_seg)
        else:
            segments.append(curr_seg)

    # 3. Áp dụng logic chia đều (cũ) cho từng đoạn
    res = []
    for seg in segments:
        i = 0
        L = len(seg)
        while L - i > 0:
            remain = L - i
            if remain > 2 * n:
                size = n
            elif remain > n:
                size = math.ceil(remain / 2)
            else:
                size = remain
            res.append(seg[i:i+size])
            i += size

    return res

def time_to_seconds(time_str):
    """Chuyển đổi chuỗi thời gian SRT thành giây, hỗ trợ cả dấu ',' và '.' """
    time_str = time_str.replace('.', ',') # Phòng trường hợp file dùng dấu chấm
    h, m, s_ms = time_str.split(':')
    s, ms = s_ms.split(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

def process_srt_visualize(folder_path, file_name, out_file_name):
    # Đường dẫn file input và output
    file_path = os.path.join(folder_path, file_name)
    out_file_path = os.path.join(folder_path, out_file_name)

    # 1. KIỂM TRA FILE CÓ TỒN TẠI KHÔNG
    if not os.path.exists(file_path):
        print(f"    ERROR: Không tìm thấy file đầu vào tại: {file_path}")
        print(f"    Please check the file name (name_file_in) or path (duong_dan)!")
        return

    FRAME_DURATION = 0.0333

    # 2. Đọc nội dung (Dùng utf-8-sig để loại bỏ ký tự BOM ẩn của Windows)
    with open(file_path, 'r', encoding='utf-8-sig') as file:
        content = file.read()

    # Chuẩn hóa dấu xuống dòng (Windows \r\n -> \n)
    content = content.replace('\r\n', '\n')

    # Tách block dựa trên 2 hoặc nhiều dấu xuống dòng liên tiếp
    blocks = re.split(r'\n{2,}', content.strip())

    end_previous = 0.0
    display_index = 1
    processed_count = 0 # Biến đếm xem có xử lý được block nào không

    # Mở file output để ghi
    with open(out_file_path, 'w', encoding='utf-8') as f_out:
        for block in blocks:
            lines = block.split('\n')
            if len(lines) >= 2: # Miễn có index và time là có thể xét
                timestamps = lines[1]
                # Lấy text (nếu có)
                text = " ".join(lines[2:]) if len(lines) >= 3 else ""

                # Bỏ qua nếu caption trống
                if not text.strip():
                    continue

                match = re.search(r'(\d+:\d+:\d+[,.]\d+)\s*-->\s*(\d+:\d+:\d+[,.]\d+)', timestamps)
                if match:
                    start_str, end_str = match.groups()
                    start_current = time_to_seconds(start_str)
                    end_current = time_to_seconds(end_str)

                    # Tính khoảng lặng và khoảng active
                    silent_duration = max(0, start_current - end_previous)
                    active_duration = max(0, end_current - start_current)

                    silent_frames = int(round(silent_duration / FRAME_DURATION))
                    active_frames = int(round(active_duration / FRAME_DURATION))

                    # Ghi ra file (ĐÃ THÊM DẤU "_" Ở GIỮA)
                    visual_str = ('.' * silent_frames) + '_' + ('|' * active_frames)
                    f_out.write(f"{display_index}\n")
                    f_out.write(f"{visual_str}\n")

                    end_previous = end_current
                    display_index += 1
                    processed_count += 1

    # IN THÔNG BÁO KẾT QUẢ
    if processed_count == 0:
        print(f"    WARNING: File {file_name} is empty or does not have a valid sub.")
    else:
        print(f"    COMPLETE {file_name}! Processed {processed_count} lines. Saved at: {out_file_path}")

def get_clean_word_list(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Lấy text từ block SRT
    blocks = re.findall(r"\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n((?:.+\n?)+)", content)

    full_text = ""
    for b in blocks:
        # Xóa marker ẩn và các ký tự đặc biệt
        clean_b = b.replace("\u200B", "").replace("\u200C", "").strip()
        if clean_b and clean_b != "...":
            full_text += " " + clean_b

    # 2. CHUẨN HÓA (QUAN TRỌNG):
    # Chuyển dấu nháy cong thành nháy thẳng
    full_text = full_text.replace("’", "'").replace("‘", "'")
    # Chuyển các dấu gạch nối thành rỗng (để ghép từ lại thay vì tách ra)
    # Ví dụ: 35-year-old -> 35yearold (để đồng bộ nếu cần) hoặc xử lý tùy ý
    # Ở đây ta giữ nguyên nhưng regex sẽ xử lý

    # 3. Tách từ: Chấp nhận từ có dấu nháy thẳng ở giữa
    # Regex này sẽ giữ "it's" thành 1 từ thay vì tách thành "it" và "s"
    words = re.findall(r"\b[a-z0-9]+(?:'[a-z]+)?\b", full_text.lower())
    return words

# 4. Logic Dò mốc thời gian thực tế (Đã fix NameError và Lookback)
def detect_precise_timing(groups):
    global activity

    opt = []
    SEC_1_FRAME = 0.0333
    SEC_9_FRAMES = 0.200 # Giảm bớt độ trễ đuôi để tránh lấn sân
    MIN_GAP = 0.066      # Khoảng hở tối thiểu giữa 2 Sub
    DUMMY_END_LIMIT = 0.133

    # Tăng giới hạn dò tìm lên 3.0 giây để xử lý các đoạn Gap lớn giữa các Section
    MAX_FORWARD_SEARCH = 3.0
    MAX_BACKWARD_SEARCH = 0.8

    for idx in range(len(groups)):
        g = groups[idx]
        #printf ("idx : ", idx)
        #printf ("    g: ", g)

        raw_s, raw_e = g[0]["start"], g[-1]["end"]
        #printf ("raw_s : ", raw_s)
        #printf ("raw_e : ", raw_e)

        if idx == 0:
            precise_s = first_sound_time - SEC_1_FRAME
        else:
            idx_s = max(0, min(len(activity)-1, round(raw_s * 100)))
            b = idx_s

            #printf ("idx_s : ", idx_s)
            #if idx==8: printf ("activity[b]['active'] : ", activity[b]['active'])

            if activity[b]['active'] == 1:
                # Nếu rơi vào vùng có tiếng: Dò ngược về điểm bắt đầu của âm thanh
                # Giới hạn lùi 0.8s để không nhảy sang câu trước
                while b > 0 and activity[b]['active'] == 1 and (raw_s - activity[b]['time']) < MAX_BACKWARD_SEARCH:
                    b -= 1
            else:
                # ĐÂY LÀ CHỖ FIX LỖI 2 GIÂY:
                # Nếu rơi vào vùng im lặng (0): Dò TIẾN về phía trước cho đến khi thấy tiếng
                # Dò tối đa 3.0 giây (vì Gap của bạn là 2.0s)
                while b < len(activity)-1 and activity[b]['active'] == 0 and (activity[b]['time'] - raw_s) < MAX_FORWARD_SEARCH:
                    b += 1

            precise_s = activity[b]['time'] - SEC_1_FRAME

        # --- Dò điểm kết thúc (Nâng cấp: 5-frame Validation & 30-frame Search Limit) ---
        idx_e = max(0, min(len(activity)-1, round(raw_e * 100)))
        e = idx_e

        if activity[e]['active'] == 1 or activity[e-4]['active'] == 1 or activity[e+4]['active'] == 1 or activity[e+8]['active'] == 1 or activity[e-8]['active'] == 1:
            # Nếu đang có tiếng: Dò TIẾN tìm điểm dứt lời thực sự
            search_ptr = e
            # Giới hạn dò tìm 30 frame (khoảng 0.3s tại 100Hz)
            # 1 unit = 0.01s
            max_search_limit = min(len(activity) - 6, e + 333)
            found_stable_silence = False

            while search_ptr < max_search_limit:
                #printf ("search_ptr ", search_ptr)
                # Nếu phát hiện 1 frame im lặng (active=0)
                if activity[search_ptr]['active'] == 0:
                    #printf ("    SILENT 1")
                    # Kiểm tra tiếp 5 frame kế tiếp xem có thực sự im lặng không
                    is_real_silence = True
                    for check_idx in range(search_ptr, search_ptr + 22, 3):
                        if activity[check_idx]['active'] == 1:
                            #printf ("        SILENT FAIL")
                            is_real_silence = False
                            break

                    if is_real_silence:
                        #printf ("        SILENT OKOKOK")
                        e = search_ptr
                        found_stable_silence = True
                        break
                search_ptr += 3

            # Nếu trong 30 frame mà không tìm được khoảng im lặng bền vững (5 frame liên tiếp)
            if not found_stable_silence:
                e = idx_e # Fallback: Lấy lại điểm end ban đầu của Whisper
                printf ("        --> [FAIL] GET ORG WHISPER SILENT AGAIN ", e, "\n")

        else:
            printf ("BUG: THIS CASE IS NOT PROCESS")
            printf ("    idx : ", idx)
            printf ("    idx_e : ", idx_e)
            printf ("    e : ", e)
            printf ("    activity[e]['active'] : ", activity[e]['active'])
            printf ("    activity[e-4]['active'] : ", activity[e-4]['active'])
            printf ("    activity[e+4]['active'] : ", activity[e+4]['active'])
            printf ("    activity[e+8]['active'] : ", activity[e+8]['active'])
            printf ("    activity[e-8]['active'] : ", activity[e-8]['active'])

            # Nếu đã im lặng: Dò lùi lại tìm mốc âm thanh cuối cùng (Logic cũ)
            while e > 0 and activity[e]['active'] == 0 and (raw_e - activity[e]['time']) < 1.0:
                e -= 1

        # Cuối cùng cộng thêm độ trễ đệm (SEC_9_FRAMES)
        precise_e = activity[e]['time'] + SEC_9_FRAMES

        # --- NORMALIZE & SAFETY ---
        new_s, new_e = max(0, precise_s), precise_e

        # Khống chế không cho phép đè lên câu trước
        if opt:
            prev_end = opt[-1]['end']
            # Nếu mốc bắt đầu mới nhảy về quá khứ đè lên câu trước, buộc phải bắt đầu sau câu trước
            if new_s < prev_end + MIN_GAP:
                # Chỉ ép nếu thực sự có âm thanh ở đó, nếu im lặng thì cho phép giãn cách
                new_s = max(new_s, prev_end + MIN_GAP)

        if idx == 0 and new_s < DUMMY_END_LIMIT: new_s = DUMMY_END_LIMIT
        if new_s >= new_e: new_e = new_s + 0.5

        opt.append({'start': new_s, 'end': new_e, 'text': "".join([w["word"] for w in g]).strip()})

    return opt

def verify_srt_consistency(file_0_path, file_1_path):
    print(f"\n    [CHECK] Verifying consistency between Step 5 and Step 6...")

    def get_blocks(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        return re.findall(r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n((?:.+\n?)+)", content)

    def clean_text(t):
        # Chỉ loại bỏ marker ẩn, giữ nguyên dấu câu và mọi thứ khác
        return t.replace("\u200B", "").replace("\u200C", "").strip()

    blocks_0 = get_blocks(file_0_path)
    blocks_1 = get_blocks(file_1_path)

    # 1. Kiểm tra Dummy Anchor (Block 1)
    if clean_text(blocks_0[0][2]) != clean_text(blocks_1[0][2]):
        print(f"        [ERROR] Dummy Anchor mismatch!")
        return False

    # Chuyển blocks_1 thành danh sách để dò dần (pointer)
    ptr_1 = 1 # Bỏ qua block dummy
    errors = 0

    # Duyệt từng câu hoàn chỉnh ở file 0 (bắt đầu từ block 2)
    for i in range(1, len(blocks_0)):
        idx_0, time_0, text_0 = blocks_0[i]
        start_0, end_0 = time_0.split(" --> ")
        clean_text_0 = clean_text(text_0)

        words_in_0 = clean_text_0.split()
        collected_words_1 = []

        # Lấy các block ở file 1 có mốc thời gian nằm trong khoảng của block_0
        # Hoặc lấy cho đến khi đủ số lượng từ
        first_child_start = None
        last_child_end = None

        while len(collected_words_1) < len(words_in_0) and ptr_1 < len(blocks_1):
            idx_1, time_1, text_1 = blocks_1[ptr_1]
            s_1, e_1 = time_1.split(" --> ")

            if first_child_start is None: first_child_start = s_1
            last_child_end = e_1

            collected_words_1.extend(clean_text(text_1).split())
            ptr_1 += 1

        # KIỂM TRA 1: So khớp nội dung từ và dấu câu
        str_0 = " ".join(words_in_0)
        str_1 = " ".join(collected_words_1)

        if str_0 != str_1:
            print(f"        CONTENT MISMATCH at Block {idx_0}:")
            print(f"        Expected: [{str_0}]")
            print(f"        Found:    [{str_1}]")
            errors += 1

        # KIỂM TRA 2: So khớp mốc thời gian (Mỏ neo đầu cuối)
        if first_child_start != start_0 or last_child_end != end_0:
            print(f"        TIMING DRIFT at Block {idx_0}:")
            print(f"        Source: {start_0} --> {end_0}")
            print(f"        Split:  {first_child_start} --> {last_child_end}")
            errors += 1

    if errors == 0:
        print(f"        --> VERIFICATION PASSED: 100% words and punctuation matched.")
        print(f"\n\n            --> PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS\n\n")
        return True
    else:
        print(f"        --> Total {errors} issues found in SRT structure.")
        print(f"\n\n            --> FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL\n\n")
        return False

#===============================================================================██████
#===============================================================================█    █
#===============================================================================█    █
#===============================================================================█    █
#===============================================================================██████
def run_tts_step0():
    print("\n--- Step 0: Extracting, Cleaning & Formatting Scripts ---")
    file_path = "scripts.eze"

    if not os.path.exists(file_path):
        print(f"    [ERROR] Không tìm thấy file {file_path}")
        step_fail_small_2l()
        return

    # Quy tắc thay thế ưu tiên cao nhất
    MANUAL_REPLACEMENTS = {
        ("35-year-old",): "35 year old",

        ("0-0",): "nil nil",
        ("0-0.",): "nil nil.",
        ("0-0!",): "nil nil!",

        ("1-0",): "one nil",
        ("1-0.",): "one nil.",
        ("1-0!",): "one nil!",
    }

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Tìm TITLE
        title_match = re.search(r'Title\s*:\s*(.*)', content, re.IGNORECASE)
        title_text = title_match.group(1).strip() if title_match else "UNTITLED"

        # 2. Tìm biến scripts
        scripts_match = re.search(r'scripts\s*=\s*"""(.*?)"""', content, re.DOTALL)
        if not scripts_match:
            print(f"    [ERROR] Không tìm thấy biến scripts trong {file_path}")
            step_fail_small_2l()
            return

        # 2. TÌm biến searches
        find_searches_var()

        raw_scripts = scripts_match.group(1).strip()
        lines = raw_scripts.split("\n")

        processed_lines = []

        print(f"    [TITLE] {title_text}")

        # 3. Xử lý từng dòng kịch bản
        for i, line in enumerate(lines, 1):
            line_str = line.strip()
            if not line_str:
                processed_lines.append("")
                continue

            # Chỉ xử lý dòng thoại
            if ":" in line_str and not line_str.startswith("("):
                prefix, body = line_str.split(":", 1)
                line_log = []

                # --- QUY TẮC MỚI: "- A B-C" -> "'A BC'" ---
                special_matches = re.findall(r'(-\s+([a-zA-Z0-9\s\-]+))', body)
                if special_matches:
                    for full_match, content in special_matches:
                        clean_content = content.replace("-", "").strip()
                        new_val = f"'{clean_content}'"

                        body = body.replace(full_match, new_val)
                        line_log.append(f"(Special): '{full_match}'->{new_val}")

                # --- QUY TẮC 2: DẤU NGOẶC (...) -> '...' ---
                bracket_groups = re.findall(r'(\((?!\d+p\d+s)([^)]+)\))', body)

                if bracket_groups:
                    for full_tag, inner_content in bracket_groups:
                        fixed_content = inner_content.replace("-", "")
                        new_tag_val = f"'{fixed_content}'"

                        body = body.replace(full_tag, new_tag_val)
                        line_log.append(f"(bracket): '{full_tag}'->{new_tag_val}")

                # --- QUY TẮC 4: 3.8% -> "3.8" percent ---
                percent_groups = re.findall(r'(\d+(?:\.\d+)?)%', body)

                if percent_groups:
                    for number in percent_groups:
                        old_val = f"{number}%"
                        new_val = f'"{number}" percent'

                        body = body.replace(old_val, new_val)
                        line_log.append(f"(percent): '{old_val}'->'{new_val}'")

                # =====================================================
                # SPLIT PHẢI ĐẶT Ở ĐÂY
                # =====================================================
                words = body.split()

                new_words = []

                for w in words:

                    # --- QUY TẮC 1: Manual ---
                    found_manual = False

                    for key_tuple, replacement in MANUAL_REPLACEMENTS.items():
                        if key_tuple[0].lower() == w.lower():
                            new_words.append(replacement)
                            line_log.append(f"(Manual): '{w}'->'{replacement}'")
                            found_manual = True
                            break

                    if found_manual:
                        continue

                    # --- QUY TẮC 3: A-B -> AB ---
                    if "-" in w:
                        w_fixed = w.replace("-", "")
                        new_words.append(w_fixed)
                        line_log.append(f"(hyphen): '{w}'->'{w_fixed}'")
                        continue

                    new_words.append(w)

                # In báo cáo thay đổi cho dòng này nếu có
                if line_log:
                    print(f"        Line {i:03d}: {', '.join(line_log)}")

                processed_lines.append(f"{prefix}: {' '.join(new_words)}")
            else:
                # Giữ nguyên Section Markers
                processed_lines.append(line_str)

        # 4. Tạo nội dung file scripts.yt
        final_txt = '\n'
        final_txt += "#" + "="*79 + "\n"
        final_txt += f"{title_text.upper()}\n\n"
        final_txt += 'scripts = """\n'
        final_txt += "\n".join(processed_lines)
        final_txt += '\n"""\n'

        with open("scripts.yt", "w", encoding="utf-8") as f:
            f.write(final_txt)
        print(f"    [SUCCESS] scripts.yt created.\n")

        # ======================================================================
        # BƯỚC 5 MỚI: KIỂM TRA DẤU CÂU KẾT THÚC (. HOẶC ?)
        # ======================================================================
        print(f"    [CHECKING] Validating end punctuation in dialogue...")
        punctuation_errors = []
        for idx, line in enumerate(processed_lines, 1):
            if ":" in line and not line.startswith("("):
                # Lấy phần text sau dấu hai chấm
                _, body_text = line.split(":", 1)
                body_text = body_text.strip()

                # Loại bỏ suffix thời gian (nếu có) ví dụ: "(1p2s)" ở cuối câu
                clean_body = re.sub(r'\(?\d+p\d+s\)?$', '', body_text).strip()

                # --- ĐIỀU CHỈNH Ở ĐÂY: Loại bỏ các ký tự không phải dấu câu ở cuối câu ---
                # Loại bỏ bất kỳ dấu ngoặc kép hoặc dấu nháy đơn ở cuối câu trước khi kiểm tra
                clean_body = re.sub(r'[\'"]+$', '', clean_body).strip()
                # ----------------------------------------------------------------------


                # Kiểm tra nếu câu không kết thúc bằng ., ? hoặc !
                if clean_body and not clean_body.endswith(('.', '?', '!')):
                    punctuation_errors.append(f"        Line {idx:03d}: Missing '.', '?' or '!' -> \"{clean_body[-20:]}\"")

        if punctuation_errors:
            print(f"    [WARNING] Found {len(punctuation_errors)} lines missing proper ending punctuation:")
            for err in punctuation_errors:
                print(err)
            print(f"\n")
            print(f"            --> FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL\n\n")
            step_fail_small_2l()
            return
        else:
            print(f"    [OK] All dialogue lines have correct end punctuation.")
            print(f"\n")
            print(f"            --> PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS\n\n")

        # ======================================================================
        # BƯỚC 6 MỚI: CHECK TỪ KHÔNG PHẢI TIẾNG ANH
        # ======================================================================
        print(f"    [CHECKING] Detecting non-English words...")

        def is_english_word(word):
            # Danh sách ngoại lệ (whitelist)
            EXCEPTIONS = {
                "let's", "don't", "doesn't", "didn't", "i'm", "you're", "we're", "they're",
                "it's", "that's", "there's", "what's", "who's", "can't", "won't", "isn't",
                "aren't", "wasn't", "weren't", "haven't", "hasn't", "hadn't", "wouldn't",
                "shouldn't", "couldn't"
            }

            # Normalize dấu nháy cong → thẳng
            word = word.replace("’", "'")

            # 👉 IGNORE timestamp dạng (0p6s), 0p6s, (12p30s)
            if re.match(r'^\(?\d+p\d+s\)?$', word.lower()):
                return True

            # Loại bỏ dấu câu ở đầu/cuối
            word_clean = word.strip(string.punctuation).lower()

            if not word_clean:
                return True

            # Check whitelist trước
            if word_clean in EXCEPTIONS:
                return True

            # Cho phép possessive: teacher's
            if re.match(r"^[a-z]+'s$", word_clean):
                return True

            # Cho phép chữ + dấu '
            if not re.match(r"^[a-z']+$", word_clean):
                return False

            return True

        non_english_words = set()

        for idx, line in enumerate(processed_lines, 1):
            if ":" in line and not line.startswith("("):
                _, body_text = line.split(":", 1)
                words = body_text.strip().split()

                for w in words:
                    if not is_english_word(w):
                        non_english_words.add(w)

        if non_english_words:
            print(f"    --> [WARNING] Found non-English or invalid words ({len(non_english_words)}):")
            for w in sorted(non_english_words):
                print(f"        -> {w}")
            print(f"\n")
            step_fail_small_2l()
        else:
            print(f"    [OK] All words look like English.\n")

    except Exception as e:
        print(f"    [ERROR] {e}")
        step_fail_small_2l()
        return

    # --- PHẦN BACKUP & MOVE FILE (Cập nhật logic theo yêu cầu) ---
    #DATE = datetime.now().strftime("%y%m%d_%H%M%S")
    #backup_dir = Path(r"C:\Users\CPH\Desktop\bk")
    #backup_dir.mkdir(exist_ok=True)

    print("--- Step 0 Finished ---\n")
    step_pass_small_2l()
    printf("\nPLEASE_USE: 'python.exe scripts.py 1' TO RUN NEXT STEP\n")

def remove_img_jpg():
    # 2. Remove img.jpg
    internal_imgs = list(Path('.').glob('img*.jpg'))[:4]
    for img in internal_imgs:
        if os.path.exists(str(img)):
            os.remove(str(img))
            print(f"    [REMOVE] {img.name}")

def find_searches_var():
    source_path = "./scripts.eze"
    output_path = "./searches.yt"

    if not os.path.exists(source_path):
        print(f"    [ERROR] File not found: {source_path}")
        step_fail_small_2l()
        return

    print(f"\n    [PROCESS] Extracting variable 'searches' from {source_path}...")

    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Regex giải thích:
        # (searches\s*=\s*""".*?#end_searches)
        # - searches\s*=\s*""": Tìm đoạn bắt đầu bằng searches = """ (chấp nhận khoảng trắng thừa)
        # - .*?: Lấy toàn bộ nội dung bất kỳ (bao gồm xuống dòng nhờ re.DOTALL)
        # - #end_searches: Tìm đoạn kết thúc
        pattern = r'(searches\s*=\s*""".*?#end_searches)'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            extracted_block = match.group(1)

            # Tạo nội dung file mới với header ngăn cách
            final_content = f"\n#===============================================================================\n{extracted_block}\n"

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_content)

            print(f"    --> [SUCCESS] Saved to: {output_path}\n")
        else:
            print(f"    [WARNING] Block 'searches = ... #end_searches' not found in file!")

    except Exception as e:
        print(f"    [ERROR] An error occurred: {e}")

#===============================================================================   █
#===============================================================================  ██
#===============================================================================   █
#===============================================================================   █
#===============================================================================██████
def run_tts_step1(m_choice=None, w_choice=None, start_from=1):
    """ Chức năng 1: Chuyển đổi văn bản thành giọng nói (TTS)
    m_choice: 1, 2, 0, 9
    w_choice: 1, 2, 0, 9
    start_from: int (bắt đầu từ câu thứ mấy) HOẶC "o<số>" để chỉ chạy 1 câu
    """
    folder = Path("./audio_elabs")

    if folder.exists() and folder.is_dir():
        print(f"\n[INFO] Directory {folder} exists. PLEASE REMOVE IT BY HAND TO CONTINUE.")
    else:
        print(f"\n--- Step 1: TTS Processing (Starting from line {start_from}) ---")
        os.makedirs(output_dir, exist_ok=True)

        # Logic mapping voice theo yêu cầu
        # Man Choice: 1->Man1, 2->Man2, 0->Woman1, 9->Man1
        # Woman Choice: 1->Woman1, 2->Woman2, 0->Man2, 9->Woman2
        mv = {"1":"Man1", "2":"Man2", "0":"Woman1", "9":"Man1"}.get(m_choice, random.choice(["Man1","Man2"]))
        wv = {"1":"Woman1", "2":"Woman2", "0":"Man2", "9":"Woman2"}.get(w_choice, random.choice(["Woman1","Woman2"]))

        session_voices = {"Man": mv, "Woman": wv}
        print(f"    Session Config: Man->{session_voices['Man']}, Woman->{session_voices['Woman']}")

        lines = scripts.strip().split("\n")
        dialogue_counter = 0

        # --- Xử lý biến start_from để hỗ trợ "o<số>" ---
        run_single_line = False
        if isinstance(start_from, str) and start_from.lower().startswith("o"):
            try:
                # Cố gắng chuyển phần số của chuỗi thành int
                target_line_num = int(start_from[1:])
                run_single_line = True
                start_from = target_line_num # Đặt start_from thành số dòng cần chạy
                print(f"    [MODE] Running only line {target_line_num}.")
            except ValueError:
                print(f"    [WARNING] Invalid format for single-line run: '{start_from}'. Defaulting to normal run from line 1.")
                start_from = 1
        # ---------------------------------------------------

        for line in lines:
            line = line.strip()
            # Thêm kiểm tra: Phần sau dấu hai chấm phải có chữ mới xử lý
            if not line or line.startswith("(") or ":" not in line or not line.split(":", 1)[1].strip():
                continue

            dialogue_counter += 1

            # KIỂM TRA START INDEX
            if dialogue_counter < start_from:
                print(f"    [Skip] Line {dialogue_counter:02d}")
                continue

            # --- Logic dừng sau khi chạy một câu nếu run_single_line là True ---
            if run_single_line and dialogue_counter > start_from:
                print(f"    [INFO] Finished running single line {start_from}. Exiting.")
                break # Thoát khỏi vòng lặp sau khi đã xử lý câu mong muốn
            # -----------------------------------------------------------------

            # Regex để tách: 0p6s_ (prefix), Man_Q (speaker), text và (1p2s) (suffix)
            main_match = re.match(r"(?P<pre>\d+p\d+s_)?(?P<spk>[^:]+):(?P<txt>.+)", line)
            if not main_match: continue

            speaker_full = main_match.group("spk").strip()
            text_raw = main_match.group("txt").strip()

            # Xóa suffix thời gian (nếu có) khỏi text gửi lên AI
            clean_text = re.sub(r"\(\d+p\d+s\)", "", text_raw).strip()

            gender_prefix = speaker_full.split("_")[0]
            tone = speaker_full.split("_")[1] if "_" in speaker_full else "N"

            chosen_speaker = session_voices.get(gender_prefix, gender_prefix)

            voice_id = VOICE_MAP[chosen_speaker]["voice_id"]

            # random stability theo tone
            if tone in STABILITY_MAP:
                low, high = STABILITY_MAP[tone]
                stability = round(random.uniform(low, high), 2)
            else:
                stability = 0.4

            # Random thêm speed (nghe tự nhiên hơn)
            speed = round(random.uniform(0.7, 0.75), 2)

            style = STYLE_MAP.get(tone, 0.1)

            print(f"    [{chosen_speaker}_{tone}] text={clean_text}")
            print(f"    [{chosen_speaker}_{tone}] voice_id={voice_id}")
            print(f"    [{chosen_speaker}_{tone}] stability={stability}")
            print(f"    [{chosen_speaker}_{tone}] speed={speed}")
            print(f"    [{chosen_speaker}_{tone}] style={style}")

            print(f"    [{dialogue_counter:02d}] Generating {chosen_speaker} for: {clean_text[:30]}...")

            try:
                audio = client.text_to_speech.convert(
                    text=clean_text,
                    voice_id=voice_id,
                    model_id="eleven_multilingual_v2",
                    output_format="mp3_44100_128",
                    voice_settings={
                        "stability": stability,
                        "similarity_boost": 0.75,
                        "style": style,
                        "use_speaker_boost": True,
                        "speed": speed
                    }
                )

                # 5. Lưu file
                safe_text = re.sub(r'[^a-zA-Z0-9]+', '_', clean_text).strip('_')[:50] # Giới hạn 50 ký tự cho ngắn
                file_name = f"{dialogue_counter:03d}_{chosen_speaker}_{tone}_{safe_text}.mp3"
                file_path = os.path.join(output_dir, file_name)

                with open(file_path, "wb") as f:
                    # Nếu audio là generator/stream
                    if hasattr(audio, "__iter__"):
                        for chunk in audio:
                            if chunk: f.write(chunk)
                    else:
                        f.write(audio)

                print(f"        [SAVED] {file_name}")

            except Exception as e:
                print(f"    [ERROR] at line {dialogue_counter}: {e}")
                return

        print("--- Step 1 Finished ---\n")
        step_pass_small_2l()
        printf("\nPLEASE_USE: 'python.exe scripts.py 2' TO RUN NEXT STEP\n")

#===============================================================================██████
#===============================================================================     █
#===============================================================================██████
#===============================================================================█
#===============================================================================██████
def run_ffmpeg_step2():
    """Chức năng 2: Quét folder audio_elabs và xử lý FFmpeg"""
    folder = Path("./audio_ffmpeg")

    if folder.exists() and folder.is_dir():
        print(f"\n[INFO] Directory {folder} exists. PLEASE REMOVE IT BY HAND TO CONTINUE.")
    else:
        print("\n--- Step 2: EQ & Mastering ---")

        if not os.path.exists(output_dir):
            print(f"    [ERROR] Directory {output_dir} does not exist.")
            return

        os.makedirs(processed_dir, exist_ok=True)

        # Lấy danh sách file và SẮP XẾP (Sorted)
        files = sorted([f for f in os.listdir(output_dir) if f.endswith(".mp3")])

        if not files:
            print("    [ERROR] NO .mp3 files found to process.")
            return

        for file_name in files:
            input_path = os.path.join(output_dir, file_name)
            output_path = os.path.join(processed_dir, file_name)

            # Dùng "Man" hay "Woman" trong tên file để áp dụng filter
            if "Man" in file_name:
                filter_cmd = ("anoisesrc=color=white:amplitude=0.0003 [n]; [0:a][n] amix=inputs=2:duration=first, "
                              "acompressor=threshold=-18dB:ratio=2:attack=5:release=100, "
                              "equalizer=f=100:t=q:w=1:g=3, equalizer=f=200:t=q:w=1:g=2, "
                              "equalizer=f=8000:t=q:w=1:g=-2, loudnorm=I=-14:TP=-3:LRA=11")
            elif "Woman" in file_name:
                filter_cmd = ("anoisesrc=color=white:amplitude=0.00025 [n]; [0:a][n] amix=inputs=2:duration=first, "
                              "acompressor=threshold=-18dB:ratio=2:attack=5:release=100, "
                              "equalizer=f=100:t=q:w=1:g=-2, equalizer=f=3000:t=q:w=1:g=3, "
                              "equalizer=f=5000:t=q:w=1:g=2, loudnorm=I=-14:TP=-3:LRA=11")
            else:
                print(f"    --> [ERROR] (gender unknown): {file_name}")
                return

            # Lệnh FFmpeg
            #command = ["ffmpeg", "-y", "-i", input_path, "-af", filter_cmd, output_path]
            command = [
                "ffmpeg", "-y",
                "-i", input_path,
                "-af", filter_cmd,
                "-c:a", "libmp3lame", "-b:a", "192k", # Đảm bảo chất lượng đầu ra
                output_path
            ]

            try:
                # Dùng subprocess.run với capture_output để dễ debug nếu lỗi
                result = subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                print(f"    --> [SUCCESS] {file_name}")
            except subprocess.CalledProcessError as e:
                # In lỗi chi tiết từ FFmpeg nếu có
                error_msg = e.stderr.decode() if e.stderr else str(e)
                print(f"    --> [ERROR] processing {file_name}: {error_msg}")
                return

        print("--- Step 2 Finished ---\n")
        step_pass_small_2l()
        printf("\nPLEASE_USE: 'python.exe scripts.py 3 0.80 2 5' TO RUN NEXT STEP\n")

#===============================================================================██████
#===============================================================================     █
#===============================================================================██████
#===============================================================================     █
#===============================================================================██████
def run_silent_step3(speed=0.8, gap_sec=2.0, gap_bye=5.0):
    folder = Path("./audio_ffmpegs")

    if folder.exists() and folder.is_dir():
        print(f"\n[INFO] Directory {folder} exists. PLEASE REMOVE IT BY HAND TO CONTINUE.")
    else:
        print(f"\n--- Step 3: Mastering Final Audio (Strict 4-Part Logic) ---")
        if not scripts or not os.path.exists(processed_dir):
            print("    [ERROR] The script is empty or the processing directory does not exist.")
            return

        os.makedirs(silent_dir, exist_ok=True)
        lines_all = [l.strip() for l in scripts.strip().split("\n") if l.strip()]

        # Lấy danh sách các dòng thoại thực tế để map với file index 001, 002...
        valid_dialogue_lines = [l for l in lines_all if ":" in l and not l.startswith("(")]

        # 1. Chèn Silent cục bộ (mp3 -> wav) cho từng câu đơn
        processed_fragments = []
        for i, line in enumerate(valid_dialogue_lines, 1):
            pre_m = re.match(r"(\d+p\d+s)_", line)
            post_m = re.search(r"\((\d+p\d+s)\)", line)

            ms_start = parse_to_ms(pre_m.group(1)) if pre_m else 500
            sec_end = float(parse_to_ms(post_m.group(1))/1000) if post_m else 0

            matching = [f for f in os.listdir(processed_dir) if f.startswith(f"{i:03d}_")]
            if not matching: continue

            in_a = os.path.join(processed_dir, matching[0])
            out_a = os.path.join(silent_dir, os.path.splitext(matching[0])[0] + ".wav")
            filter_str = f"adelay={ms_start}:all=1"
            if sec_end > 0: filter_str += f",apad=pad_dur={sec_end}"
            filter_str += ",areverse,afade=t=in:st=0:d=0.2,areverse"

            subprocess.run(["ffmpeg", "-y", "-i", in_a, "-af", filter_str, "-acodec", "pcm_s16le", out_a], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            processed_fragments.append(out_a)

        # 2. Phân nhóm vào 4 Hũ dựa trên Marker CHÍNH XÁC
        sections_map = {"1_HOOK": [], "2_INFO_START": [], "3_MAIN": [], "4_BYE": []}
        current_state = "1_HOOK"
        v_idx = 0

        for line in lines_all:
            l_cmd = line.upper()

            # CHỈ chuyển trạng thái nếu dòng là từ khóa đứng độc lập
            if l_cmd in ["INFO", "START"]: current_state = "2_INFO_START"
            elif l_cmd in ["MAIN", "(MAIN)"]: current_state = "3_MAIN"
            elif l_cmd in ["BYE", "GOODBYE"]: current_state = "4_BYE"
            elif l_cmd == "HOOK": current_state = "1_HOOK"

            # Nếu dòng này chứa thoại (có dấu :) và không phải chú thích (dấu ngoặc)
            if ":" in line and not line.startswith("("):
                if v_idx < len(processed_fragments):
                    sections_map[current_state].append(processed_fragments[v_idx])
                    v_idx += 1

        # 3. Xuất file phân đoạn
        speed_suffix = str(speed).replace('.', 'p')
        master_base = "anoisesrc=color=white:amplitude=0.0005:duration=1 [n]; [0:a][n] amix=inputs=2:duration=first:dropout_transition=0, acompressor=threshold=-18dB:ratio=2:attack=5:release=100:makeup=2dB, loudnorm=I=-14:TP=-1:LRA=11"
        list_txt = os.path.join(silent_dir, "list_tmp.txt")
        section_files_with_gap = []

        for sec_name in ["1_HOOK", "2_INFO_START", "3_MAIN", "4_BYE"]:
            files = sections_map[sec_name]
            if not files: continue

            pad_dur = gap_bye if "BYE" in sec_name else gap_sec
            out_name = f"{sec_name}_{speed_suffix}.wav"
            out_p = os.path.join(silent_dir, out_name)

            with open(list_txt, "w", encoding="utf-8") as f:
                for pf in files:
                    # Sửa lỗi Syntax: replace nằm ngoài f-string
                    p_abs = os.path.abspath(pf).replace('\\', '/')
                    f.write(f"file '{p_abs}'\n")

            filter_complex = f"{master_base}, atempo={speed}, apad=pad_dur={pad_dur}"
            subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_txt, "-filter_complex", filter_complex, "-acodec", "pcm_s16le", out_p], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            section_files_with_gap.append(out_p)
            print(f"    --> [CREATED] {out_name} (Gap: {pad_dur}s | Lines: {len(files)})")

        # 4. Tạo file tổng final_audio.wav
        final_name = f"final_audio_{speed_suffix}.wav" if speed != 1.0 else "final_audio.wav"
        final_p = os.path.join(silent_dir, final_name)
        with open(list_txt, "w", encoding="utf-8") as f:
            for ps in section_files_with_gap:
                p_ps = os.path.abspath(ps).replace('\\', '/')
                f.write(f"file '{p_ps}'\n")

        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_txt),
            "-c", "copy", final_p
        ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

        if os.path.exists(list_txt): os.remove(list_txt)
        print(f"    --> [MASTER SUCCESS] {final_name}")

        print("--- Step 3 Finished ---\n")
        step_pass_small_2l()
        printf("\nPLEASE_USE: 'python.exe scripts.py 4' TO RUN NEXT STEP\n")

#===============================================================================█    █
#===============================================================================█    █
#===============================================================================██████
#===============================================================================     █
#===============================================================================     █
def run_srt_step4():
    print(f"\n--- Step 4: Transcribing (Hie: 0=1f/9f, anchored to 0) & Script-Based Alignment ---")
    global first_sound_time

    # 1. Tìm audio
    audio_pattern = os.path.join(silent_dir, "final_audio*.wav")
    all_final_wavs = [f for f in glob.glob(audio_pattern) if not any(x in f for x in ["HOOK", "INFO", "MAIN", "BYE", "START"])]
    if not all_final_wavs: return
    audio_path = max(all_final_wavs, key=os.path.getmtime)

    # 2. Phân tích Waveform
    activity = get_audio_activity(audio_path, threshold=500)

    # Dò điểm có tiếng đầu tiên (Ultra-sensitive)
    cmd_start = ['ffmpeg', '-i', audio_path, '-t', '2', '-f', 's16le', '-ac', '1', '-ar', '16000', '-']
    proc = subprocess.Popen(cmd_start, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    raw_head = proc.stdout.read()
    proc.terminate()

    if raw_head:
        samples_head = struct.unpack(f"<{len(raw_head)//2}h", raw_head)
        for s_idx, val in enumerate(samples_head):
            if abs(val) > 100:
                first_sound_time = s_idx / 16000.0
                break

    # 3. Whisper Transcription
    model = stable_whisper.load_model("small")

    def run_whisper(audio_path_inner):
        result = model.transcribe(audio_path_inner, fp16=False, vad=True, language='en', suppress_silence=True)
        return result.to_dict()

    result = get_whisper_result(audio_path, run_whisper)

    # Thu thập TẤT CẢ các từ từ Whisper thành 1 danh sách phẳng
    all_whisper_words = []
    for seg in result.segments:
        for w in seg.words:
            all_whisper_words.append({'word': w.word, 'start': w.start, 'end': w.end})

    # 4. CHUẨN BỊ DỮ LIỆU TỪ KỊCH BẢN (Giống Step 5)
    def expand_symbols(text):
        text = re.sub(r'\$(\d+(?:\.\d+)?)\s*b(illion)?', r'\1 billion dollars', text, flags=re.I)
        text = re.sub(r'\$(\d+(?:\.\d+)?)\s*m(illion)?', r'\1 million dollars', text, flags=re.I)
        text = re.sub(r'\$(\d+(?:\.\d+)?)', r'\1 dollars', text)
        text = text.replace("%", " percent").replace("-", " ")
        return text

    script_lines_data = [] # Chứa danh sách các từ của từng dòng thoại
    full_script_word_list = [] # Danh sách phẳng để so khớp

    lines = scripts.strip().split("\n")
    for line in lines:
        if ":" in line and not line.startswith("("):
            _, txt = line.split(":", 1)
            # Loại bỏ tag (0p5s) và expand symbols
            clean_txt = expand_symbols(re.sub(r"\(.*?\)", "", txt)).strip()
            line_words = clean_txt.split()
            if line_words:
                script_lines_data.append(line_words)
                for lw in line_words:
                    full_script_word_list.append(re.sub(r'[^\w]', '', lw).lower())

    # 5. SO KHỚP (ALIGNMENT)
    whisper_clean = [re.sub(r'[^\w]', '', w['word']).lower() for w in all_whisper_words]
    matcher = difflib.SequenceMatcher(None, whisper_clean, full_script_word_list)

    # Tạo pool chứa các từ whisper đã khớp vào vị trí kịch bản
    mapped_word_pool = [None] * len(full_script_word_list)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1):
                mapped_word_pool[j1 + k] = all_whisper_words[i1 + k]
        elif tag == 'replace':
            # Trường hợp Whisper nghe sai từ nhưng đúng vị trí (ví dụ: "Iran." vs "Iran")
            # Map 1-1 nếu số lượng từ tương đồng
            size = min(i2-i1, j2-j1)
            for k in range(size):
                mapped_word_pool[j1 + k] = all_whisper_words[i1 + k]

    # 6. NHÓM LẠI THEO DÒNG KỊCH BẢN
    sentences_list = []
    current_ptr = 0
    for line_words in script_lines_data:
        group = []
        for _ in range(len(line_words)):
            if current_ptr < len(mapped_word_pool):
                w_obj = mapped_word_pool[current_ptr]
                if w_obj:
                    group.append(w_obj)
                current_ptr += 1

        if not group:
            print(f"    [ERROR] Câu kịch bản không tìm thấy âm thanh tương ứng: {' '.join(line_words[:5])}...")
            return
        else:
            sentences_list.append(group)

    # Kiểm tra số lượng câu
    if len(sentences_list) != len(script_lines_data):
        print(f"    [ERROR] Số lượng câu không khớp! Script: {len(script_lines_data)}, Audio Detect: {len(sentences_list)}")
        return

    dummy = "1\n00:00:00,000 --> 00:00:00,100\n    \n\n"

    # --- XUẤT FILE 0 (Dùng detect_precise_timing như cũ) ---
    opt0 = detect_precise_timing(sentences_list)
    with open(os.path.join(silent_dir, "fin_aud_0.srt"), "w", encoding="utf-8") as f:
        f.write(dummy)
        for idx, item in enumerate(opt0, 2):
            f.write(f"{idx}\n{format_timestamp(item['start'])} --> {format_timestamp(item['end'])}\n{item['text']}\n\n")

    printf("\n")
    print(f"            --> PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS\n\n")
    print(f"    --> [SUCCESS] fin_aud_0.srt aligned with script structure.")
    printf("\n")

    # convert SRT to TEXT
    process_srt_visualize(silent_dir, "fin_aud_0.srt", "fin_aud_0.txt")

    print("--- Step 4 Finished ---\n")
    step_pass_small_2l()
    printf("\nPLEASE_USE: 'python.exe scripts.py 5' TO RUN NEXT STEP\n")

#===============================================================================██████
#===============================================================================█
#===============================================================================██████
#===============================================================================     █
#===============================================================================██████
def run_srt_step5():
    print(f"\n--- Step 5: 100% Script Sync & Detailed Alignment Report (with Migration) ---")

    srt_path = os.path.join(silent_dir, "fin_aud_0.srt")
    if not os.path.exists(srt_path):
        print(f"    [ERROR] Not found {srt_path}")
        return

    # 1. BỘ TỪ ĐIỂN NỞ RỘNG
    def expand_all_symbols(text):
        text = re.sub(r'\$(\d+(?:\.\d+)?)\s*b(illion)?', r'\1 billion dollars', text, flags=re.I)
        text = re.sub(r'\$(\d+(?:\.\d+)?)\s*m(illion)?', r'\1 million dollars', text, flags=re.I)
        text = re.sub(r'\$(\d+(?:\.\d+)?)', r'\1 dollars', text)
        text = text.replace("%", " percent")
        text = text.replace("-", " ")
        return text

    all_script_words_info = []
    lines = scripts.strip().split("\n")
    for line in lines:
        if ":" in line and not line.startswith("("):
            spk, txt = line.split(":", 1)
            is_man = "Man" in spk
            clean_txt = expand_all_symbols(re.sub(r"\(.*?\)", "", txt))
            for w in clean_txt.split():
                all_script_words_info.append({"word": w, "is_man": is_man})

    # 2. ĐỌC WHISPER GỐC
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    blocks_raw = re.findall(r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n((?:.+\n?)+)", content)

    srt_word_pool = []
    for b_idx, block in enumerate(blocks_raw):
        if block[0] == "1": continue
        for w in block[2].strip().split():
            srt_word_pool.append({"word": w, "b_idx": b_idx, "ts": block[1].split(" --> ")[0]})

    # 3. SO KHỚP VÀ BÁO CÁO CHI TIẾT
    buckets = {b_idx: [] for b_idx in range(len(blocks_raw))}
    script_clean = [re.sub(r'[^\w]', '', x["word"]).lower() for x in all_script_words_info]
    srt_clean = [re.sub(r'[^\w]', '', x["word"]).lower() for x in srt_word_pool]

    matcher = difflib.SequenceMatcher(None, srt_clean, script_clean)

    print(f"{'TYPE':<10} | {'DETAILS'}")
    print("-" * 110)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1):
                w_wh = srt_word_pool[i1 + k]
                w_sc = all_script_words_info[j1 + k]
                buckets[w_wh["b_idx"]].append({"word": w_sc["word"], "is_man": w_sc["is_man"]})
                print(f"[MATCH]      | whisper: {w_wh['word']:<12} -> ORG: {w_sc['word']:<12} -> correct: {w_sc['word']:<12} -> TS {w_wh['b_idx']+1:>2} -> {w_wh['ts']}")

        elif tag == 'replace':
            w_wh_chunk = srt_word_pool[i1:i2]
            w_sc_chunk = all_script_words_info[j1:j2]
            for k, w_sc in enumerate(w_sc_chunk):
                ref = w_wh_chunk[min(k, len(w_wh_chunk)-1)]
                buckets[ref["b_idx"]].append({"word": w_sc["word"], "is_man": w_sc["is_man"]})
                w_name = w_wh_chunk[k]["word"] if k < len(w_wh_chunk) else "[SPLIT]"
                print(f"[REPLACE]    | whisper: {w_name:<12} -> ORG: {w_sc['word']:<12} -> correct: {w_sc['word']:<12} -> TS {ref['b_idx']+1:>2} -> {ref['ts']}")

        elif tag == 'insert':
            ref = srt_word_pool[i1] if i1 < len(srt_word_pool) else srt_word_pool[-1]
            for w_sc in all_script_words_info[j1:j2]:
                buckets[ref["b_idx"]].append({"word": w_sc["word"], "is_man": w_sc["is_man"]})
                print(f"[INSERT]     | whisper: {'[MISSING]':<12} -> ORG: {w_sc['word']:<12} -> correct: {w_sc['word']:<12} -> TS {ref['b_idx']+1:>2} -> {ref['ts']}")

        elif tag == 'delete':
            for w_wh in srt_word_pool[i1:i2]:
                print(f"[DELETE]     | whisper: {w_wh['word']:<12} -> ORG: {'[EXTRA]':<12} -> correct: {'[REMOVED]':<12} -> TS {w_wh['b_idx']+1:>2} -> {w_wh['ts']}")

    # 4. THUẬT TOÁN HÀN GẮN (Suffixes)
    STICKY_SUFFIXES = ["dollars", "dollar", "percent", "old", "billion", "million", "cents", "cent"]
    for b_idx in range(len(blocks_raw) - 1, 1, -1):
        if buckets[b_idx]:
            first_w_obj = buckets[b_idx][0]
            if re.sub(r'[^\w]', '', first_w_obj["word"]).lower() in STICKY_SUFFIXES:
                moved = buckets[b_idx].pop(0)
                buckets[b_idx-1].append(moved)
                print(f"[HEAL]       | Moving '{moved['word']}' from TS {b_idx+1} back to {b_idx} (Sticky Suffix)")

    # ===================================================
    # 5. GIẢI THUẬT DI CƯ (Fix lỗi "Hmm" dính vào người trước)
    # ===================================================
    for b_idx in range(len(blocks_raw) - 1):
        curr_words = buckets[b_idx]
        next_words = buckets[b_idx + 1]
        if not curr_words or not next_words: continue

        while len(curr_words) > 1:
            last_w = curr_words[-1]
            first_w = curr_words[0]
            target_first_w = next_words[0]

            # Nếu từ cuối khác giới tính với từ đầu block hiện tại, nhưng giống giới tính block sau
            if last_w["is_man"] != first_w["is_man"] and last_w["is_man"] == target_first_w["is_man"]:
                moved = curr_words.pop(-1)
                buckets[b_idx + 1].insert(0, moved)
                print(f"[MIGRATE]    | Moving '{moved['word']}' from Block {b_idx+1} forward to {b_idx+2} (Speaker Match)")
            else:
                break

    # 6. XUẤT FILE SRT
    final_blocks = []
    MARKER_MAN, MARKER_WOMAN = "\u200B", "\u200C"
    for b_idx, block in enumerate(blocks_raw):
        idx_val, timeframe, _ = block
        if idx_val == "1":
            final_blocks.append(f"1\n{timeframe}\n    ")
            continue

        words_info = buckets[b_idx]
        if not words_info:
            final_blocks.append(f"{idx_val}\n{timeframe}\n...")
            continue

        # Xác định giới tính block dựa trên đa số từ
        man_count = sum(1 for w in words_info if w["is_man"])
        is_man_block = man_count > (len(words_info) / 2)

        sync_text = " ".join([w["word"] for w in words_info]).strip()
        marker = MARKER_MAN if is_man_block else MARKER_WOMAN
        final_blocks.append(f"{idx_val}\n{timeframe}\n{sync_text + marker}")

    out_p = os.path.join(silent_dir, "fin_aud_0_cor.srt")
    with open(out_p, "w", encoding="utf-8") as f:
        f.write("\n\n".join(final_blocks) + "\n\n")

    print("-" * 110)
    print(f"    --> [SUCCESS] Created {out_p}")

    # convert SRT to TEXT
    duong_dan = "./audio_ffmpegs"
    ten_file_in = "fin_aud_0_cor.srt"
    ten_file_out = "fin_aud_0_cor.txt"
    process_srt_visualize(duong_dan, ten_file_in, ten_file_out)
    print(f"    --> [CREATED] {ten_file_in}")

    # ===================================================
    # 7. BÁO CÁO VÀ KIỂM TRA SỐ LƯỢNG CÂU (FINAL REPORT)
    # ===================================================
    print(f"\n    {'='*30} COUNT REPORT {'='*30}")

    # Đếm câu trong Scripts (Chỉ đếm các dòng thoại thực tế)
    count_script = 0
    for line in scripts.strip().split("\n"):
        if ":" in line and not line.startswith("("):
            count_script += 1

    # Đếm câu trong file 0.srt (Trừ đi 1 block mỏ neo dummy)
    count_srt_0 = len(blocks_raw) - 1

    # Đếm câu trong file 0_cor.srt (Trừ đi 1 block mỏ neo dummy)
    count_srt_correct = len(final_blocks) - 1

    print(f"    [1] Total dialogues in Scripts      : {count_script}")
    print(f"    [2] Total blocks in 0.srt           : {count_srt_0}")
    print(f"    [3] Total blocks in 0_cor.srt   : {count_srt_correct}")

    # Kiểm tra sai lệch
    if count_script != count_srt_correct:
        print(f"    [ERROR] Script count ({count_script}) does not match Final SRT count ({count_srt_correct})!")
        return

    if count_srt_0 != count_srt_correct:
        print(f"    [ERROR] Original Whisper count ({count_srt_0}) mismatch with Corrected count ({count_srt_correct})!")
        return

    print(f"    VERIFICATION SUCCESS: All dialogue counts are perfectly synced (Total: {count_script})")
    print(f"\n\n            --> PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS\n\n")
    print(f"    {'='*74}\n")

    print("--- Step 5 Finished ---\n")
    step_pass_small_2l()
    printf("\nPLEASE_USE: 'python.exe scripts.py 6 nword' TO RUN NEXT STEP\n")

#===============================================================================██████
#===============================================================================█
#===============================================================================██████
#===============================================================================█    █
#===============================================================================██████
def run_srt_step6(nword=6):
    nword = int(nword)
    print(f"\n--- Step 6: Advanced SRT Splitting (VDA + Comma + Proper Noun Protection) ---")
    print(f"    [CONFIG] nword set to: {nword}")

    silent_dir = Path("./audio_ffmpegs")
    if not silent_dir.exists():
        os.makedirs(silent_dir, exist_ok=True)

    in_path = os.path.join(silent_dir, "fin_aud_0_cor.srt")
    out_path = os.path.join(silent_dir, "fin_aud_1.srt")

    audio_files = glob.glob(os.path.join(silent_dir, "final_audio*.wav"))
    if not audio_files:
        print(f"    [ERROR] No final_audio*.wav found in {silent_dir}")
        return
    audio_path = audio_files[0]

    if not os.path.exists(in_path):
        print(f"    [ERROR] Not found {in_path}")
        return

    # --- HÀM HỖ TRỢ VDA: TÌM KHOẢNG LẶNG TRONG ĐOẠN ---
    def find_best_gap(start_sec, end_sec, target_ratio):
        """
        Dò trong dữ liệu 'activity' toàn cục để tìm điểm im lặng gần với vị trí target_ratio nhất
        target_ratio: 0.5 là chính giữa câu, 0.33 là 1/3 câu...
        """
        global activity
        if not activity:
            print(f"    [DEBUG] Activity data is empty, returning simple ratio split for VDA.")
            return start_sec + (end_sec - start_sec) * target_ratio

        idx_s = int(start_sec * 100)
        idx_e = int(end_sec * 100)
        target_idx = idx_s + int((idx_e - idx_s) * target_ratio)

        search_range = 50
        best_gap_idx = target_idx
        min_dist = 9999

        found = False
        # Đảm bảo không tìm ngoài biên của activity
        for i in range(max(idx_s + 5, target_idx - search_range), min(len(activity), idx_e - 5, target_idx + search_range)):
            if activity[i]['active'] == 0:
                dist = abs(i - target_idx)
                if dist < min_dist:
                    min_dist = dist
                    best_gap_idx = i
                    found = True

        result_gap_time = best_gap_idx / 100.0 if found else (start_sec + (end_sec - start_sec) * target_ratio)
        return result_gap_time

    def is_proper_noun(w):
        clean = re.sub(r'[^\w]', '', w)
        return clean and clean[0].isupper()

    # --- HÀM HỖ TRỢ: CHIA ĐOẠN KHI KHÔNG CÓ DẤU PHẨY (hoặc đã quyết định bỏ qua dấu phẩy) ---
    # Hàm này giờ nhận một danh sách từ và chia nhỏ nó theo các quy tắc >2*nword và >nword
    def split_no_comma_logic(words_list_for_splitting):
        L = len(words_list_for_splitting)
        print(f"    [DEBUG - split_no_comma_logic] Called with {L} words: '{' '.join(words_list_for_splitting[:10])}{'...' if L > 10 else ''}'")

        if L <= nword:
            print(f"    [DEBUG - split_no_comma_logic]   -> Length ({L}) <= nword ({nword}), returning as single segment.")
            return [words_list_for_splitting]

        segments = []
        current_idx = 0

        while current_idx < L:
            remaining_len = L - current_idx

            if remaining_len > 2 * nword: # + nếu không có "," thì xét nếu > 2*nword word thì tách thành nhóm nword trước, phần còn lại lại xét tiếp theo nhóm nword
                split_point = current_idx + nword
                print(f"    [DEBUG - split_no_comma_logic]   -> Remaining > 2*nword ({remaining_len} > {2*nword}). Cutting {nword} words.")
            elif remaining_len > nword: # + nếu > nword word thì chia thành 2 nhóm
                split_point = current_idx + remaining_len // 2
                print(f"    [DEBUG - split_no_comma_logic]   -> Remaining > nword ({remaining_len} > {nword}). Cutting into two halves.")

                # Ưu tiên bảo vệ tên riêng (chỉ khi chia đôi)
                # Kiểm tra từ tại split_point và từ trước nó
                # Nếu cả hai đều là Proper Noun, cố gắng dịch điểm cắt
                original_split_point = split_point
                if split_point > current_idx and split_point < L: # Đảm bảo split_point hợp lệ
                    if is_proper_noun(words_list_for_splitting[split_point-1]) and is_proper_noun(words_list_for_splitting[split_point]):
                        # Cố gắng dịch sang phải (sau cả cặp tên riêng)
                        if split_point + 1 < L and (L - (split_point + 1)) >= (remaining_len // 2) - 1: # Đảm bảo phần còn lại không quá ngắn
                            split_point += 1
                        # Nếu không thể, thử dịch sang trái (trước cả cặp tên riêng)
                        elif split_point - 1 > current_idx and (split_point - 1 - current_idx) >= (remaining_len // 2) - 1: # Đảm bảo phần cắt ra không quá ngắn
                            split_point -= 1

                        if split_point != original_split_point:
                            print(f"    [DEBUG - split_no_comma_logic]     -> Adjusted split_point from {original_split_point} to {split_point} to protect Proper Nouns.")

            else: # Phần còn lại <= nword, thêm vào đoạn cuối
                split_point = L # Đặt split_point là cuối cùng để lấy hết phần còn lại
                print(f"    [DEBUG - split_no_comma_logic]   -> Remaining <= nword ({remaining_len} <= {nword}). Taking all remaining words.")

            # Đảm bảo split_point hợp lệ (ít nhất 1 từ trong segment và không vượt quá giới hạn)
            split_point = max(current_idx + 1, min(split_point, L))

            # Gộp đoạn cuối quá ngắn vào đoạn trước đó nếu có
            # Nếu chỉ còn lại một đoạn nhỏ (ví dụ < nword/2) và có đoạn trước để gộp
            if (L - split_point) > 0 and (L - split_point) < (nword // 2) and len(segments) > 0:
                print(f"    [DEBUG - split_no_comma_logic]   -> Remaining words ({L - split_point}) too small, merging with previous segment.")
                segments[-1].extend(words_list_for_splitting[current_idx:])
                current_idx = L # Đánh dấu là đã xử lý hết
                break # Thoát vòng lặp

            segments.append(words_list_for_splitting[current_idx : split_point])
            current_idx = split_point

            print(f"    [DEBUG - split_no_comma_logic]   -> Added segment ({len(segments[-1])} words). Next start index: {current_idx}. Current segments count: {len(segments)}")

        print(f"    [DEBUG - split_no_comma_logic]   -> Final segments for this call: {[len(s) for s in segments]} words.")
        return segments


    # --- LOGIC CHIA ĐOẠN THEO USER (chính) ---
    def get_split_segments(words):
        L = len(words)
        print(f"\n    [DEBUG - get_split_segments] Processing original block words (len={L}): '{' '.join(words[:15])}{'...' if L > 15 else ''}'")

        # 1. Nếu câu có số lượng word <= nword thì giữ nguyên câu
        if L <= nword:
            print(f"    [DEBUG - get_split_segments]   -> Length ({L}) <= nword ({nword}), returning as single segment.")
            return [words]

        comma_indices = [i for i, w in enumerate(words) if "," in w and i < L - 1]
        print(f"    [DEBUG - get_split_segments]   -> Comma indices: {comma_indices}")

        # Danh sách để lưu các segment cuối cùng sau khi xử lý
        final_segments_result = []

        # Xử lý khi CÓ dấu phẩy
        if comma_indices:
            raw_segments = []
            prev = 0
            for idx in comma_indices:
                raw_segments.append(words[prev:idx+1])
                prev = idx + 1
            raw_segments.append(words[prev:])

            print(f"    [DEBUG - get_split_segments]   -> Initial raw segments based on commas: {[len(s) for s in raw_segments]} words.")

            # * nếu có đoạn 1/2 word thì xem như câu ko có "," và chi theo câu có số lượng word > nword
            for seg in raw_segments:
                if len(seg) <= 2:
                    print(f"    [DEBUG - get_split_segments]   -> Found small segment (len {len(seg)} <= 2) in raw_segments. Treating as no commas. Calling split_no_comma_logic for whole original sentence.")
                    return split_no_comma_logic(words) # Chuyển toàn bộ câu gốc cho split_no_comma_logic

            # + nếu trong câu có "," chia câu thành 2 đoạn
            if len(raw_segments) == 2:
                seg1, seg2 = raw_segments[0], raw_segments[1]
                print(f"    [DEBUG - get_split_segments]   -> Handling 2 raw segments: Seg1 (len={len(seg1)}), Seg2 (len={len(seg2)})")

                # Sau khi tách, mỗi đoạn sẽ được xét tiếp theo nword word
                final_segments_result.extend(split_no_comma_logic(seg1))
                final_segments_result.extend(split_no_comma_logic(seg2))
                return final_segments_result

            # + nếu trong câu có "," chia câu thành 3 đoạn (1, 2, 3) (hoặc nhiều hơn 3, gộp lại thành 3)
            if len(raw_segments) >= 3:
                seg1 = raw_segments[0]
                seg2 = raw_segments[1]
                seg3_combined = []
                for s in raw_segments[2:]: # Gộp tất cả các đoạn từ thứ 3 trở đi vào seg3_combined
                    seg3_combined.extend(s)
                seg3 = seg3_combined

                print(f"    [DEBUG - get_split_segments]   -> Handling 3+ raw segments: Seg1 (len={len(seg1)}), Seg2 (len={len(seg2)}), Seg3 (len={len(seg3)})")

                # * nếu 2 <= 2*nword thì gọp vào 1 nếu sl word 1 < sl word 3, gọp vào 3 nếu sl word 3 < sl word 1
                if len(seg2) <= 2 * nword:
                    print(f"    [DEBUG - get_split_segments]     -> Seg2 (len={len(seg2)}) <= 2*nword ({2*nword}). Applying merge logic for Seg2.")
                    if len(seg1) < len(seg3): # Gộp seg2 vào seg1
                        seg1.extend(seg2)
                        print(f"    [DEBUG - get_split_segments]       -> Merged Seg2 into Seg1. New Seg1 len: {len(seg1)}")
                    else: # Gộp seg2 vào seg3
                        seg3.insert(0, *seg2)
                        print(f"    [DEBUG - get_split_segments]       -> Merged Seg2 into Seg3. New Seg3 len: {len(seg3)}")

                    # Sau gộp sẽ xét tiếp theo nword word
                    final_segments_result.extend(split_no_comma_logic(seg1))
                    final_segments_result.extend(split_no_comma_logic(seg3))
                    return final_segments_result

                # * nếu 1 có 1/2 word thì xem như câu ko có "," và gọp vào 2 đề chia.
                if len(seg1) <= 2:
                    print(f"    [DEBUG - get_split_segments]     -> Seg1 (len={len(seg1)}) <= 2 words. Merging Seg1 into Seg2 and deferring to split_no_comma_logic for merged (Seg1+Seg2) and Seg3.")
                    seg2.insert(0, *seg1) # Gộp seg1 vào seg2
                    # Sau đó xử lý 2 đoạn đã gộp (Seg1+Seg2) và Seg3
                    final_segments_result.extend(split_no_comma_logic(seg2))
                    final_segments_result.extend(split_no_comma_logic(seg3))
                    return final_segments_result

                # * Nếu 2 có 1/2 word thì xem như câu ko có "," và gọp vào 3 để chia tiếp theo có số lượng word > nword
                if len(seg2) <= 2:
                    print(f"    [DEBUG - get_split_segments]     -> Seg2 (len={len(seg2)}) <= 2 words. Merging Seg2 into Seg3 and deferring to split_no_comma_logic for Seg1 and merged (Seg2+Seg3).")
                    seg3.insert(0, *seg2) # Gộp seg2 vào seg3
                    # Sau đó xử lý 2 đoạn Seg1 và Seg2+Seg3
                    final_segments_result.extend(split_no_comma_logic(seg1))
                    final_segments_result.extend(split_no_comma_logic(seg3))
                    return final_segments_result

                # * nếu 3 <= 2*word, thì gọp 3 vào 2 rồi xét tiếp cho 2 gọp và 1
                if len(seg3) <= 2 * nword:
                    print(f"    [DEBUG - get_split_segments]     -> Seg3 (len={len(seg3)}) <= 2*nword ({2*nword}). Merging Seg3 into Seg2.")
                    seg2.extend(seg3)
                    # Sau đó xử lý 2 đoạn Seg1 và Seg2 (đã gộp)
                    final_segments_result.extend(split_no_comma_logic(seg1))
                    final_segments_result.extend(split_no_comma_logic(seg2))
                    return final_segments_result

                # * nếu 1 >2 word thì tách đoạn đó thành đoạn độc lập, xét tiếp 2 tương tự như 1, nếu 2 <=2*word thì gọp vào 3 chia, nếu 2 >2 word thì tách độc lập ...
                # Nếu không có điều kiện gộp nào phía trên được thỏa mãn, xử lý từng đoạn độc lập
                print(f"    [DEBUG - get_split_segments]     -> No merge conditions met. Splitting Seg1, Seg2, Seg3 independently using split_no_comma_logic.")
                final_segments_result.extend(split_no_comma_logic(seg1))
                final_segments_result.extend(split_no_comma_logic(seg2))
                final_segments_result.extend(split_no_comma_logic(seg3))
                return final_segments_result

        else: # Xử lý khi KHÔNG CÓ dấu phẩy
            print(f"    [DEBUG - get_split_segments]   -> No commas found. Deferring to split_no_comma_logic for the whole sentence.")
            return split_no_comma_logic(words)

    # --- THỰC THI CHÍNH ---
    with open(in_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    blocks = re.findall(r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n((?:.+\n?)+)", content)
    print(f"    [DEBUG] Loaded {len(blocks)} blocks from {in_path}")

    def to_sec(ts):
        h, m, s_ms = ts.strip().split(":")
        s, ms = s_ms.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

    new_blocks = []
    if blocks:
        new_blocks.append(f"1\n{blocks[0][1]}\n    ") # Block 1 (Dummy)
    else:
        print(f"    [WARNING] No blocks found in input SRT. Output will be empty.")


    current_idx = 2 if blocks else 1
    for b_num, b in enumerate(blocks[1:]):
        printf(f"\n    [DEBUG - MAIN LOOP] Processing original block #{b_num+2}: {b[0]}")
        idx, timeframe, text = b
        times = timeframe.split(" --> ")
        start_f, end_f = to_sec(times[0]), to_sec(times[1])

        marker = ""
        if "\u200B" in text:
            marker = "\u200B"
        elif "\u200C" in text:
            marker = "\u200C"

        clean_text = text.replace("\u200B", "").replace("\u200C", "").strip()
        words = clean_text.split()
        print(f"    [DEBUG - MAIN LOOP]   -> Original text: '{text.strip()}'")
        print(f"    [DEBUG - MAIN LOOP]   -> Cleaned text: '{clean_text}'")
        print(f"    [DEBUG - MAIN LOOP]   -> Word list (len={len(words)}): {' '.join(words)}")

        if not words:
            print(f"    [DEBUG - MAIN LOOP]   -> Empty word list, skipping block {idx}.")
            continue

        segments = get_split_segments(words)
        num_seg = len(segments)
        print(f"    [DEBUG - MAIN LOOP]   -> Final segments count: {num_seg}, lengths: {[len(s) for s in segments]}")

        # Tính toán mốc thời gian dựa trên VDA
        time_points = [start_f]
        if num_seg > 1:
            for i in range(1, num_seg):
                ratio = i / num_seg
                gap_time = find_best_gap(start_f, end_f, ratio)
                time_points.append(gap_time)
        time_points.append(end_f)
        print(f"    [DEBUG - MAIN LOOP]   -> Calculated time points: {[f'{t:.2f}' for t in time_points]}")

        # Gộp các đoạn cuối cùng nếu có quá nhiều đoạn nhỏ (áp dụng VDA)
        final_segments_with_vda = []
        current_time_idx = 0
        while current_time_idx < num_seg:
            current_segment = segments[current_time_idx]
            current_start_time = time_points[current_time_idx]
            current_end_time = time_points[current_time_idx + 1]

            # Nếu đoạn hiện tại quá ngắn (ví dụ, 1-2 từ) và không phải là đoạn cuối cùng
            # và nếu đoạn tiếp theo cũng không quá dài, thì gộp lại để tránh các đoạn quá bé.
            # Ngưỡng gộp: Ví dụ, nếu đoạn hiện tại < nword/2 và đoạn tiếp theo cũng < nword
            if len(current_segment) < (nword // 2) and (current_time_idx + 1 < num_seg):
                next_segment = segments[current_time_idx + 1]
                if len(next_segment) < nword: # Nếu đoạn tiếp theo cũng không quá dài
                    print(f"    [DEBUG - MAIN LOOP]   -> Merging small segment ({len(current_segment)} words) with next segment ({len(next_segment)} words).")
                    current_segment.extend(next_segment)
                    current_end_time = time_points[current_time_idx + 2] # Cập nhật end_time sang đoạn tiếp theo
                    current_time_idx += 1 # Bỏ qua đoạn tiếp theo đã gộp

            final_segments_with_vda.append((current_segment, current_start_time, current_end_time))
            current_time_idx += 1

        # Cập nhật time_points sau khi gộp VDA
        # Điều này hơi phức tạp vì VDA cần các mốc thời gian đã được gộp.
        # Để đơn giản, tôi sẽ gộp các đoạn TỪ BÂY GIỜ và sau đó phân bổ lại thời gian
        # Điều này có thể không chính xác hoàn toàn với VDA nếu các đoạn gộp có khoảng lặng lớn ở giữa.
        # Cần một chiến lược VDA tốt hơn cho việc gộp đoạn nhỏ.
        # Tạm thời, tôi sẽ chỉ gộp TEXT và sau đó tính lại time_points dựa trên số đoạn mới.

        # Nếu đã có logic VDA phức tạp, việc thay đổi số lượng đoạn sẽ cần tính toán lại các mốc thời gian.
        # Với mục đích hiện tại (debug và logic cắt), tôi sẽ giữ nguyên cách gán segments và time_points như cũ
        # và chỉ thêm marker vào đoạn cuối của original block, không phải cuối của sub-segments.
        # Logic gộp đoạn nhỏ ở đây có thể làm thay đổi số lượng đoạn so với num_seg ban đầu.
        # Cần điều chỉnh lại time_points cho phù hợp với segments sau khi gộp.

        # Cách đơn giản hơn để xử lý marker và VDA:
        # Gắn marker vào đoạn cuối CỦA TỪNG CHUỖI GỐC sau khi split_no_comma_logic xử lý.
        # Tức là chỉ đoạn cuối của *toàn bộ block ban đầu* nhận marker.

        # Thay đổi logic gán marker để chỉ đoạn cuối cùng của CẢ KHỐI được gắn marker.
        for i, seg in enumerate(segments):
            seg_text = " ".join(seg)
            if i == num_seg - 1: # Chỉ gắn marker cho đoạn cuối của TOÀN BỘ block gốc
                seg_text += marker

            s_t, e_t = time_points[i], time_points[i+1]
            new_blocks.append(f"{current_idx}\n{format_timestamp(s_t)} --> {format_timestamp(e_t)}\n{seg_text}")
            print(f"    [DEBUG - MAIN LOOP]     -> Added new block {current_idx}: {format_timestamp(s_t)} --> {format_timestamp(e_t)} | {seg_text[:50]}{'...' if len(seg_text) > 50 else ''}")
            current_idx += 1

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(new_blocks) + "\n\n")

    print(f"    --> [SUCCESS] Created {out_path} with {current_idx-1} blocks.")

    verify_srt_consistency(in_path, out_path)

    duong_dan = silent_dir
    ten_file_in = "fin_aud_1.srt"
    ten_file_out = "fin_aud_1.txt"
    process_srt_visualize(duong_dan, ten_file_in, ten_file_out)
    print(f"    --> [CREATED] {ten_file_out}")

    run_analyze_long()

    print("--- Step 6 Finished ---\n")
    step_pass_small_2l()
    printf("\nPLEASE_USE: 'python.exe scripts.py 7' TO RUN NEXT STEP\n")

def run_analyze_long():
    print(f"\n--- Step: Analyze Longest Elements (Source: fin_aud_1.srt) ---")
    srt_path = os.path.join(silent_dir, "fin_aud_1.srt")
    if not os.path.exists(srt_path):
        print(f"    ERROR: File {srt_path} not found. Please run Step 4 and 6 first.")
        return

    # 1. Trích xuất kịch bản để map Giới tính với từng từ
    script_word_map = []
    for line in scripts.strip().split("\n"):
        if ":" in line and not line.startswith("("):
            speaker_part, text_content = line.split(":", 1)
            gender = "Man" if "Man" in speaker_part else "Woman"
            clean_text = re.sub(r"\(.*?\)", "", text_content).strip()
            # Xử lý gạch nối thành dấu cách để đếm từ đồng bộ với Step 6
            words = clean_text.replace('-', ' ').split()
            for w in words:
                script_word_map.append({"word": w, "gender": gender})

    # 2. Đọc file SRT
    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read().strip()

    blocks = re.findall(r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n((?:.+\n?)+)", srt_content)
    if len(blocks) < 2:
        print("    ERROR: SRT file is empty or only contains dummy anchor.")
        return

    long_man = {"len": 0, "word": "", "time": ""}
    long_woman = {"len": 0, "word": "", "time": ""}
    long_sent = {"len": 0, "text": "", "time": ""}

    word_ptr = 0
    # Bỏ qua block 1 (Dummy)
    for block in blocks[1:]:
        idx, time, text = block
        clean_text = text.strip()

        # A. Tìm block (câu) chứa nhiều ký tự nhất
        if len(clean_text) > long_sent["len"]:
            long_sent = {"len": len(clean_text), "text": clean_text, "time": time}

        # B. Tách từ trong block để tìm từ dài nhất theo giới tính
        words_in_block = clean_text.replace('-', ' ').split()
        for srt_w in words_in_block:
            if word_ptr < len(script_word_map):
                gender = script_word_map[word_ptr]["gender"]
                # Đếm độ dài "từ" (loại bỏ ký tự đặc biệt như , . ! ? khi tính length)
                pure_word_len = len(re.sub(r'[^\w]', '', srt_w))

                if gender == "Man":
                    if pure_word_len > long_man["len"]:
                        long_man = {"len": pure_word_len, "word": srt_w, "time": time}
                else:
                    if pure_word_len > long_woman["len"]:
                        long_woman = {"len": pure_word_len, "word": srt_w, "time": time}
                word_ptr += 1

    # 3. Chuẩn bị nội dung xuất ra (Full nội dung cho file)
    report = [
        "="*80,
        f"{'CATEGORY':<15} | {'LEN':<3} | {'CONTENT':<30} | {'TIMEFRAME'}",
        "-" * 80,
        f"{'Longest Man':<15} | {long_man['len']:<3} | {long_man['word']:<30} | {long_man['time']}",
        f"{'Longest Woman':<15} | {long_woman['len']:<3} | {long_woman['word']:<30} | {long_woman['time']}",
        f"{'Longest Block':<15} | {long_sent['len']:<3} | {long_sent['text']:<30} | {long_sent['time']}",
        "="*80
    ]
    final_report = "\n".join(report)

    # 4. In ra màn hình
    print("\n" + final_report)

    # 5. Ghi vào file bk_wlongest (Đảm bảo in FULL câu)
    try:
        with open("bk_wlongest", "w", encoding="utf-8") as f:
            f.write("--- DETAILED ANALYSIS REPORT ---\n")
            f.write(f"Longest Man Word: '{long_man['word']}' ({long_man['len']} chars) at {long_man['time']}\n")
            f.write(f"Longest Woman Word: '{long_woman['word']}' ({long_woman['len']} chars) at {long_woman['time']}\n")
            f.write(f"Longest Sentence: '{long_sent['text']}' ({long_sent['len']} chars) at {long_sent['time']}\n")
            f.write("-" * 40 + "\n")
            f.write(final_report) # Kèm theo cả bảng tóm tắt
        print(f"\n    --> Analysis saved to: bk_wlongest\n")
    except Exception as e:
        print(f"    ERROR saving file: {e}")

#===============================================================================██████
#===============================================================================     █
#===============================================================================    █
#===============================================================================   █
#===============================================================================  █
def run_srt_step7():
    print(f"\n--- Step 7: Gen SRT word by word and check match SCRIPTS VS SRT ---")
    convert_final1srt_2_final2seg()
    align_scripts_2_final2alignseg()
    convert_final2alignseg_2_srt( "audio_ffmpegs/fin_aud_2ali.seg", "audio_ffmpegs/fin_aud_2ali.srt" )
    check_match_scripts_and_finalsrt()

    print("--- Step 7 Finished ---\n")
    step_pass_small_2l()
    printf("\nPLEASE_USE: 'python.exe scripts.py 8' TO RUN NEXT STEP\n")

def convert_final1srt_2_final2seg():
    print(f"\n--- Step: convert_final1srt_2_final2seg ---")

    srt_path = os.path.join(silent_dir, "fin_aud_1.srt")
    out_path = os.path.join(silent_dir, "fin_aud_2.seg")

    if not os.path.exists(srt_path):
        print(f"    [ERROR] Không tìm thấy file: {srt_path}")
        return

    # 1. Đọc nội dung file SRT
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    # 2. Regex tách các block (ID, Time, Text)
    blocks = re.findall(r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n((?:.+\n?)+)", content)

    segments = []

    for b in blocks:
        idx, timeframe, text = b

        # Bỏ qua block mỏ neo (Dummy Anchor)
        if idx == "1":
            continue

        # Chuyển đổi thời gian sang float
        start_str, end_str = timeframe.split(" --> ")
        start_sec = time_to_seconds(start_str)
        end_sec = time_to_seconds(end_str)

        # Làm sạch văn bản: bỏ Marker \u200B (Man), \u200C (Woman) và xuống dòng
        clean_txt = text.replace("\u200B", "").replace("\u200C", "").strip()

        segments.append({
            "start": round(start_sec, 3),
            "end": round(end_sec, 3),
            "text": clean_txt
        })

    # 3. Lưu thành file .seg (định dạng JSON để giữ cấu trúc mảng/dict)
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            # Lưu với indent=4 để dễ đọc bằng mắt
            json.dump(segments, f, ensure_ascii=False, indent=4)

        print(f"    --> [SUCCESS] Converted {srt_path} to {out_path}")
        print(f"    --> Total segments saved: {len(segments)}")

    except Exception as e:
        print(f"    [ERROR] Không thể lưu file: {e}")

def align_scripts_2_final2alignseg():
    print(f"\n--- Step: align_scripts_2_final2alignseg ---")

    if not hasattr(torchaudio, "set_audio_backend"):
        def dummy_backend(x):
            pass
        torchaudio.set_audio_backend = dummy_backend

    def normalize_word(w):
        w = w.lower()
        # remove invisible unicode
        w = (
            w.replace("\u200b", "")
             .replace("\u200c", "")
             .replace("\u200d", "")
        )
        # remove punctuation
        w = re.sub(r"[^\w]", "", w)
        return w.strip()

    # ==========================================================================
    # QUAN TRỌNG: MONKEY PATCH ĐỂ SỬA LỖI "NOT A ZIP FILE" TRÊN WINDOWS
    # ==========================================================================
    original_load = torch.load
    def patched_torch_load(*args, **kwargs):
        # Ép PyTorch cho phép nạp các file định dạng cũ (Pickle)
        # vốn là nguyên nhân gây lỗi "Not a zip file"
        kwargs['weights_only'] = False
        return original_load(*args, **kwargs)

    # Thay thế hàm load mặc định của hệ thống bằng hàm đã vá
    torch.load = patched_torch_load
    # ==========================================================================

    device = "cpu"
    # Tìm file audio tự động
    # Giả định 'silent_dir' đã được định nghĩa ở đâu đó trong môi trường của bạn
    # Ví dụ: silent_dir = "audio_ffmpegs"
    # silent_dir = "audio_ffmpegs" # <--- THAY ĐỔI DÒNG NÀY NẾU CHƯA CÓ silent_dir

    audio_files = [f for f in os.listdir(silent_dir) if "final_audio" in f and f.endswith(".wav")]
    audio_file_name = next((f for f in audio_files if "0p8" in f), audio_files[0])
    audio_path = os.path.join(silent_dir, audio_file_name)
    seg_path = os.path.join(silent_dir, "fin_aud_2.seg")
    srt_path = os.path.join(silent_dir, "fin_aud_1.srt") # Thêm đường dẫn đến file SRT gốc

    print(f"    --> Using device: {device}")
    print(f"    --> Target Audio: {audio_path}")
    print(f"    --> Reference SRT: {srt_path}") # In thêm thông tin về file SRT

    # ==========================================================================
    # Lấy thông tin thời gian từ SRT để dùng làm fallback cho từng segment
    # ==========================================================================
    srt_segments_info = {}
    if os.path.exists(srt_path):
        try:
            with open(srt_path, "r", encoding="utf-8") as f:
                raw_subs = list(srt.parse(f.read()))

                # REMOVE EMPTY SUBS
                subs = []
                for sub in raw_subs:
                    text = sub.content.strip()

                    # bỏ các subtitle rỗng / invisible chars
                    if text.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "").strip():
                        subs.append(sub)

                for i, sub in enumerate(subs):
                    srt_segments_info[i] = {
                        "start": sub.start.total_seconds(),
                        "end": sub.end.total_seconds(),
                        "text": sub.content.strip()
                    }
            print(f"    --> Loaded {len(srt_segments_info)} segments from SRT for fallback timing.")
        except Exception as e_srt:
            print(f"    [ERROR] Failed to load SRT file {srt_path}: {e_srt}. Per-segment fallback will not be available.")
            srt_segments_info = {} # Đảm bảo không sử dụng dữ liệu SRT lỗi
    else:
        print(f"    [WARNING] SRT file not found at {srt_path}. Cannot use SRT for per-segment fallback timing.")

    # ==========================================================================
    try:
        print("    --> Loading audio data...")
        audio = whisperx.load_audio(audio_path)

        print("    --> Loading Align Model (Wav2Vec2)...")
        # Sử dụng model của facebook để ổn định nhất
        model_a, metadata = whisperx.load_align_model(
            language_code="en",
            device=device
        )

        if not os.path.exists(seg_path):
            print(f"    [ERROR] Không tìm thấy file segments: {seg_path}")
            return

        with open(seg_path, "r", encoding="utf-8") as f:
            segments_to_align = json.load(f) # Các segment gốc từ fin_aud_2.seg

        # DEBUG: kiểm tra lệch index giữa SEG và SRT
        # print("\n--- CHECK SEG vs SRT ALIGNMENT ---")
        # for i in range(min(len(segments_to_align), len(srt_segments_info))):
        #     seg_text = segments_to_align[i].get("text", "").strip()
        #     srt_text = srt_segments_info[i]["text"].strip()
        #     if seg_text != srt_text:
        #         print(f"\n[MISMATCH] idx={i}")
        #         print(f"SEG : {seg_text}")
        #         print(f"SRT : {srt_text}")
        # print("--- END CHECK ---\n")

        print("    --> Starting Alignment (Executing Patched Torch Pipeline)...")

        # Thực hiện alignment toàn bộ bằng WhisperX
        try:
            temp_result = whisperx.align(segments_to_align, model_a, metadata, audio, device)
            print("    --> [SUCCESS] WhisperX Alignment completed.")
        except Exception as e_align:
            print(f"    [WARNING] Global WhisperX Alignment failed: {e_align}. Proceeding with per-segment analysis and potential fallback.")
            # Nếu toàn bộ quá trình align thất bại, temp_result sẽ trống,
            # chúng ta vẫn sẽ cố gắng xử lý từng segment một bằng fallback nếu có SRT.

        # Lưu kết quả word-level ra file
        output_path = os.path.join(silent_dir, "fin_aud_2ali.seg")

        with open(output_path, "w", encoding="utf-8") as f:
            # Lưu alignment_result đã có
            json.dump(temp_result, f, ensure_ascii=False, indent=2)

        print(f"    --> [SUCCESS] Saved word-level segments to: {output_path}")

    except Exception as e:
        print(f"    [ERROR] Process failed: {e}")
    finally:
        # Khôi phục lại hàm gốc để tránh ảnh hưởng các phần khác nếu cần
        torch.load = original_load

def convert_final2alignseg_2_srt(seg_path="audio_ffmpegs/fin_aud_2ali.seg", srt_path="audio_ffmpegs/fin_aud_2ali.srt"):
    print(f"\n--- Step: convert_final2alignseg_2_srt ---")

    def sec_to_srt_time(t):
        hours = int(t // 3600)
        minutes = int((t % 3600) // 60)
        seconds = int(t % 60)
        millis = int((t - int(t)) * 1000)
        return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"

    # Load .seg
    with open(seg_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    segments = data.get("segments", [])

    srt_lines = []

    # Dummy subtitle
    srt_lines.append("1")
    srt_lines.append("00:00:00,000 --> 00:00:00,100")
    srt_lines.append("    ")
    srt_lines.append("")

    idx = 2

    # Convert each word to SRT entry
    for seg in segments:
        for word_info in seg.get("words", []):

            word = word_info.get("word", "").strip()
            start = word_info.get("start", 0)
            end = word_info.get("end", 0)

            srt_lines.append(str(idx))
            srt_lines.append(
                f"{sec_to_srt_time(start)} --> {sec_to_srt_time(end)}"
            )
            srt_lines.append(word)
            srt_lines.append("")

            idx += 1

    # Save SRT
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))

    print(f"    --> [SAVED] SRT to: {srt_path}")

def check_match_scripts_and_finalsrt():
    print(f"\n--- Step: Testing Ultra-Strict Alignment Accuracy (Punctuation + Case-sensitive) ---")

    srt_path = os.path.join(silent_dir, "fin_aud_2ali.srt")
    if not os.path.exists(srt_path):
        print(f"    [ERROR] Không tìm thấy file: {srt_path}")
        return

    # 1. TRÍCH XUẤT TỪ TRONG KỊCH BẢN (Giữ nguyên Hoa/Thường & Dấu câu)
    def expand_symbols(text):
        # Lưu ý: Các từ nở rộng như "dollars" sẽ để thường vì AI thường đọc vậy,
        # nhưng kịch bản gốc vẫn giữ nguyên Hoa/Thường.
        text = re.sub(r'\$(\d+(?:\.\d+)?)\s*b(illion)?', r'\1 billion dollars', text, flags=re.I)
        text = re.sub(r'\$(\d+(?:\.\d+)?)\s*m(illion)?', r'\1 million dollars', text, flags=re.I)
        text = re.sub(r'\$(\d+(?:\.\d+)?)', r'\1 dollars', text)
        text = text.replace("-", " ")
        return text

    script_words = []
    lines = scripts.strip().split("\n")
    for line in lines:
        if ":" in line and not line.startswith("("):
            _, txt = line.split(":", 1)
            # 1. Xóa các tag thời gian (0p5s)
            # 2. Nở rộng ký hiệu
            clean_txt = expand_symbols(re.sub(r"\(.*?\)", "", txt))
            # 3. Tách từ theo khoảng trắng (Giữ nguyên Hoa/Thường và Dấu câu dính kèm)
            words = clean_txt.split()
            script_words.extend(words)

    # 2. TRÍCH XUẤT TỪ TRONG FILE SRT
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    # Regex tách các block SRT
    srt_blocks = re.findall(r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n((?:.+\n?)+)", content)

    srt_word_list = []
    for b in srt_blocks:
        idx, timeframe, text = b
        if idx == "1": continue # Bỏ qua dummy anchor

        # Làm sạch khỏi Marker ẩn, GIỮ NGUYÊN HOA/THƯỜNG
        clean_w = text.replace("\u200B", "").replace("\u200C", "").strip()

        if clean_w:
            srt_word_list.append({
                "word": clean_w,
                "ts": timeframe.split(" --> ")[0],
                "idx": idx
            })

    # 3. SO KHỚP CỰC KỲ NGHIÊM NGẶT (Không dùng .lower())
    s_words_pure = script_words
    a_words_pure = [w["word"] for w in srt_word_list]

    matcher = difflib.SequenceMatcher(None, s_words_pure, a_words_pure)

    print(f"\n{'STATUS':<12} | {'SRT WORD':<18} | {'SCRIPT WORD':<18} | {'TIMESTAMP'}")
    print("-" * 75)

    errors = 0
    matches = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1):
                matches += 1

        elif tag == 'replace':
            # Mismatch do khác chữ, khác dấu câu, hoặc khác Hoa/Thường
            for k in range(max(i2-i1, j2-j1)):
                w_scr = script_words[i1+k] if (i1+k) < i2 else "---"
                w_srt = srt_word_list[j1+k]["word"] if (j1+k) < j2 else "---"
                ts = srt_word_list[j1+k]["ts"] if (j1+k) < j2 else "N/A"
                print(f"{'![MISMATCH]':<12} | {w_srt:<18} | {w_scr:<18} | {ts}")
                errors += 1

        elif tag == 'insert':
            # Thừa từ trong SRT
            for k in range(j2 - j1):
                w_srt = srt_word_list[j1+k]["word"]
                ts = srt_word_list[j1+k]["ts"]
                print(f"{'x[EXTRA]':<12} | {w_srt:<18} | {'---':<18} | {ts}")
                errors += 1

        elif tag == 'delete':
            # Thiếu từ trong SRT
            for k in range(i2 - i1):
                w_scr = script_words[i1+k]
                # Tìm mốc thời gian xấp xỉ
                ts_approx = srt_word_list[j1]['ts'] if j1 < len(srt_word_list) else "End"
                print(f"{'?[MISSING]':<12} | {'---':<18} | {w_scr:<18} | Around {ts_approx}")
                errors += 1

    # 4. TỔNG KẾT
    print("-" * 75)
    total_script = len(script_words)
    accuracy = (matches / total_script) * 100 if total_script > 0 else 0

    print(f"    --> Total Elements (Case-sensitive): {total_script}")
    print(f"    --> Exact Matches: {matches}")
    print(f"    --> Discrepancies: {errors}")
    print(f"    --> Strict Accuracy: {accuracy:.2f}%")

    if errors == 0:
        print(f"    [PERFECT SYNC] Words, Case, and Punctuation match 100%.")
        print(f"\n\n            --> PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS\n\n")
    else:
        print(f"    [DIVERGENCE] Found {errors} case or punctuation differences.")
        print(f"\n\n            --> FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL\n\n")
        step_fail_small_2l()

#===============================================================================██████
#===============================================================================█    █
#===============================================================================██████
#===============================================================================█    █
#===============================================================================██████
def run_srt_step8():
    print(f"\n--- Step 8: Gen PUPCAPS SRT file ---")
    one_word_srt = os.path.join(silent_dir, "fin_aud_2ali.srt")
    six_word_srt = os.path.join(silent_dir, "fin_aud_1.srt")
    pupcaps_srt = os.path.join(silent_dir, "fin_aud_1pcap.srt")

    # 1. Tạo file Pupcaps gốc
    convert_srt_2_pupcaps(one_word_srt, six_word_srt, pupcaps_srt)

    # 2. Kiểm tra tính toàn vẹn
    check_pupcaps_integrity()

    #   # 3. Visual check cho file đã sửa
    #   process_srt_visualize(silent_dir, "fin_aud_1pcap.srt", "fin_aud_1pcap.txt")

    print("--- Step 8 Finished ---\n")
    step_pass_small_2l()
    printf("\nPLEASE_USE: 'python.exe scripts.py 9' TO RUN NEXT STEP\n")

def convert_srt_2_pupcaps(one_word_srt, six_word_srt, pupcaps_srt):
    print(f"\n--- Step: Generating Pupcaps Style SRT ---")

    def get_srt_blocks(path):
        if not os.path.exists(path): return []
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        # Regex lấy ID, Time và Text
        return re.findall(r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n((?:.+\n?)+)", content)

    def clean(t):
        # Xóa marker ẩn và khoảng trắng thừa
        return t.replace("\u200B", "").replace("\u200C", "").strip()

    blocks_1w = get_srt_blocks(one_word_srt)
    blocks_6w = get_srt_blocks(six_word_srt)

    if not blocks_1w or not blocks_6w:
        print("    [ERROR] File input không hợp lệ hoặc trống.")
        return

    # 1. Bỏ qua block dummy (Index 1) ở cả 2 file
    list_1w = [b for b in blocks_1w if b[0] != "1"]
    list_6w = [b for b in blocks_6w if b[0] != "1"]

    ptr_1w = 0
    final_pupcaps = []
    global_idx = 1

    for b6 in list_6w:
        time_6w = b6[1].split(" --> ")
        sent_start = time_to_seconds(time_6w[0])
        sent_end = time_to_seconds(time_6w[1])
        sent_text = clean(b6[2])
        sent_words = sent_text.split()

        # Lấy danh sách các block 1-word tương ứng với số từ trong câu này
        group_1w = []
        for _ in range(len(sent_words)):
            if ptr_1w < len(list_1w):
                group_1w.append(list_1w[ptr_1w])
                ptr_1w += 1

        if not group_1w: continue

        # --- LOGIC XỬ LÝ KHOẢNG LẶNG ĐẦU CÂU ---
        first_word_start = time_to_seconds(group_1w[0][1].split(" --> ")[0])
        if first_word_start > sent_start + 0.01: # Nếu có khoảng hở > 10ms
            final_pupcaps.append(f"{global_idx}\n{format_timestamp(sent_start)} --> {format_timestamp(first_word_start - 0.001)}\n{sent_text}")
            global_idx += 1

        # --- LOGIC TẠO CÁC NHỊP HIGHLIGHT [WORD] ---
        for i in range(len(group_1w)):
            current_w_block = group_1w[i]
            w_time = current_w_block[1].split(" --> ")

            w_start = time_to_seconds(w_time[0])

            # Thời gian kết thúc của nhịp này là bắt đầu của từ tiếp theo
            # Nếu là từ cuối cùng, lấy mốc kết thúc của chính từ đó (hoặc của cả câu)
            if i < len(group_1w) - 1:
                w_end = time_to_seconds(group_1w[i+1][1].split(" --> ")[0]) - 0.001
            else:
                w_end = time_to_seconds(w_time[1])

            # Tạo text có dấu ngoặc []
            # Chúng ta dùng index để tránh highlight nhầm nếu trong câu có 2 từ giống nhau
            highlighted_sent = " ".join([f"[{w}]" if j == i else w for j, w in enumerate(sent_words)])

            final_pupcaps.append(f"{global_idx}\n{format_timestamp(w_start)} --> {format_timestamp(w_end)}\n{highlighted_sent}")
            global_idx += 1

    # Xuất file
    with open(pupcaps_srt, "w", encoding="utf-8") as f:
        f.write("\n\n".join(final_pupcaps) + "\n\n")

    print(f"    --> [SUCCESS] Pupcaps SRT created: {pupcaps_srt}")

def check_pupcaps_integrity():
    print(f"\n--- Step: CHECK PUPCAPS INTEGRITY ---")
    print(f"\n    {'='*25} ULTIMATE PUPCAPS VERIFICATION {'='*25}")

    path_1 = os.path.join(silent_dir, "fin_aud_1pcap.srt") # File 1
    path_2 = os.path.join(silent_dir, "fin_aud_1.srt")         # File 2
    path_3 = os.path.join(silent_dir, "fin_aud_2ali.srt")   # File 3

    def get_blocks(path):
        if not os.path.exists(path): return []
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        # Regex bóc tách ID, Timeframe và Text
        raw = re.findall(r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n((?:.+\n?)+)", content)

        # SỬA TẠI ĐÂY:
        # Không lọc theo b[0] != "1" nữa.
        # Mà lọc theo b[2].strip() != "" (Nếu text có chữ thì giữ lại, trắng thì bỏ)
        valid_blocks = [b for b in raw if b[2].strip()]

        return valid_blocks

    def clean_full(t):
        # Xóa marker ẩn và xóa cả ngoặc [] để so khớp nội dung câu
        return t.replace("\u200B", "").replace("\u200C", "").replace("[", "").replace("]", "").strip()

    def get_word_in_brackets(t):
        # Trích xuất nội dung bên trong dấu ngoặc []
        match = re.search(r"\[(.*?)\]", t)
        return match.group(1) if match else None

    blocks_f1 = get_blocks(path_1)
    blocks_f2 = get_blocks(path_2)
    blocks_f3 = get_blocks(path_3)

    if not blocks_f1:
        print("    [ERROR] File fin_aud_1pcap.srt trống hoặc không tồn tại.")
        return

    errors = 0
    prev_end = -1.0
    ptr_f3 = 0 # Con trỏ tịnh tiến cho file word-align (File 3)

    # đọc vào file silent_dir/fin_aud_2ali.srt lưu vào biến fin_aud_2ali_srt
    with open(path_3, "r", encoding="utf-8") as f:
        fin_aud_2ali_srt = f.read()

    # Duyệt từng Timeline (TL) của file Pupcaps
    for i in range(len(blocks_f1)):
        #printf ("i: ", i)
        idx, timeframe, text = blocks_f1[i]
        #printf ("text: ", text)
        start_f1_str, end_f1_str = timeframe.split(" --> ")
        s_f1 = time_to_seconds(start_f1_str)
        e_f1 = time_to_seconds(end_f1_str)

        # --- 1. KIỂM TRA OVERLAP ---
        if s_f1 <= prev_end: # Dung sai 1ms
            printf ("s_f1: ", s_f1)
            printf ("prev_end: ", prev_end)
            print(f"    --> [ERROR] [OVERLAP] Block {idx}: {start_f1_str} đè lên block trước kết thúc tại {format_timestamp(prev_end)}")

            # hàm đọc dò điểm OVERLAP trong biến fin_aud_2ali_srt và sửa, lưu lại vào biến fin_aud_2ali_srt
            # --- FIX OVERLAP TRONG fin_aud_2ali_srt ---
            def fix_overlap_in_srt(srt_text, overlap_sec):

                pattern = re.compile(
                    r"(\d+)\n"
                    r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n"
                    r"(.*?)"
                    r"(?=\n\n\d+\n|\Z)",
                    re.DOTALL
                )

                matches = list(pattern.finditer(srt_text))

                blocks = []

                for m in matches:
                    blocks.append({
                        "idx": m.group(1),
                        "start": m.group(2),
                        "end": m.group(3),
                        "text": m.group(4).strip()
                    })

                changed = False

                # =========================================================
                # FIX TYPE 1:
                # Detect overlap logic between consecutive subtitles
                # =========================================================
                for k in range(1, len(blocks)):

                    prev_end_sec = time_to_seconds(blocks[k-1]["end"])
                    cur_start_sec = time_to_seconds(blocks[k]["start"])

                    if cur_start_sec <= prev_end_sec:

                        new_end = round(cur_start_sec - 0.001, 3)

                        if new_end < time_to_seconds(blocks[k-1]["start"]):
                            new_end = time_to_seconds(blocks[k-1]["start"])

                        old_end = blocks[k-1]["end"]

                        blocks[k-1]["end"] = format_timestamp(new_end)

                        print(
                            f"        [FIX OVERLAP TYPE1] "
                            f"{blocks[k-1]['idx']} : "
                            f"{old_end} -> {blocks[k-1]['end']}"
                        )

                        changed = True

                # =========================================================
                # FIX TYPE 2:
                # Directly search exact overlap timestamp and -0.001
                # overlap_sec = timestamp bị overlap
                # =========================================================
                overlap_ts = format_timestamp(overlap_sec)

                for b in blocks:

                    end_sec = time_to_seconds(b["end"])

                    if abs(end_sec - overlap_sec) == 0:

                        new_end_sec = round(end_sec - 0.001, 3)

                        if new_end_sec < time_to_seconds(b["start"]):
                            new_end_sec = time_to_seconds(b["start"])

                        old_end = b["end"]

                        b["end"] = format_timestamp(new_end_sec)

                        print(
                            f"        [FIX OVERLAP TYPE2] "
                            f"{b['idx']} : "
                            f"{old_end} -> {b['end']}"
                        )

                        changed = True

                if not changed:
                    return srt_text

                out = []

                for b in blocks:
                    out.append(str(b["idx"]))
                    out.append(f"{b['start']} --> {b['end']}")
                    out.append(b["text"])
                    out.append("")

                return "\n".join(out)

            fin_aud_2ali_srt = fix_overlap_in_srt(fin_aud_2ali_srt, prev_end)

            errors += 1
        prev_end = e_f1

        pure_text = clean_full(text)

        # --- 2. XỬ LÝ TIMELINE KHÔNG CHỨA [] (Gap đầu câu) ---
        if "[" not in text:
            match_f2 = None
            # Quét tìm câu tương ứng trong file 2
            for b2 in blocks_f2:
                if clean_full(b2[2]) == pure_text:
                    match_f2 = b2
                    # Nếu tìm thấy nhiều câu giống nhau, ưu tiên câu có thời gian gần nhất
                    if abs(s_f1 - time_to_seconds(b2[1].split(" --> ")[0])) < 5.0:
                        break

            if match_f2 is None:
                print(f"    -->[ERROR] [NOTMATCH] Block {idx}: Nội dung '{pure_text[:30]}...' không khớp bất kỳ câu nào trong File 2.")
                errors += 1
            else:
                s_f2 = time_to_seconds(match_f2[1].split(" --> ")[0])
                if abs(s_f1 - s_f2) == 0:
                    #printf ("s_f1: ", s_f1)
                    #printf ("s_f2: ", s_f2)
                    print(f"    [RULE1 OK] Block {idx}: Start match File 2 ({start_f1_str})")
                else:
                    # Report điều chỉnh theo yêu cầu
                    print(f"    --> [ERROR] [RULE1] Block {idx}: Điều chỉnh Start từ gốc {format_timestamp(s_f2)} thành {start_f1_str}")
                    errors += 1

        # --- 3. XỬ LÝ TIMELINE CHỨA [word] ---
        else:
            #printf ("text: ", text)
            word_target = get_word_in_brackets(text)
            #printf ("word_target: ", word_target)

            if ptr_f3 < len(blocks_f3):
                # File 3 bọc từ đơn, ta lấy text sạch của nó
                word_f3 = blocks_f3[ptr_f3][2].replace("\u200B", "").replace("\u200C", "").strip()
                s_f3 = time_to_seconds(blocks_f3[ptr_f3][1].split(" --> ")[0])

                # Kiểm tra match từ và match start time
                if word_target.lower() != word_f3.lower():
                    # Nếu lệch, có thể do file word-align bị trượt, báo lỗi nghiêm trọng
                    print(f"    --> [ERROR] [RULE2_word] Block {idx}: Từ trong ngoặc '{word_target}' không khớp File 3 '{word_f3}' tại pointer.")
                    errors += 1

                if (s_f1 - s_f3) != 0:
                    printf ("s_f1: ", s_f1)
                    printf ("s_f3: ", s_f3)
                    print(f"    --> [ERROR] [RULE2_start] Block {idx}: Start của '{word_target}' ({start_f1_str}) không match File 3 ({format_timestamp(s_f3)})")
                    errors += 1

                # Kiểm tra End nhịp này = Start nhịp sau - 1ms
                if i < len(blocks_f1) - 1:
                    next_text = blocks_f1[i+1][2]
                    # CHỈ kiểm tra nếu từ kế tiếp vẫn nằm trong CÙNG một câu (file 2)
                    if clean_full(next_text) == pure_text:
                        next_s_f1 = time_to_seconds(blocks_f1[i+1][1].split(" --> ")[0])
                        expected_end = round(next_s_f1 - 0.001, 3)
                        if abs(round(e_f1, 3) - expected_end) != 0:
                            printf ("e_f1: ", e_f1)
                            printf ("expected_end: ", format_timestamp(expected_end))
                            print(f"    --> [ERROR] [RULE2_end] Block {idx}: End {end_f1_str} sai logic gối đầu. Phải là {format_timestamp(expected_end)}")
                            errors += 1

                ptr_f3 += 1 # Tăng con trỏ file 3 sau khi check xong 1 từ
            else:
                print(f"    --> [ERROR] Block {idx}: Hết từ trong File 3 để đối chiếu.")
                errors += 1

    # lưu lại vào file silent_dir/fin_aud_2ali.srt
    with open(path_3, "w", encoding="utf-8") as f:
        f.write(fin_aud_2ali_srt)

    print(f"    {'-'*75}")
    if errors == 0:
        print(f"    INTEGRITY PASSED: fin_aud_1pcap.srt is 100% logic-safe.")
        print(f"\n\n            --> PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS PASS\n\n")
    else:
        print(f"    INTEGRITY FAILED: Found {errors} discrepancies.")
        print(f"\n\n            --> FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL FAIL\n\n")
        step_fail_small_2l()

#===============================================================================██████
#===============================================================================█    █
#===============================================================================██████
#===============================================================================     █
#===============================================================================██████
def run_srt_step9():
    print(f"\n--- Step 9: Extracting Longest Highlight Section (Punctuation-Insensitive) ---")
    fixed_segment_duration_sec = 0.7  # Có thể chỉnh nhanh tại đây (ví dụ: 0.8, 1.2, 2.0)

    srt_path = os.path.join(silent_dir, "fin_aud_1pcap.srt")
    out_path = os.path.join(silent_dir, "fin_aud_1pcap_lest.srt")

    if not os.path.exists(srt_path):
        print(f"    [ERROR] Không tìm thấy file: {srt_path}")
        return

    def get_blocks(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        raw = re.findall(r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n((?:.+\n?)+)", content)
        return [b for b in raw if b[2].strip()]

    # Hàm chuẩn hóa để so sánh: Xóa marker, xóa ngoặc, xóa cả dấu câu và khoảng trắng thừa
    def normalize_for_compare(t):
        t = t.replace("\u200B", "").replace("\u200C", "").replace("[", "").replace("]", "")
        # Xóa tất cả ký tự không phải chữ cái hoặc số
        return re.sub(r'[^a-zA-Z0-9]', '', t).lower()

    def get_bracket_word(t):
        match = re.search(r"\[(.*?)\]", t)
        return match.group(1) if match else ""

    def parse_longest_sentence_from_report(report_path="bk_wlongest"):
        if not os.path.exists(report_path):
            return ""
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                report = f.read()
            match = re.search(r"Longest Sentence:\s*'(.+?)'\s*\(\d+\s*chars\)\s*at", report, re.DOTALL)
            if match:
                return match.group(1).strip()
        except Exception as e:
            print(f"    [WARN] Không đọc được {report_path}: {e}")
        return ""

    def find_best_idx_for_sentence(target_sentence, all_blocks):
        target_norm = normalize_for_compare(target_sentence)
        if not target_norm:
            return -1

        matched_idxs = [i for i, b in enumerate(all_blocks) if normalize_for_compare(b[2]) == target_norm]
        if not matched_idxs:
            return -1

        # Ưu tiên block có [word] dài nhất, giống logic hiện tại
        best_idx = -1
        best_len = -1
        for idx in matched_idxs:
            word = get_bracket_word(all_blocks[idx][2])
            pure_word = re.sub(r'[^a-zA-Z0-9]', '', word)
            if len(pure_word) > best_len:
                best_len = len(pure_word)
                best_idx = idx
        return best_idx

    blocks = get_blocks(srt_path)
    if len(blocks) < 3:
        print("    [ERROR] File SRT quá ngắn.")
        return

    # 1. Tìm độ dài câu lớn nhất (dựa trên chuỗi đã chuẩn hóa)
    max_norm_len = -1
    target_norm_text = ""

    for b in blocks:
        norm_txt = normalize_for_compare(b[2])
        if len(norm_txt) > max_norm_len:
            max_norm_len = len(norm_txt)
            target_norm_text = norm_txt

    # 2. Tìm block chứa từ trong ngoặc dài nhất thuộc về câu auto-detect
    target_absolute_idx = find_best_idx_for_sentence(target_norm_text, blocks)
    max_word_len = -1
    if target_absolute_idx != -1:
        auto_word = get_bracket_word(blocks[target_absolute_idx][2])
        max_word_len = len(re.sub(r'[^a-zA-Z0-9]', '', auto_word))

    if target_absolute_idx != -1:
        longest_sentence = blocks[target_absolute_idx][2].replace("[", "").replace("]", "").strip()
        total_chars = len(longest_sentence)

    if target_absolute_idx == -1:
        print("    [ERROR] Không tìm thấy từ phù hợp.")
        return

    # 3. Trích xuất thêm 1 câu từ file bk_wlongest (nếu có)
    report_sentence = parse_longest_sentence_from_report("bk_wlongest")
    report_target_idx = find_best_idx_for_sentence(report_sentence, blocks) if report_sentence else -1

    #printf ("report_sentence: ", report_sentence)
    #printf ("target_absolute_idx: ", target_absolute_idx)
    #printf ("report_target_idx: ", report_target_idx)

    # 4. Xuất .srt: mỗi câu target sẽ trích 3 timeline liên tục như logic cũ
    all_target_idxs = [target_absolute_idx]
    #if report_target_idx != -1 and report_target_idx not in all_target_idxs:
    if report_target_idx != -1 :
        all_target_idxs.append(report_target_idx)

    # DEBUG
    #with open("123.test", "w", encoding="utf-8") as f: f.write(str(all_target_idxs))

    final_output = []
    running_idx = 1
    current_base = 0.0
    for target_idx in all_target_idxs:
        start_idx = max(0, target_idx - 1)
        end_idx = min(len(blocks) - 1, target_idx + 1)
        selected_blocks = blocks[start_idx : end_idx + 1]
        for b in selected_blocks:
            s_sec = current_base
            e_sec = s_sec + fixed_segment_duration_sec
            final_output.append(
                f"{running_idx}\n{format_timestamp(s_sec)} --> {format_timestamp(e_sec)}\n{b[2].strip()}"
            )
            running_idx += 1
            current_base = e_sec

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(final_output) + "\n\n")

    print(f"    --> [SUCCESS] Longest snippet saved to: {out_path}")
    print(f"    --> [CONFIG] Fixed segment duration: {fixed_segment_duration_sec}s")
    print(f"    --> Longest sentence found: \"{longest_sentence}\"")
    print(f"        --> Total characters: {total_chars} (including spaces & punctuation)")
    print(f"    --> Longest word found: \"{get_bracket_word(blocks[target_absolute_idx][2])}\" ({max_word_len} chars)\n")
    if report_sentence:
        if report_target_idx != -1:
            print(f"    --> bk_wlongest sentence added: \"{report_sentence}\"")
        else:
            print(f"    --> [WARN] Không match được câu từ bk_wlongest trong fin_aud_1pcap.srt")
    print("--- Step 9 Finished ---\n")
    step_pass_small_2l()
    printf("\nPLEASE_USE: 'python.exe scripts.py 10' TO RUN NEXT STEP\n")

#===============================================================================   █   ██████
#===============================================================================  ██   █    █
#===============================================================================   █   █    █
#===============================================================================   █   █    █
#===============================================================================██████ ██████
def run_pupcaps_step10(s10mode="full", fontsize=88, spacing=-5):
    print(f"\n--- Step 10: Gen _pcap_test.MOV _pcap_full.MOV _pcap_full_aud.MP4 ---")

    printf("s10mode: ", s10mode)
    printf("fontsize: ", fontsize)
    printf("spacing: ", spacing)

    # Cấu hình chung
    base_dir = "./audio_ffmpegs"
    css_file_name = "fin_aud_1pcap.css" # Chỉ tên file
    css_file_path = os.path.join(css_file_name)
    width = "1920"
    height = "1080"

    FONTSIZE    = fontsize
    SPACING     = spacing

    gen_fin_aud_1pcap(FONTSIZE, SPACING, css_file_path)

    # Cấu hình riêng theo s10mode
    if s10mode == "full":
        srt_input = os.path.join(base_dir, "fin_aud_1pcap.srt")
        output_mov = os.path.join(base_dir, "fin_aud_1pcap.mov")
    else:  # Mặc định là test
        srt_input = os.path.join(base_dir, "fin_aud_1pcap_lest.srt")
        output_mov = os.path.join(base_dir, "fin_aud_1pcap_lest.mov")

    # 1. Chạy PupCaps
    # Sử dụng css_file_path đã được tạo/cập nhật
    command = f'pupcaps {srt_input} -s {css_file_path} -w {width} -h {height} --output {output_mov}'
    print(f"\n--- Running PupCaps Step 10 ({s10mode.upper()}) ---\n")
    print(f"Command: {command}")

    try:
        subprocess.run(command, shell=True, check=True)
        print(f"\n    --> [SUCCESS] Generated: {output_mov}\n")

        # # 2. Xử lý ghép Audio nếu là mode FULL
        # if s10mode == "full":
        #     # Tìm file audio có dạng final_audio_*.wav
        #     audio_files = glob.glob(os.path.join(base_dir, "final_audio_*.wav"))

        #     if not audio_files:
        #         print(f"    --> [WARNING] Không tìm thấy file audio .wav nào trong {base_dir} để ghép!")
        #         return
        #     else:
        #         # Lấy file đầu tiên tìm thấy
        #         audio_input = audio_files[0]
        #         output_mp4 = os.path.join(base_dir, "fin_aud_1pcap.mp4")

        #         print(f"    --> [INFO] Found audio file: {audio_input}")
        #         print(f"    --> [INFO] Encoding to MP4 with Audio...")

        #         # Lệnh FFmpeg ghép audio và convert sang mp4 (yuv420p để tương thích mọi thiết bị)
        #         ffmpeg_cmd = (
        #             f'ffmpeg -hwaccel dxva2 -y -i {output_mov} -i {audio_input} '
        #             f'{HWGPU}-pix_fmt yuv420p ' # <-- THAY ĐỔI Ở ĐÂY
        #             f'-c:a aac -b:a 192k -shortest {output_mp4}'
        #         )

        #         subprocess.run(ffmpeg_cmd, shell=True, check=True)
        #         print(f"\n    --> [SUCCESSFULLY COMPLETE] Final Video: {output_mp4}\n")

        # elif s10mode == "test":
        #     print(f"        --> [TIP] Use 'python.exe scripts.py 10 full' to generate final MP4 with audio.\n")

    except subprocess.CalledProcessError as e:
        print(f"\n    --> [ERROR] Process failed with error code {e.returncode}")
        return
    except Exception as e:
        print(f"\n    --> [ERROR] An unexpected error occurred: {e}")
        return

    def _find_longest_line_start_time(srt_path):
        """Lấy mốc thời gian từ frame thứ 5 trong SRT (ưu tiên end-time, định dạng HH:MM:SS)."""
        try:
            with open(srt_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return None

        blocks = re.split(r"\n\s*\n", content.strip())
        frame_index = 5  # luôn lấy mốc từ timerframe 5

        for block in blocks:
            lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
            if len(lines) < 2:
                continue

            if lines[0] != str(frame_index):
                continue

            timing_line = lines[1]
            m = re.match(r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})", timing_line)
            if not m:
                continue

            end_time = m.group(2)
            return end_time.split(",")[0]

        return None

    def _find_longest_line_start_time1(srt_path):
        """Lấy mốc thời gian từ frame thứ 2 trong SRT (ưu tiên end-time, định dạng HH:MM:SS)."""
        try:
            with open(srt_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return None

        blocks = re.split(r"\n\s*\n", content.strip())
        frame_index = 2  # luôn lấy mốc từ timerframe 2

        for block in blocks:
            lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
            if len(lines) < 2:
                continue

            if lines[0] != str(frame_index):
                continue

            timing_line = lines[1]
            m = re.match(r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})", timing_line)
            if not m:
                continue

            end_time = m.group(2)
            return end_time.split(",")[0]

        return None

    # Export preview PNG có viền đỏ
    if s10mode == "test":
        try:
            longest_start_time1 = _find_longest_line_start_time1(srt_input)
            if longest_start_time1:
                png_output = os.path.join(base_dir, "fin_aud_1pcap_lest1.png")
                longest_start_ffmpeg1 = longest_start_time1.replace(",", ".")
                ffmpeg_preview_cmd = (
                    f'ffmpeg -y -ss {longest_start_ffmpeg1} -i "{output_mov}" '
                    f'-filter_complex '
                    f'"color=c=white:s=1920x1080[bg];'
                    f'[bg][0:v]overlay=0:0,'
                    f'drawbox=x=0:y=0:w=1920:h=1080:color=red@1.0:thickness=4" '
                    f'-frames:v 1 "{png_output}"'
                )
                print(f"        --> [INFO] Export longest-line preview at {longest_start_time1}...")
                subprocess.run(ffmpeg_preview_cmd, shell=True, check=True)
                print(f"    --> [SUCCESS] Generated preview: {png_output}")
            else:
                print(f"        --> [WARNING] Không tìm được timestamp câu dài nhất trong {srt_input}")

            longest_start_time = _find_longest_line_start_time(srt_input)
            if longest_start_time:
                png_output_longest = os.path.join(base_dir, "fin_aud_1pcap_lest2.png")
                longest_start_ffmpeg = longest_start_time.replace(",", ".")
                ffmpeg_longest_cmd = (
                    f'ffmpeg -y -ss {longest_start_ffmpeg} -i "{output_mov}" '
                    f'-filter_complex '
                    f'"color=c=white:s=1920x1080[bg];'
                    f'[bg][0:v]overlay=0:0,'
                    f'drawbox=x=0:y=0:w=1920:h=1080:color=red@1.0:thickness=4" '
                    f'-frames:v 1 "{png_output_longest}"'
                )
                print(f"        --> [INFO] Export longest-line preview at {longest_start_time}...")
                subprocess.run(ffmpeg_longest_cmd, shell=True, check=True)
                print(f"    --> [SUCCESS] Generated longest-line preview: {png_output_longest}")
            else:
                print(f"        --> [WARNING] Không tìm được timestamp câu dài nhất trong {srt_input}")
        except Exception as e:
            print(f"        --> [WARNING] Failed to export preview PNG: {e}")

    print("--- Step 10 Finished ---\n")
    step_pass_small_2l()
    printf("\nPLEASE_USE: 'python.exe scripts.py 11' TO RUN NEXT STEP\n")

def gen_fin_aud_1pcap(fontsize: int, spacing: int, css_output_path: str):
    """
    Tạo nội dung cho file fin_aud_1pcap.css với font-size và letter-spacing tùy chỉnh.
    """
    css_content = f"""
/* --- 1. KHOÁ CHẶT THẺ GỐC CỦA TRÌNH DUYỆT (HTML) --- */
html {{
    width: 1920px !important;
    height: 1080px !important;
    margin: 0 !important;
    padding: 0 !important;
    /* Cấm tuyệt đối Javascript can thiệp làm mờ thẻ gốc */
    opacity: 1 !important;
    visibility: visible !important;
}}

/* --- 2. TẠO MÀN CHIẾU PHÔNG XANH GẮN CHẶT VÀO HTML --- */
html::before {{
    content: "" !important;
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 1920px !important;
    height: 1080px !important;

    /* Màu phông xanh và Viền đỏ */
    background-color: rgba(0, 0, 0, 0) !important;
    border: 0px solid #FF0000 !important;
    box-sizing: border-box !important;

    /* Luôn hiển thị và nằm dưới cùng */
    display: block !important;
    z-index: -9999 !important;
    pointer-events: none !important;
}}

/* --- 3. ĐẢM BẢO BODY VÀ VIDEO KHÔNG LÀM PHIỀN --- */
body {{
    margin: 0 !important;
    padding: 0 !important;
    width: 100% !important;
    height: 100% !important;
}}

#video {{
    display: flex;
    flex-direction: column;
    position: relative;
    width: 1920px;
    height: 1080px;
}}

.captions {{
    position: absolute;
    white-space: nowrap;
    transform: translateX(-50%) rotate(0deg);
    left: 50%;
    bottom: 50px;
}}

/* 1. ĐỊNH DẠNG CHỮ GỐC */
.word {{
    display: inline-block;                  /*scale / animate từng từ độc lập*/
    font-family: 'Inter', sans-serif;
    font-size: {fontsize}px; /* <--- Đã tùy chỉnh */
    font-weight: 900;                       /*font-weight: bold;*/ /*Inter chỉ hỗ trợ tới 900*/

    color: #FFFF00;
    text-shadow: -4px -4px 0 #000, 4px -4px 0 #000, -4px 4px 0 #000, 4px 4px 0 #000;
    transform: scale(1, 1.2);

    letter-spacing: {spacing}px; /* <--- Đã tùy chỉnh */
    margin: 0 5px;                          /*khoảng cách giữa các word*/

    padding: 10px 10px;                     /*khoảng trống bên trong*/
    line-height: 0.9;                       /*padding cao hơn when > 1.0*/

    /*Animation: transform → hiệu ứng nảy mượt; color → đổi màu gần như instant*/
    transition: transform 0.15s cubic-bezier(0.175, 0.885, 0.32, 1.275), color 0.01s ease-in;
    /*scale X = 1; scale Y = 1.1 → chữ cao hơn bình thường*/
}}

.word.before-highlighted {{
    color: #FFFF00; /* Màu vàng */
    text-shadow: -4px -4px 0 #000, 4px -4px 0 #000, -4px 4px 0 #000, 4px 4px 0 #000;
    transform: scale(1, 1.2);
}}

/* 2. HIỆU ỨNG KHI ĐỌC TỚI */
.word.highlighted {{
    color: white;
    text-shadow: -4px -4px 0 #000, 4px -4px 0 #000, -4px 4px 0 #000, 4px 4px 0 #000;
    transform: scale(1.05, 1.2) translateY(-8px); /* Nảy to và nhích lên trên */

    background-color: rgba(0, 0, 255, 1.0); /*background-color: transparent;*/
    border-radius: 32px;   /* bo góc borger */
    padding: 4px 8px;       /* phải có padding để thấy nền của border */
}}

.word.after-highlighted {{
    color: #FFFF00; /* Màu vàng */
    text-shadow: -4px -4px 0 #000, 4px -4px 0 #000, -4px 4px 0 #000, 4px 4px 0 #000;
    transform: scale(1, 1.2);
}}
"""
    with open(css_output_path, "w", encoding="utf-8") as f:
        f.write(css_content)
    print(f"    --> Generated CSS file: {css_output_path} with font-size={fontsize}px, letter-spacing={spacing}px")

#===============================================================================   █      █
#===============================================================================  ██     ██
#===============================================================================   █      █
#===============================================================================   █      █
#===============================================================================██████ ██████
def run_pupcaps_step11(s11mode="full", m_size=140, w_size=140, m_space=-5, w_space=-5, m_align="RIGHT", m_anchor=960, w_align="LEFT", w_anchor=960):
    print(f"\n--- Step 11: Gen Separate SRT & Test Mode ---")

    printf("s11mode:  ", s11mode)
    printf("m_size:   ", m_size)
    printf("w_size:   ", w_size)
    printf("m_space:  ", m_space)
    printf("w_space:  ", w_space)
    printf("m_align:  ", m_align)
    printf("w_align:  ", w_align)
    printf("m_anchor: ", m_anchor)
    printf("w_anchor: ", w_anchor)

    MAN_SIZE_LOC    = m_size
    M_spacing_loc   = m_space
    MAN_ALIGN       = str(m_align).upper() #LEFT/RIGHT/CENTER
    WOMAN_SIZE_LOC  = w_size
    W_spacing_loc   = w_space
    WOMAN_ALIGN     = str(w_align).upper()

    #printf("MAN_ALIGN: ", MAN_ALIGN)
    #printf("WOMAN_ALIGN: ", WOMAN_ALIGN)

    # 1. Định nghĩa Tọa độ và Màu sắc cho MAN
    MAN_SIZE        = str(MAN_SIZE_LOC)+"px"
    M_spacing       = str(M_spacing_loc)+"px"
    MAN_HOOK        = {"x": m_anchor, "y": MAN_SIZE_LOC}
    MAN_START       = {"x": m_anchor, "y": MAN_SIZE_LOC}
    MAN_MAIN        = {"x": m_anchor, "y": MAN_SIZE_LOC}
    MAN_BYE         = {"x": m_anchor, "y": MAN_SIZE_LOC}
    MAN_COLOR       = "rgba(0, 0, 0, 1.0)"
    MAN_TEST_CSS    = "./fin_aud_2man_lest.css"
    MAN_TEST_SRT    = "./audio_ffmpegs/fin_aud_2man_lest.srt"
    MAN_TEST_MOV    = "./audio_ffmpegs/fin_aud_2man_lest.mov"
    MAN_TEST_MP4    = "./audio_ffmpegs/fin_aud_2man_lest.mp4"
    MAN_FULL_CSS    = "./fin_aud_2man.css"
    MAN_FULL_SRT    = "./audio_ffmpegs/fin_aud_2man.srt"
    MAN_FULL_MOV    = "./audio_ffmpegs/fin_aud_2man.mov"
    MAN_FULL_MP4    = "./audio_ffmpegs/fin_aud_2man.mp4"

    # 2. Định nghĩa Tọa độ và Màu sắc cho WOMAN
    WOMAN_SIZE      = str(WOMAN_SIZE_LOC)+"px"
    W_spacing       = str(W_spacing_loc)+"px"
    WOMAN_HOOK      = {"x": w_anchor, "y": WOMAN_SIZE_LOC}
    WOMAN_START     = {"x": w_anchor, "y": WOMAN_SIZE_LOC}
    WOMAN_MAIN      = {"x": w_anchor, "y": WOMAN_SIZE_LOC}
    WOMAN_BYE       = {"x": w_anchor, "y": WOMAN_SIZE_LOC}
    WOMAN_COLOR     = "rgba(0, 0, 255, 1.0)"
    WOMAN_TEST_CSS  = "./fin_aud_2woman_lest.css"
    WOMAN_TEST_SRT  = "./audio_ffmpegs/fin_aud_2woman_lest.srt"
    WOMAN_TEST_MOV  = "./audio_ffmpegs/fin_aud_2woman_lest.mov"
    WOMAN_TEST_MP4  = "./audio_ffmpegs/fin_aud_2woman_lest.mp4"
    WOMAN_FULL_CSS  = "./fin_aud_2woman.css"
    WOMAN_FULL_SRT  = "./audio_ffmpegs/fin_aud_2woman.srt"
    WOMAN_FULL_MOV  = "./audio_ffmpegs/fin_aud_2woman.mov"
    WOMAN_FULL_MP4  = "./audio_ffmpegs/fin_aud_2woman.mp4"

    if      MAN_ALIGN=="LEFT"       : malign_code="(0%, -100%)"
    elif    MAN_ALIGN=="CENTER"     : malign_code="(-50%, -100%)"
    elif    MAN_ALIGN=="RIGHT"      : malign_code="(-100%, -100%)"

    if      WOMAN_ALIGN=="LEFT"     : walign_code="(0%, -100%)"
    elif    WOMAN_ALIGN=="CENTER"   : walign_code="(-50%, -100%)"
    elif    WOMAN_ALIGN=="RIGHT"    : walign_code="(-100%, -100%)"

    convert_1920_1080()

    # A. Thực hiện tách file SRT và lấy mốc ID
    report = separate_2_srt()
    # DEBUG
    #with open("123.test", "w", encoding="utf-8") as f: f.write(str(report))

    # sync timeline from _1pcap.srt
    sync_timeline()

    # B. Gán 16 biến ID cho Man và Woman từ report
    # MAN
    S_H_M, E_H_M = report['man']['1_HOOK']
    S_S_M, E_S_M = report['man']['2_START']
    S_M_M, E_M_M = report['man']['3_MAIN']
    S_B_M, E_B_M = report['man']['4_BYE']
    # WOMAN
    S_H_W, E_H_W = report['woman']['1_HOOK']
    S_S_W, E_S_W = report['woman']['2_START']
    S_M_W, E_M_W = report['woman']['3_MAIN']
    S_B_W, E_B_W = report['woman']['4_BYE']

    # 3. Nếu là mode TEST, thực hiện tạo CSS và chạy video cho MAN (Longest)
    if s11mode == "test":
        if GENDER=="man":
            print("    [MODE TEST] Generating CSS and Video for only MAN ...")
            gen_fin_aud_2lest(MAN_HOOK, MAN_START, MAN_MAIN, MAN_BYE, MAN_SIZE, MAN_COLOR, MAN_TEST_CSS, malign_code, M_spacing)
            run_fin_aud_2lest(MAN_TEST_CSS, MAN_TEST_SRT, MAN_TEST_MOV, MAN_TEST_MP4)
        elif GENDER=="woman":
            print("    [MODE TEST] Generating CSS and Video for only WOMAN ...")
            gen_fin_aud_2lest(WOMAN_HOOK, WOMAN_START, WOMAN_MAIN, WOMAN_BYE, WOMAN_SIZE, WOMAN_COLOR, WOMAN_TEST_CSS, walign_code, W_spacing)
            run_fin_aud_2lest(WOMAN_TEST_CSS, WOMAN_TEST_SRT, WOMAN_TEST_MOV, WOMAN_TEST_MP4)
        else:
            print("    [MODE TEST] Generating CSS and Video for MAN/WOMAN in parallel...")

            thread_errors = []

            def run_man_test():
                try:
                    print("    [MODE TEST] [MAN] Start...")
                    gen_fin_aud_2lest(MAN_HOOK, MAN_START, MAN_MAIN, MAN_BYE, MAN_SIZE, MAN_COLOR, MAN_TEST_CSS, malign_code, M_spacing)
                    run_fin_aud_2lest(MAN_TEST_CSS, MAN_TEST_SRT, MAN_TEST_MOV, MAN_TEST_MP4)
                    print("    [MODE TEST] [MAN] Done.")
                except Exception as e:
                    thread_errors.append(("man", str(e)))

            def run_woman_test():
                try:
                    print("    [MODE TEST] [WOMAN] Start...")
                    gen_fin_aud_2lest(WOMAN_HOOK, WOMAN_START, WOMAN_MAIN, WOMAN_BYE, WOMAN_SIZE, WOMAN_COLOR, WOMAN_TEST_CSS, walign_code, W_spacing)
                    run_fin_aud_2lest(WOMAN_TEST_CSS, WOMAN_TEST_SRT, WOMAN_TEST_MOV, WOMAN_TEST_MP4)
                    print("    [MODE TEST] [WOMAN] Done.")
                except Exception as e:
                    thread_errors.append(("woman", str(e)))

            man_thread = threading.Thread(target=run_man_test, name="step11-test-man-thread")
            woman_thread = threading.Thread(target=run_woman_test, name="step11-test-woman-thread")

            man_thread.start()
            woman_thread.start()

            man_thread.join()
            woman_thread.join()

            if thread_errors:
                for role, err in thread_errors:
                    print(f"    [MODE TEST] [{role.upper()}] ERROR: {err}")
                raise RuntimeError("Step11 test parallel render failed. Check logs above.")

    # 4. Mode FULL
    elif s11mode == "full":
        if GENDER=="man":
            print("    [MODE FULL] Generating CSS and Video for only MAN...")
            gen_fin_aud_2full(MAN_HOOK, MAN_START, MAN_MAIN, MAN_BYE, MAN_SIZE, MAN_COLOR, MAN_FULL_CSS, S_H_M, E_H_M, S_S_M, E_S_M, S_M_M, E_M_M, S_B_M, E_B_M, malign_code, M_spacing)
            run_fin_aud_2full(MAN_FULL_CSS, MAN_FULL_SRT, MAN_FULL_MOV, MAN_FULL_MP4, report, "man")
        elif GENDER=="woman":
            print("    [MODE FULL] Generating CSS and Video for only WOMAN...")
            gen_fin_aud_2full(WOMAN_HOOK, WOMAN_START, WOMAN_MAIN, WOMAN_BYE, WOMAN_SIZE, WOMAN_COLOR, WOMAN_FULL_CSS, S_H_W, E_H_W, S_S_W, E_S_W, S_M_W, E_M_W, S_B_W, E_B_W, walign_code, W_spacing)
            run_fin_aud_2full(WOMAN_FULL_CSS, WOMAN_FULL_SRT, WOMAN_FULL_MOV, WOMAN_FULL_MP4, report, "woman")
        else:
            print("    [MODE FULL] Generating CSS and Video for MAN/WOMAN in parallel...")

            thread_errors = []

            def run_man_full():
                try:
                    print("    [MODE FULL] [MAN] Start...")
                    gen_fin_aud_2full(MAN_HOOK, MAN_START, MAN_MAIN, MAN_BYE, MAN_SIZE, MAN_COLOR, MAN_FULL_CSS, S_H_M, E_H_M, S_S_M, E_S_M, S_M_M, E_M_M, S_B_M, E_B_M, malign_code, M_spacing)
                    run_fin_aud_2full(MAN_FULL_CSS, MAN_FULL_SRT, MAN_FULL_MOV, MAN_FULL_MP4, report, "man")
                    print("    [MODE FULL] [MAN] Done.")
                except Exception as e:
                    thread_errors.append(("man", str(e)))

            def run_woman_full():
                try:
                    print("    [MODE FULL] [WOMAN] Start...")
                    gen_fin_aud_2full(WOMAN_HOOK, WOMAN_START, WOMAN_MAIN, WOMAN_BYE, WOMAN_SIZE, WOMAN_COLOR, WOMAN_FULL_CSS, S_H_W, E_H_W, S_S_W, E_S_W, S_M_W, E_M_W, S_B_W, E_B_W, walign_code, W_spacing)
                    run_fin_aud_2full(WOMAN_FULL_CSS, WOMAN_FULL_SRT, WOMAN_FULL_MOV, WOMAN_FULL_MP4, report, "woman")
                    print("    [MODE FULL] [WOMAN] Done.")
                except Exception as e:
                    thread_errors.append(("woman", str(e)))

            man_thread = threading.Thread(target=run_man_full, name="step11-man-thread")
            woman_thread = threading.Thread(target=run_woman_full, name="step11-woman-thread")

            man_thread.start()
            woman_thread.start()

            man_thread.join()
            woman_thread.join()

            if thread_errors:
                raise RuntimeError(f"Step 11 parallel full mode failed: {thread_errors}")

    print("--- Step 11 Finished ---\n")
    step_pass_small_2l()
    printf("\nPLEASE_USE: 'python.exe scripts.py 12' TO RUN NEXT STEP\n")

def gen_fin_aud_2full(HOOK, START, MAIN, BYE, SIZE, COLOR, CSS_PATH, SH, EH, SS, ES, SM, EM, SB, EB, ALIGN, SPACING):
    css_content = f"""
html {{ width: 1920px !important; height: 1080px !important; margin: 0; padding: 0; }}
html::before {{
    content: "" !important; position: fixed; top: 0; left: 0; width: 1920px; height: 1080px;
    background-color: rgba(0, 0, 0, 0) !important; z-index: -9999;
}}
#video {{ position: relative; width: 1920px; height: 1080px; overflow: hidden; }}
.captions {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; }}

.word {{
    display: inline-block; font-family: 'Inter', sans-serif; font-size: {SIZE}; font-weight: 900;
    color: {COLOR}; transform: scale(1.0, 1.2); letter-spacing: {SPACING};
    background-color: rgba(255, 255, 255, 1.0); border-radius: 32px; padding: 0px 15px 12px 15px; line-height: 0.75;
}}

/* --- VỊ TRÍ 4 GIAI ĐOẠN --- */
.caption.pup-indexes-{SH}-{EH} {{
    position: absolute !important; left: {HOOK['x']}px !important; top: {HOOK['y']}px !important;
    transform: translate{ALIGN} rotate(0deg) !important;
}}

.caption.pup-indexes-{SS}-{ES} {{
    position: absolute !important; left: {START['x']}px !important; top: {START['y']}px !important;
    transform: translate{ALIGN} rotate(0deg) !important;
}}

.caption.pup-indexes-{SM}-{EM} {{
    position: absolute !important; left: {MAIN['x']}px !important; top: {MAIN['y']}px !important;
    transform: translate{ALIGN} rotate(0deg) !important;
}}

.caption.pup-indexes-{SB}-{EB} {{
    position: absolute !important; left: {BYE['x']}px !important; top: {BYE['y']}px !important;
    transform: translate{ALIGN} rotate(0deg) !important;
}}
"""
    with open(CSS_PATH, "w", encoding="utf-8") as f:
        f.write(css_content)

def run_fin_aud_2full(CSS, SRT, MOV, MP4, report, speaker):
    """
    Quy trình Full:
    1. Chạy Pupcaps tạo MOV nền xanh. (Lưu ý: Theo cập nhật mới MOV đã trong suốt)
    2. Quét SRT tìm thời điểm bắt đầu của các Stage dựa trên ID từ report.
    3. Dùng FFmpeg ghép 4 ảnh nền chuyển cảnh theo thời gian thực + Chèn Audio.
    """

    # --- BƯỚC 1: CHẠY PUPCAPS (Giữ nguyên) ---
    print(f"    --> [1/3] Running Pupcaps for {speaker.upper()} Full...")
    pup_cmd = f'pupcaps "{SRT}" -s "{CSS}" -w 1920 -h 1080 --output "{MOV}"'
    try:
        subprocess.run(pup_cmd, shell=True, check=True)
    except subprocess.CalledProcessError:
        print(f"    [ERROR] Pupcaps failed for {speaker}")
        return

    # # --- BƯỚC 2: PHÂN TÍCH TIMELINE TỪ SRT (Giữ nguyên) ---
    # print(f"    --> [2/3] Analyzing stage transitions from SRT...")
    # with open(SRT, "r", encoding="utf-8") as f:
    #     srt_content = f.read()

    # def get_start_time_of_id(target_id):
    #     if target_id == 0: return 999999
    #     pattern = rf"^{target_id}\r?\n(\d{{2}}:\d{{2}}:\d{{2}},\d{{3}}) -->"
    #     match = re.search(pattern, srt_content, re.MULTILINE)
    #     if match:
    #         return time_to_seconds(match.group(1))
    #     return 999999

    # id_start = report[speaker]['2_START'][0]
    # id_main  = report[speaker]['3_MAIN'][0]
    # id_bye   = report[speaker]['4_BYE'][0]

    # t_start = get_start_time_of_id(id_start)
    # t_main  = get_start_time_of_id(id_main)
    # t_bye   = get_start_time_of_id(id_bye)

    # all_times = re.findall(r"--> (\d{2}:\d{2}:\d{2},\d{3})", srt_content)
    # total_duration = time_to_seconds(all_times[-1]) if all_times else 0

    # # --- BƯỚC 3: GHÉP NỀN VÀ AUDIO BẰNG FFMPEG ---
    # print(f"    --> [3/3] Merging Backgrounds, Audio and removing GreenScreen...")

    # # Tìm file audio (tự động nhận diện xxx)
    # audio_search = glob.glob(os.path.join("audio_ffmpegs", "final_audio_*.wav"))
    # audio_path = audio_search[0] if audio_search else None

    # # Lấy độ dài theo Audio bằng ffprobe
    # output_duration = total_duration + 0.05 # Backup bằng total_duration cũ nếu không có audio
    # if audio_path:
    #     try:
    #         probe_cmd = [
    #             "ffprobe", "-v", "error", "-show_entries",
    #             "format=duration", "-of",
    #             "default=noprint_wrappers=1:nokey=1", audio_path
    #         ]
    #         probe_out = subprocess.check_output(probe_cmd).decode("utf-8").strip()
    #         output_duration = float(probe_out)
    #     except Exception as e:
    #         print(f"    [WARNING] Lỗi lấy độ dài audio, dùng độ dài SRT: {e}")

    # imgs = ["./img1_HOOK.jpg", "./img2_INFO.jpg", "./img3_MAIN.jpg", "./img4_BYE.jpg"]

    # # Đã xóa colorkey, gọi thẳng [0:v] vì MOV đã có nền trong suốt
    # filter_complex = (
    #     f"[1:v]scale=1920:1080,setsar=1,format=rgba[i1];"
    #     f"[2:v]scale=1920:1080,setsar=1,format=rgba[i2];"
    #     f"[3:v]scale=1920:1080,setsar=1,format=rgba[i3];"
    #     f"[4:v]scale=1920:1080,setsar=1,format=rgba[i4];"
    #     f"[i1][i2]overlay=enable='between(t,{t_start},99999)'[bg1];"
    #     f"[bg1][i3]overlay=enable='between(t,{t_main},99999)'[bg2];"
    #     f"[bg2][i4]overlay=enable='between(t,{t_bye},99999)'[bg3];"
    #     f"[bg3][0:v]overlay=x=0:y=0:shortest=1[outv]"
    # )

    # # Khởi tạo lệnh FFmpeg
    # ffmpeg_cmd = [
    #     "ffmpeg", "-y",
    #     "-i", MOV,                                          # Input 0: MOV trong suốt
    #     "-framerate", "30", "-loop", "1", "-i", imgs[0],    # Input 1
    #     "-framerate", "30", "-loop", "1", "-i", imgs[1],    # Input 2
    #     "-framerate", "30", "-loop", "1", "-i", imgs[2],    # Input 3
    #     "-framerate", "30", "-loop", "1", "-i", imgs[3],    # Input 4
    # ]

    # # Thêm input audio nếu tìm thấy
    # if audio_path:
    #     ffmpeg_cmd.extend(["-i", audio_path]) # Input 5

    # ffmpeg_cmd.extend([
    #     "-filter_complex", filter_complex,
    #     "-map", "[outv]",               # Lấy video từ filter complex
    # ])

    # # Map audio và cấu hình codec
    # if audio_path:
    #     ffmpeg_cmd.extend(["-map", "5:a", "-c:a", "aac", "-b:a", "192k"])

    # # Xuất độ dài video (-t) dựa trên output_duration (độ dài Audio lấy từ trên)
    # ffmpeg_cmd.extend(["-pix_fmt", "yuv420p",])
    # ffmpeg_cmd.extend(HWGPU.strip().split())
    # ffmpeg_cmd.extend(["-t", str(output_duration), MP4])

    # try:
    #     subprocess.run(ffmpeg_cmd, check=True)
    #     print(f"    --> [SUCCESS] Final MP4 created with Audio: {MP4}")
    # except subprocess.CalledProcessError as e:
    #     print(f"    [ERROR] FFmpeg merge failed: {e}")

def gen_fin_aud_2lest(HOOK, START, MAIN, BYE, SIZE, COLOR, CSS, ALIGN, SPACING):
    css_path = CSS

    css_content = f"""
/* --- 1. KHOÁ CHẶT THẺ GỐC CỦA TRÌNH DUYỆT (HTML) --- */
html {{
    width: 1920px !important;
    height: 1080px !important;
    margin: 0 !important;
    padding: 0 !important;
    opacity: 1 !important;
    visibility: visible !important;
}}

/* --- 2. TẠO MÀN CHIẾU PHÔNG XANH GẮN CHẶT VÀO HTML --- */
html::before {{
    content: "" !important;
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 1920px !important;
    height: 1080px !important;
    background-color: rgba(0, 0, 0, 0) !important;
    display: block !important;
    z-index: -9999 !important;
    pointer-events: none !important;
}}

body {{
    margin: 0 !important;
    padding: 0 !important;
    width: 100% !important;
    height: 100% !important;
}}

#video {{
    position: relative;
    width: 1920px;
    height: 1080px;
    overflow: hidden;
}}

.captions {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
}}

/* 1. ĐỊNH DẠNG CHỮ GỐC */
.word {{
    display: inline-block;
    font-family: 'Inter', sans-serif;
    font-size: {SIZE};
    font-weight: 900;

    color: {COLOR}; /* Sử dụng biến màu được truyền vào */
    transform: scale(1.0, 1.2);

    letter-spacing: {SPACING};
    background-color: rgba(255, 255, 255, 1.0);
    border-radius: 32px;
    padding: 0px 2px 8px 2px; /* đẩy chữ lên: Trên 0px, Phải 2px, Dưới 8px, Trái 2px */
    line-height: 0.8;
}}

/* --- VỊ TRÍ 4 CAPTIONS --- */
.caption.pup-indexes-1 {{
    position: absolute !important; left: {HOOK['x']}px !important; top: {HOOK['y']}px !important;
    transform: translate{ALIGN} rotate(0deg) !important;
}}

.caption.pup-indexes-2 {{
    position: absolute !important; left: {START['x']}px !important; top: {START['y']}px !important;
    transform: translate{ALIGN} rotate(0deg) !important;
}}

.caption.pup-indexes-3 {{
    position: absolute !important; left: {MAIN['x']}px !important; top: {MAIN['y']}px !important;
    transform: translate{ALIGN} rotate(0deg) !important;
}}

.caption.pup-indexes-4 {{
    position: absolute !important; left: {BYE['x']}px !important; top: {BYE['y']}px !important;
    transform: translate{ALIGN} rotate(0deg) !important;
}}
"""
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(css_content)
    print(f"    --> Created CSS: {css_path}")

def run_fin_aud_2lest(CSS, SRT, MOV, MP4):
    css_file    = CSS
    srt_file    = SRT
    mov_output  = MOV
    mp4_output  = MP4

    # 1. Chạy Pupcaps
    print(f"    --> Running Pupcaps to create MOV...")
    pup_cmd = f"pupcaps {srt_file} -s {css_file} -w 1920 -h 1080 --output {mov_output}"
    subprocess.run(pup_cmd, shell=True, check=True)

    # 2. Lấy timeline từ file SRT vừa tạo
    with open(srt_file, "r", encoding="utf-8") as f:
        srt_content = f.read()
    times = re.findall(r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})", srt_content)

    t = []
    for i in range(4):
        if i < len(times):
            t.append({'s': time_to_seconds(times[i][0]), 'e': time_to_seconds(times[i][1])})
        else:
            t.append({'s': 0, 'e': 0})

    total_duration = t[3]['e'] if len(t) > 3 else 2.0

    # Danh sách ảnh tương ứng 4 phần
    imgs = ["./img1_HOOK.jpg", "./img2_INFO.jpg", "./img3_MAIN.jpg", "./img4_BYE.jpg"]

    # 3. Ghép ảnh và Video (ChromaKey khử nền xanh)
    filter_complex = (
        f"[1:v]scale=1920:1080,setsar=1,format=rgba[i1];"
        f"[2:v]scale=1920:1080,setsar=1,format=rgba[i2];"
        f"[3:v]scale=1920:1080,setsar=1,format=rgba[i3];"
        f"[4:v]scale=1920:1080,setsar=1,format=rgba[i4];"

        # Background timeline
        f"[i1][i2]overlay=enable='between(t,{t[1]['s']},99999)'[bg1];"
        f"[bg1][i3]overlay=enable='between(t,{t[2]['s']},99999)'[bg2];"
        f"[bg2][i4]overlay=enable='between(t,{t[3]['s']},99999)'[bg3];"

        # Overlay subtitle MOV lên background
        f"[bg3][0:v]overlay=x=0:y=0:shortest=1[outv]"
    )

    # Thêm "-pix_fmt yuv420p" nếu nó chưa có trong HWGPU và là cần thiết
    # (ví dụ: libx264 cần nó, h264_amf/qsv thường ngầm định hoặc tự chọn nếu không chỉ định)
    # Để đơn giản, ta luôn thêm nó sau các tùy chọn codec, trừ khi nó đã được HWGPU bao gồm rõ ràng.
    if "-pix_fmt" not in HWGPU:
        hwgpu_args.extend(["-pix_fmt", "yuv420p"])

    # Lệnh FFmpeg dạng danh sách
    ffmpeg_cmd = [
        "ffmpeg", "-y",

        "-i", mov_output,

        "-framerate", "30", "-loop", "1", "-i", imgs[0],
        "-framerate", "30", "-loop", "1", "-i", imgs[1],
        "-framerate", "30", "-loop", "1", "-i", imgs[2],
        "-framerate", "30", "-loop", "1", "-i", imgs[3],

        "-filter_complex", filter_complex,
        "-map", "[outv]",
    ]

    # Chèn các đối số từ HWGPU và -pix_fmt
    ffmpeg_cmd.extend(hwgpu_args)

    # Tiếp tục với các đối số còn lại
    ffmpeg_cmd.extend([
        "-t", str(total_duration + 0.1),
        mp4_output
    ])

    print(f"    --> Merging Images with Scale and ChromaKey...")
    subprocess.run(ffmpeg_cmd, check=True)
    print(f"    --> [SUCCESS] Final Video with Backgrounds: {mp4_output}")

def separate_2_srt():
    script_yt_path = "./scripts.yt"
    master_srt_path = "./audio_ffmpegs/fin_aud_2ali.srt"
    output_dir = "./audio_ffmpegs"
    DEBUG_PARSE_LIMIT = 20

    stage_map = {
        "HOOK": "1_HOOK", "INFO": "2_START", "START": "2_START",
        "MAIN": "3_MAIN", "BYE": "4_BYE"
    }

    if not os.path.exists(script_yt_path) or not os.path.exists(master_srt_path):
        print("    [ERROR] Missing input file!")
        return

    #---------------------------------------------------------------------------
    # --- BƯỚC 1: TRÍCH XUẤT TỪ TRONG SCRIPT VÀ TÌM TỪ DÀI NHẤT ---
    with open(script_yt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    script_words = []
    dropped_words = []
    unknown_speaker_lines = []
    parse_debug_rows = []
    speaker_counter = {"man": 0, "woman": 0}
    longest_word_text = {
        "man": {v: "" for v in stage_map.values()},
        "woman": {v: "" for v in stage_map.values()}
    }
    # DEBUG
    #printf("longest_word_text: ", longest_word_text)

    def detect_speaker(label):
        """
        Detect speaker từ nhãn trước dấu ":" trong scripts.yt.
        Dùng token để tránh match nhầm MAN trong WOMAN.
        """
        u = label.upper()
        tokens = [t for t in re.split(r"[^A-ZÀ-Ỹ0-9]+", u) if t]

        if any(t in {"WOMAN", "NU", "NỮ"} for t in tokens):
            return "woman"
        if any(t in {"MAN", "NAM"} for t in tokens):
            return "man"
        return None

    current_stage = None
    line_no = 0
    for line in lines:
        line_no += 1
        l = line.strip()
        if not l or any(l.startswith(x) for x in ["#", "scripts =", '"""']): continue
        if l.upper() in stage_map:
            current_stage = l.upper()
            continue
        if ":" in l and current_stage:
            parts = l.split(":", 1)
            speaker = detect_speaker(parts[0])
            text_clean = re.sub(r'\(.*?\)', '', parts[1]).replace("[", "").replace("]", "").replace("...", " ")

            if len(parse_debug_rows) < DEBUG_PARSE_LIMIT:
                parse_debug_rows.append({
                    "line_no": line_no,
                    "stage": current_stage,
                    "label": parts[0].strip(),
                    "speaker": speaker,
                    "text_preview": text_clean.strip()[:80]
                })

            if not speaker:
                unknown_speaker_lines.append((line_no, parts[0].strip(), l))
                continue

            target_stage = stage_map[current_stage]
            for w in text_clean.split():
                norm_w = re.sub(r'[^a-z0-9]', '', w.lower())
                if norm_w:
                    script_words.append({'norm': norm_w, 'speaker': speaker, 'stage': target_stage, 'orig': w, 'line_no': line_no})
                    speaker_counter[speaker] += 1
                    # Đếm bao gồm cả dấu câu theo yêu cầu
                    if len(w) > len(longest_word_text[speaker][target_stage]):
                        longest_word_text[speaker][target_stage] = w
                else:
                    dropped_words.append((line_no, speaker, w))

    print("\n    [DEBUG] First parsed dialogue lines (up to 20):")
    for idx, row in enumerate(parse_debug_rows, 1):
        print(
            f"        #{idx:02d} line={row['line_no']} stage={row['stage']} "
            f"label='{row['label']}' -> speaker={row['speaker']} | text='{row['text_preview']}'"
        )

    print("    [DEBUG] Word distribution from scripts.yt:")
    print(f"        man_words   : {speaker_counter['man']}")
    print(f"        woman_words : {speaker_counter['woman']}")
    print(f"        unknown_speaker_lines: {len(unknown_speaker_lines)}")

    # Fail-fast nếu speaker không nhận diện được hoặc bị rớt word sau normalize
    if unknown_speaker_lines:
        print("\n    [ERROR] Có line không nhận diện được speaker trong scripts.yt:")
        for ln, lb, raw in unknown_speaker_lines[:20]:
            print(f"        - line {ln}: label='{lb}' | raw='{raw}'")
        if len(unknown_speaker_lines) > 20:
            print(f"        ... and {len(unknown_speaker_lines)-20} more lines")
        print("    --> Dừng để tránh lệch map Nam/Nữ.")
        return None

    if dropped_words:
        print("\n    [ERROR] Có word bị rớt sau normalize (norm_w=''):")
        for ln, sp, w in dropped_words[:30]:
            print(f"        - line {ln} [{sp}] word='{w}'")
        if len(dropped_words) > 30:
            print(f"        ... and {len(dropped_words)-30} more words")
        print("    --> Dừng để tránh lệch số lượng word script vs SRT.")
        return None
    # DEBUG
    #with open("123.test", "w", encoding="utf-8") as f: f.write(str(longest_word_text))
    #printf("longest_word_text: ", longest_word_text)

    # DEBUG
    #with open("234.test", "w", encoding="utf-8") as f: f.write(str(script_words))

    #---------------------------------------------------------------------------
    # --- BƯỚC 2: TRÍCH XUẤT SRT VÀ BỎ DUMMY ---
    with open(master_srt_path, "r", encoding="utf-8") as f:
        srt_raw = f.read().strip()
        # DEBUG
        #with open("123.test", "w", encoding="utf-8") as f: f.write(str(srt_raw))
    all_blocks_raw = re.findall(r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n((?:.+\n?)+)", srt_raw)
    # Bỏ block dummy/blank để tránh lệch 1-word-per-block
    all_blocks = [b for b in all_blocks_raw if clean_srt_text(b[2])]
    # DEBUG
    #with open("345.test", "w", encoding="utf-8") as f: f.write(str(all_blocks))
    #printf("all_blocks[0]: ", all_blocks[0])

    #---------------------------------------------------------------------------
    # --- BƯỚC 3: PHÂN PHỐI VÀO 2 THÙNG CHỨA VÀ LẤY BLOCK DÀI NHẤT ---
    final_data = {"man": [], "woman": []}
    longest_blocks_data = {
        "man": {v: None for v in stage_map.values()},
        "woman": {v: None for v in stage_map.values()}
    }
    report_map = {
        "man": {v: [0, 0] for v in stage_map.values()},
        "woman": {v: [0, 0] for v in stage_map.values()}
    }

    # Fail-fast nếu số lượng word lệch với số block SRT (1 word / block)
    if len(script_words) != len(all_blocks):
        print("\n    [ERROR] Mismatch số lượng word giữa script và fin_aud_2ali.srt")
        print(f"        - script_words: {len(script_words)}")
        print(f"        - srt_blocks  : {len(all_blocks)}")
        print("    [ALIGNMENT AUDIT] 20 phần tử đầu để dò điểm lệch:")
        max_audit = min(20, max(len(script_words), len(all_blocks)))
        for i in range(max_audit):
            sw = script_words[i] if i < len(script_words) else None
            sb = all_blocks[i] if i < len(all_blocks) else None
            sw_word = sw['orig'] if sw else '---'
            sw_spk = sw['speaker'] if sw else '---'
            sw_ln = sw['line_no'] if sw else '-'
            srt_word = clean_srt_text(sb[2]) if sb else '---'
            srt_time = sb[1] if sb else '---'
            print(f"        idx={i+1:04d} | script='{sw_word}' ({sw_spk},L{sw_ln}) | srt='{srt_word}' | {srt_time}")
        print("    --> Dừng để tránh lệch dây chuyền sang speaker sai.")
        return None

    srt_ptr = 0
    for s_word in script_words:
        if srt_ptr < len(all_blocks):
            sp = s_word['speaker']
            st = s_word['stage']
            block = all_blocks[srt_ptr]

            final_data[sp].append(block)
            new_id = len(final_data[sp])

            if report_map[sp][st][0] == 0: report_map[sp][st][0] = new_id
            report_map[sp][st][1] = new_id

            if s_word['orig'] == longest_word_text[sp][st] and longest_blocks_data[sp][st] is None:
                # DEBUG
                #printf("s_word['orig']: ", s_word['orig'])
                #printf("longest_word_text[sp][st]: ", longest_word_text[sp][st])
                #printf("block: ", block)
                longest_blocks_data[sp][st] = block
            srt_ptr += 1
    # DEBUG
    #printf("report_map: ", report_map)
    # DEBUG
    #with open("123.test", "w", encoding="utf-8") as f: f.write(str(longest_blocks_data))

    # --- BƯỚC 4: IN REPORT ---
    print(f"\n{'='*20} SRT SEPARATION REPORT {'='*20}\n")
    for sp in ["man", "woman"]:
        for st_key in sorted(set(stage_map.values())):
            start, end = report_map[sp][st_key]
            l_word = longest_word_text[sp][st_key]
            l_len = len(l_word)

            section_name = f"+ {sp}_{st_key}:"
            range_str = f"from {start:02d} - {end:02d}"
            word_info = f"{l_word} ({l_len} chars)" if l_word else "-"
            if start != 0:
                print(f"{section_name:<18} {range_str:<20} {word_info}")
            else:
                print(f"{section_name:<18} {'EMPTY':<20}")
        print("-" * 55)

    # --- BƯỚC 5: XUẤT FILE FULL VÀ FILE LONGEST ---
    def clean_caption_text(text):
        if text is None:
            return ""
        text = str(text)
        text = text.replace("\r", " ")
        text = text.replace("\n", " ")
        text = text.replace("[", "")
        text = text.replace("]", "")
        text = re.sub(r"<.*?>", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    for sp in ["man", "woman"]:
        # 1. Xuất file FULL
        full_name = f"fin_aud_2{sp}.srt"
        with open(os.path.join(output_dir, full_name), "w", encoding="utf-8") as f:
            valid_idx = 1
            for i, b in enumerate(final_data[sp], 1):
                try:
                    if len(b) < 3:
                        print(f"[BAD BLOCK] len<3 : {b}")
                        continue
                    timeline = str(b[1]).strip()
                    text = clean_caption_text(b[2])
                    # BAD TIMELINE
                    if " --> " not in timeline:
                        print(f"[BAD TIMELINE] {timeline}")
                        continue
                    # EMPTY TEXT
                    if not text:
                        print(f"[EMPTY TEXT] {i}")
                        continue
                    # TOO LONG
                    if len(text) > 500:
                        print(f"[TOO LONG] {i}")
                        continue
                    f.write(
                        f"{valid_idx}\n"
                        f"{timeline}\n"
                        f"{text}\n\n"
                    )
                    valid_idx += 1
                except Exception as e:
                    print(f"[WRITE ERROR] {i}")
                    print(e)
                    print(b)
        print(f"    --> [SUCCESS] Created: {full_name}")

        # 2. Xuất file LONGEST
        # Không dò timeline gốc nữa: start từ 0, mỗi word hiển thị theo cấu hình.
        LONGEST_WORD_DURATION_SEC = 0.7
        longest_name = f"fin_aud_2{sp}_lest.srt"
        current_offset = 0.0
        longest_content = []
        valid_idx = 1

        for st_key in sorted(set(stage_map.values())):
            longest_word = clean_caption_text(longest_word_text[sp][st_key])
            if longest_word:
                new_start = current_offset
                new_end = new_start + LONGEST_WORD_DURATION_SEC

                new_timeline = f"{format_timestamp(new_start)} --> {format_timestamp(new_end)}"
                longest_content.append(f"{valid_idx}\n{new_timeline}\n{longest_word}")

                current_offset = new_end
                valid_idx += 1

        if longest_content:
            with open(os.path.join(output_dir, longest_name), "w", encoding="utf-8") as f:
                f.write("\n\n".join(longest_content) + "\n\n")
            print(f"    --> [SUCCESS] Created: {longest_name}")

    # DEBUG
    #printf("report_map: ", report_map)

    print(f"\nTotal processed: {srt_ptr} blocks")
    print("\n--- Separate 2 SRT Finished ---\n")
    return report_map

def clean_srt_text(text):
    if text is None:
        return ""
    text = str(text).replace("\r", " ").replace("\n", " ")
    text = text.replace("[", "").replace("]", "")
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def convert_1920_1080():
    imgs = ["./img1_HOOK.png", "./img2_INFO.png", "./img3_MAIN.png", "./img4_BYE.png"]

    # Chuỗi filter complex bạn yêu cầu
    filter_complex_str = (
        "[0:v]crop=100:100:0:0,boxblur=luma_radius=30:luma_power=1:chroma_radius=25:chroma_power=1[blur];"
        "[0:v][blur]overlay=0:0,"
        "crop=iw*0.99:ih*0.99,scale=iw/0.99:ih/0.99,"
        "gblur=sigma=0.2,"
        "eq=contrast=1.01:brightness=0.001,"
        "scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
    )

    print(f"\n--- Checking/Converting Background Images ---")

    any_converted = False

    for img_in in imgs:
        img_out = os.path.splitext(img_in)[0] + ".jpg"

        # 1. KIỂM TRA: Nếu file .jpg đã tồn tại thì bỏ qua
        if os.path.exists(img_out):
            print(f"    [SKIP] File already exists: {img_out}")
            continue

        # 2. KIỂM TRA: Nếu file nguồn .png không tồn tại thì không thể convert
        if not os.path.exists(img_in):
            print(f"    [WARNING] Source file not found: {img_in}")
            continue

        # 3. THỰC HIỆN: Gọi FFmpeg nếu chưa có file đích
        command = [
            "ffmpeg", "-y",
            "-i", img_in,
            "-filter_complex", filter_complex_str,
            "-q:v", "2",
            img_out
        ]

        try:
            print(f"    [PROCESS] Converting {img_in}...")
            subprocess.run(command, check=True, capture_output=True)
            print(f"    --> [SUCCESS] Created: {img_out}")
            any_converted = True
        except subprocess.CalledProcessError as e:
            print(f"    [ERROR] Failed to convert {img_in}: {e}")

    if not any_converted:
        print("--- All background images are already up to date ---")
    else:
        print("--- Image conversion completed ---")

def sync_timeline(debug_mode=0):
    pcap_path = "./audio_ffmpegs/fin_aud_1pcap.srt"
    man_path = "./audio_ffmpegs/fin_aud_2man.srt"
    woman_path = "./audio_ffmpegs/fin_aud_2woman.srt"

    if not all(os.path.exists(p) for p in [pcap_path, man_path, woman_path]):
        print("    [ERROR] Thiếu file SRT để thực hiện sync!")
        return

    # 1. Hàm đọc SRT thành list các block
    def get_blocks(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        # Regex lấy: ID, Timeline, Text
        return re.findall(r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n((?:.+\n?)+)", content)

    # 2. Phân tích file PCAP (file gốc có highlight)
    raw_pcap = get_blocks(pcap_path)
    pcap_data = []
    for b in raw_pcap:
        text = b[2].strip()
        # Tìm từ nằm trong ngoặc [ ]
        match = re.search(r"\[(.*?)\]", text)
        pcap_data.append({
            'start': b[1].split(" --> ")[0],
            'end': b[1].split(" --> ")[1],
            'text_clean': text.replace("[", "").replace("]", "").strip(),
            'highlight': match.group(1) if match else None
        })

    # 2. Đọc Man và Woman, gắn nhãn Speaker rồi TRỘN CHÚNG LẠI
    man_raw = get_blocks(man_path)
    woman_raw = get_blocks(woman_path)

    merged_targets = []
    for b in man_raw:
        merged_targets.append({'id': b[0], 'time': b[1], 'text': b[2].strip(), 'speaker': 'man', 'start_ms': time_to_ms(b[1].split(" --> ")[0])})
    for b in woman_raw:
        merged_targets.append({'id': b[0], 'time': b[1], 'text': b[2].strip(), 'speaker': 'woman', 'start_ms': time_to_ms(b[1].split(" --> ")[0])})

    # SẮP XẾP TỔNG THEO THỜI GIAN GỐC (Để biết ai nói trước, ai nói sau)
    merged_targets.sort(key=lambda x: x['start_ms'])

    # 3. TIẾN HÀNH ĐỒNG BỘ (Chỉ dùng 1 con trỏ duy nhất cho cả 2 người)
    pcap_ptr = 0
    adjust_stats = {'man': 0, 'woman': 0}

    final_man_blocks = {}
    final_woman_blocks = {}

    print(f"\n--- Cross-Checking & Syncing Timeline ---")

    for target in merged_targets:
        word = target['text']
        found = False

        # Dò trong pcap_list từ vị trí con trỏ hiện tại (không bao giờ quay đầu)
        for i in range(pcap_ptr, len(pcap_data)):
            p_item = pcap_data[i]

            if p_item['highlight'] == word:
                new_start = p_item['start']
                new_end = p_item['end']

                # Logic lấy Start từ block Intro
                if i > 0:
                    prev = pcap_data[i-1]
                    if prev['text_clean'] == p_item['text_clean'] and prev['highlight'] is None:
                        new_start = prev['start']

                new_time = f"{new_start} --> {new_end}"

                if debug_mode == 1 and target['time'] != new_time:
                    print(f"    [{target['speaker'].upper()}] '{word}': {target['time']} -> {new_time}")

                if target['time'] != new_time:
                    adjust_stats[target['speaker']] += 1

                # Lưu vào danh sách tương ứng
                block_str = f"{target['id']}\n{new_time}\n{word}"
                if target['speaker'] == 'man':
                    final_man_blocks[int(target['id'])] = block_str
                else:
                    final_woman_blocks[int(target['id'])] = block_str

                pcap_ptr = i + 1 # Nhảy con trỏ pcap đi tiếp, từ "He" này đã được dùng
                found = True
                break

        if not found:
            # Nếu không tìm thấy, giữ nguyên timeline cũ
            block_str = f"{target['id']}\n{target['time']}\n{word}"
            if target['speaker'] == 'man': final_man_blocks[int(target['id'])] = block_str
            else: final_woman_blocks[int(target['id'])] = block_str

    # 4. Ghi lại file (Sắp xếp lại theo ID để bảo toàn cấu trúc SRT)
    def save_srt(path, data_dict):
        sorted_keys = sorted(data_dict.keys())
        with open(path, "w", encoding="utf-8") as f:
            for k in sorted_keys:
                f.write(data_dict[k] + "\n\n")

    save_srt(man_path, final_man_blocks)
    save_srt(woman_path, final_woman_blocks)

    print(f"\n{'='*50}")
    print(f"    REPORT CROSS-SYNC TIMELINE:")
    print(f"    - Man:   Adjusted {adjust_stats['man']} words")
    print(f"    - Woman: Adjusted {adjust_stats['woman']} words")
    print(f"{'='*50}\n")

def format_timestamp(seconds):
    # seconds -> HH:MM:SS,mmm
    ms = int(round((seconds - int(seconds)) * 1000))
    s = int(seconds) % 60
    m = (int(seconds) // 60) % 60
    h = int(seconds) // 3600
    # Đảm bảo mili giây luôn là 3 chữ số
    if ms == 1000: # Xử lý làm tròn lên
        ms = 0
        seconds += 1
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

#===============================================================================   █   █    █
#===============================================================================  ██   █    █
#===============================================================================   █   ██████
#===============================================================================   █        █
#===============================================================================██████      █
def detect_4_silent(input_srt):
    if not os.path.exists(input_srt):
        print(f"    [ERROR] Không tìm thấy file: {input_srt}")
        return

    with open(input_srt, 'r', encoding='utf-8') as f:
        content = f.read().strip()

    matches = re.findall(r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})", content)
    if not matches: return

    # 1. Tìm tất cả các khoảng lặng giữa các timeline
    all_gaps = []
    for i in range(len(matches) - 1):
        start_ms = time_to_ms(matches[i][1])
        end_ms = time_to_ms(matches[i+1][0])
        duration = end_ms - start_ms
        if duration > 0:
            all_gaps.append({
                'start': matches[i][1],
                'start_ms': start_ms,
                'end': matches[i+1][0],
                'end_ms': end_ms,
                'duration_ms': duration,
                'is_last': False
            })

    # 2. Lấy 3 khoảng lặng dài nhất
    top_3_longest = sorted(all_gaps, key=lambda x: x['duration_ms'], reverse=True)[:3]

    # 3. Tính Silent 4 (Timeline cuối + 2s)
    last_end_ms = time_to_ms(matches[-1][1])
    silent_4 = {
        'start': matches[-1][1],
        'start_ms': last_end_ms,
        'end': ms_to_time(last_end_ms + 2000),
        'end_ms': last_end_ms + 2000,
        'duration_ms': 2000,
        'is_last': True
    }

    # 4. Gộp lại và sắp xếp theo trình tự thời gian
    final_list = top_3_longest + [silent_4]
    final_list_sorted = sorted(final_list, key=lambda x: x['start_ms'])

    # 5. Tính toán giá trị start_img và chuẩn bị Report
    output_path = "./bk_4_silent"
    header = f"{'ID':<10} {'start':<13} {'end':<13} {'duration':<10} {'start_img':<13}"
    separator = "-" * 65
    report_lines = [header, separator]

    for i, s in enumerate(final_list_sorted, 1):
        dur_sec = s['duration_ms'] / 1000

        # Công thức tính start_img
        if s['is_last']:
            # Silent 4: lấy mốc end
            start_img_ms = s['end_ms']
        else:
            # Silent 1, 2, 3: lấy mốc ở giữa (start + duration/2)
            start_img_ms = s['start_ms'] + (s['duration_ms'] // 2)

        start_img_ts = ms_to_time(start_img_ms)

        line = f"silent{i:<3} {s['start']:<13} {s['end']:<13} {dur_sec:>5.1f} s     {start_img_ts:<13}"
        report_lines.append(line)

    # Ghi file và In màn hình
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"\n--- DETECTED 4 SILENTS (ORDERED BY TIME) ---")
    print("\n".join(report_lines))
    print(f"--- Report saved to: {output_path} ---\n")
    printf("\nSTEP 14 DONE\n")

def time_to_ms(ts):
    """Chuyển HH:MM:SS,mmm sang milliseconds"""
    h, m, s_ms = ts.split(':')
    s, ms = s_ms.split(',')
    return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms)

def ms_to_time(ms_total):
    """Chuyển milliseconds sang HH:MM:SS,mmm"""
    if ms_total < 0: ms_total = 0
    h = ms_total // 3600000
    m = (ms_total % 3600000) // 60000
    s = (ms_total % 60000) // 1000
    ms = ms_total % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def time_to_seconds(t_str):
    """Hỗ trợ chuyển đổi format 00:00:00,000 sang giây"""
    if not t_str: return 0
    t_str = t_str.replace(',', '.')
    parts = t_str.split(':')
    if len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    return float(t_str)

#===============================================================================   █   ██████
#===============================================================================  ██   █
#===============================================================================   █   ██████
#===============================================================================   █        █
#===============================================================================██████ ██████
def scale_all_img(corner_radius=30):
    target_w, target_h = 960, 540

    print(f"\n--- Scaling images in ./images to fit {target_w}x{target_h} (Radius: {corner_radius}) ---")
    img_folder = "./images"
    img_files = glob.glob(os.path.join(img_folder, "*.jpg")) + glob.glob(os.path.join(img_folder, "*.JPG"))

    if not img_files:
        print("    [INFO] No .jpg files found.")
        return

    for fpath in img_files:
        try:
            with Image.open(fpath) as img:
                img = img.convert("RGBA")
                img_w, img_h = img.size

                # TÍNH TOÁN TỶ LỆ (Scaling Factor)
                # Tỷ lệ để đạt được chiều rộng mục tiêu
                ratio_w = target_w / img_w
                # Tỷ lệ để đạt được chiều cao mục tiêu
                ratio_h = target_h / img_h

                # CHỌN TỶ LỆ NHỎ NHẤT để đảm bảo ảnh không bị vượt quá khung ở bất kỳ chiều nào
                # nhưng vẫn là kích thước lớn nhất có thể nằm trong khung đó.
                scaling_factor = min(ratio_w, ratio_h)

                # Tính toán kích thước mới
                new_w = int(img_w * scaling_factor)
                new_h = int(img_h * scaling_factor)

                # Thực hiện resize
                img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                # --- BO GÓC SỬ DỤNG BIẾN ĐƯỢC TRUYỀN VÀO ---
                mask = Image.new("L", (new_w, new_h), 0)
                draw = ImageDraw.Draw(mask)
                draw.rounded_rectangle((0, 0, new_w, new_h), radius=corner_radius, fill=255)
                img_resized.putalpha(mask)

                base_name = os.path.splitext(fpath)[0]
                save_path = base_name + ".png"
                img_resized.save(save_path, "PNG")

                print(f"    --> {'Landscape' if img_w > img_h else 'Portrait'}: "
                      f"{img_w}x{img_h} -> {new_w}x{new_h} (Rounded {corner_radius}px)")

        except Exception as e:
            print(f"    [ERROR] {fpath}: {e}")

    print("--- Scaling & Rounding complete ---\n")
    printf("\nSTEP 15 DONE\n")

def fmt_time(seconds):
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m:02d}:{s:05.2f}"

#===============================================================================   █   ██████
#===============================================================================  ██   █
#===============================================================================   █   ██████
#===============================================================================   █   █    █
#===============================================================================██████ ██████
# Định nghĩa các biến cố định cho thời lượng hiệu ứng
_FADE_DURATION = 1.5 # Thời lượng hiệu ứng chuyển cảnh nền
_OVERLAY_FADE_DURATION = 0.5 # Thời lượng hiệu ứng fade cho ảnh minh họa/overlay
_LOGO_DISPLAY_DURATION = 3.0 # Thời lượng hiển thị mỗi lần của logo
_SUB_DISPLAY_DURATION = 3.2 # Thời lượng hiển thị mỗi lần của sub

# CẬP NHẬT: Loại bỏ time_effect_overlay khỏi tham số hàm
def build_video_final(mode="full", time_range=None,
                      output="build_video_final.mp4", MAN_POS_IMG="LEFT",
                      logo_path="./img6_LOGO.png", logo_size="100x100", logo_opacity=0.3,
                      sub_path="./img7_SUB.mov"):

    # ÉP KIỂU VÀ KIỂM TRA GIÁ TRỊ (Rất quan trọng)
    f_dur = _FADE_DURATION
    o_dur = _OVERLAY_FADE_DURATION

    print(f"\n--- Building Video Stage 1 ({mode.upper()}) ---")
    print(f"    [CHECK] Background Effect Duration: {f_dur}s (Fixed)")
    print(f"    [CHECK] Overlay Effect Duration: {o_dur}s (Fixed)")
    print(f"    [CHECK] Logo Opacity: {logo_opacity}")

    base_dir = "./audio_ffmpegs"
    audio_wav = None
    if os.path.exists(base_dir):
        audio_files = [f for f in os.listdir(base_dir) if f.startswith("final_audio_") and f.endswith(".wav")]
        if audio_files: audio_wav = os.path.join(base_dir, audio_files[0])

    width_box, hight_box = 960, 540
    half_w = 1920/2
    x_box1 = (half_w - width_box) / 2
    x_box2 = half_w + x_box1
    y_box_all = 300

    imgs_bg = ["./img1_HOOK.jpg", "./img2_INFO.jpg", "./img3_MAIN.jpg", "./img4_BYE.jpg", "./img5_CHAN.jpg"]
    silent_report = "./bk_4_silent"
    img_folder = "./images"
    img_time_file = "./bk_img_time"
    effects_list = ["fade", "wipeleft", "wiperight", "wipeup", "wipedown", "slideleft", "slideright", "slideup", "slidedown", "circleopen", "circleclose", "vertopen", "vertclose", "horzopen", "horzclose", "dissolve", "pixelize", "diagtl", "diagtr", "diagbl", "diagbr", "radial", "hblur"]

    # 1. LẤY MỐC THỜI GIAN
    transition_times = []
    if os.path.exists(silent_report): # Đảm bảo file tồn tại
        with open(silent_report, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("silent"):
                    parts = line.split()
                    if len(parts) >= 5: transition_times.append(time_to_seconds(parts[-1]))
        if len(transition_times) < 4:
            print(f"    [ERROR] Not enough transition times found in {silent_report}. Expected 4, got {len(transition_times)}. Exiting.")
            return # Thoát nếu không đủ mốc thời gian
        t2, t3, t4, t5 = transition_times
    else:
        print(f"    [ERROR] Silent report file not found: {silent_report}. Cannot determine transition times. Exiting.")
        return # Thoát nếu không tìm thấy file

    # 2. XÁC ĐỊNH TỔNG THỜI GIAN
    total_vid_time = t5 + 5.0 # Mặc định nếu không lấy được từ audio, thêm 5s sau mốc t5
    if audio_wav:
        try:
            cmd_probe = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_wav]
            audio_duration = float(subprocess.check_output(cmd_probe).decode().strip())
            total_vid_time = max(total_vid_time, audio_duration + 1.0) # Đảm bảo video không bị cắt ngắn hơn audio, cộng thêm 1s đệm
        except Exception as e:
            print(f"    [WARNING] Could not get audio duration from '{audio_wav}': {e}. Using default total_vid_time ({total_vid_time:.2f}s).")

    # 4. ĐỌC DỮ LIỆU ẢNH MINH HỌA
    overlay_data = []
    if os.path.exists(img_time_file):
        with open(img_time_file, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) >= 7:
                    # Cập nhật: Kiểm tra sự tồn tại của file trước khi thêm vào overlay_data
                    actual_files = glob.glob(os.path.join(img_folder, f"{parts[0].strip()}*.png"))
                    if actual_files and os.path.exists(actual_files[0]):
                        overlay_data.append({"path": actual_files[0], "start": time_to_seconds(parts[1]), "end": time_to_seconds(parts[3]), "gender": parts[6].strip().lower()})
                    else:
                        print(f"    [WARNING] Overlay image not found or invalid: {os.path.join(img_folder, parts[0].strip() + '*.png')}")
    else:
        print(f"    [WARNING] Image time file not found: {img_time_file}. No overlay images will be used.")

    # --- 5. LOGIC EFFECT (NỀN) ---
    fx = [random.choice(effects_list) for _ in range(4)]

    # --- BẮT ĐẦU PHẦN TÍNH TOÁN CHỈ SỐ INPUT VÀ LOG DEBUG ---
    # Thứ tự input cho FFmpeg:
    # 0-4: imgs_bg (5 files)
    # 5-7: mov_inputs (3 files)
    # 8: audio_wav (IF PRESENT)
    # 8 (if no audio) or 9 (if audio): overlay_data (len(overlay_data) files)
    # X: logo_path (1 file)
    # Y: sub_path (1 file)

    # 6. FILTER COMPLEX
    mov_inputs = [os.path.join(base_dir, f) for f in ["fin_aud_1pcap.mov", "fin_aud_2man.mov", "fin_aud_2woman.mov"]]

    # Xác định chỉ số cho audio_wav (nếu có)
    audio_input_idx_val = -1
    if audio_wav:
        audio_input_idx_val = 8 # Index 8 sau 5 bg imgs và 3 mov inputs (0-7)

    # Xác định chỉ số bắt đầu cho overlay_data
    # Nếu có audio_wav (index 8), overlay_data bắt đầu từ index 9.
    # Nếu không có audio_wav, overlay_data bắt đầu từ index 8.
    overlay_data_start_idx = 8 + (1 if audio_wav else 0)

    # Xác định chỉ số cho logo
    logo_input_idx = overlay_data_start_idx + len(overlay_data)

    # Xác định chỉ số cho sub
    sub_input_idx = logo_input_idx + 1

    print(f"\n    [DEBUG] FFMPEG Input Indices:")
    print(f"        Background Images (0-4): {imgs_bg}")
    print(f"        Mov Inputs (5-7): {mov_inputs}")
    if audio_wav and os.path.exists(audio_wav):
        print(f"        Audio WAV ({audio_input_idx_val}): {audio_wav}")
    else:
        print(f"        Audio WAV: Not present or file not found")
    print(f"        Overlay Data (starts {overlay_data_start_idx}, {len(overlay_data)} files): {[item['path'] for item in overlay_data]}")
    if os.path.exists(logo_path):
        print(f"        Logo Image ({logo_input_idx}): {logo_path}")
    else:
        print(f"        Logo Image ({logo_input_idx}): {logo_path} (File NOT FOUND!)")
    if os.path.exists(sub_path):
        print(f"        Subscribe Video ({sub_input_idx}): {sub_path}")
    else:
        print(f"        Subscribe Video ({sub_input_idx}): {sub_path} (File NOT FOUND!)")
    print(f"        Total Expected FFMPEG Inputs: {sub_input_idx + 1}")
    # --- KẾT THÚC PHẦN TÍNH TOÁN CHỈ SỐ INPUT VÀ LOG DEBUG ---

    filters = [
        f"[0:v]format=yuv420p[v0]", f"[1:v]format=yuv420p[v1]",
        f"[2:v]format=yuv420p[v2]", f"[3:v]format=yuv420p[v3]",
        f"[4:v]format=yuv420p[v4]",
        f"[v0][v1]xfade=transition={fx[0]}:duration={f_dur}:offset={t2-f_dur/2}[bg1]",
        f"[bg1][v2]xfade=transition={fx[1]}:duration={f_dur}:offset={t3-f_dur/2}[bg2]",
        f"[bg2][v3]xfade=transition={fx[2]}:duration={f_dur}:offset={t4-f_dur/2}[bg3]",
        f"[bg3][v4]xfade=transition={fx[3]}:duration={f_dur}:offset={t5-f_dur/2}[bg_f]",

        f"[5:v]format=yuva420p[m1]", f"[6:v]format=yuva420p[m2]", f"[7:v]format=yuva420p[m3]",
        f"[bg_f]format=yuva420p[bg_a]",
        f"[bg_a][m1]overlay=x=0:y=0:eof_action=pass[tmp1]",
        f"[tmp1][m2]overlay=x=0:y=0:eof_action=pass[tmp2]",
        f"[tmp2][m3]overlay=x=0:y=0:eof_action=pass[base_overlay]"
    ]

    last_label = "[base_overlay]"

    # LOGIC CHO CÁC LỚP PHỦ ẢNH MINH HỌA
    for i, item in enumerate(overlay_data):
        input_idx = overlay_data_start_idx + i # Sử dụng chỉ số đã tính toán chính xác
        is_man = (item["gender"] == "man")
        x_s = (x_box1 if is_man else x_box2) if MAN_POS_IMG == "LEFT" else (x_box2 if is_man else x_box1)
        st_out = max(item['start'], item['end'] - o_dur)

        filters.append(f"[{input_idx}:v]fade=t=in:st={item['start']}:d={o_dur}:alpha=1,fade=t=out:st={st_out}:d={o_dur}:alpha=1[faded{i}]")
        new_label = f"[tmp_ovl{i}]"
        filters.append(f"{last_label}[faded{i}]overlay=x='{x_s}+({width_box}-w)/2':y='{y_box_all}+({hight_box}-h)/2':enable='between(t,{item['start']},{item['end']})':eof_action=pass{new_label}")
        last_label = new_label

    # --- LOGO KÊNH MỜ ---
    middle_video_time = total_vid_time / 2
    logo_time_start_1 = max(0, middle_video_time - total_vid_time * 0.03)
    logo_time_end_1 = min(total_vid_time, middle_video_time + total_vid_time * 0.03)

    logo_width = int(logo_size.split('x')[0])
    logo_height = int(logo_size.split('x')[1])
    screen_width = 1920
    screen_height = 1080

    logo_x1 = 0
    logo_y1 = (screen_height - logo_height) / 2
    logo_x2 = screen_width - logo_width
    logo_y2 = (screen_height - logo_height) / 2

    print(f"\n    [DEBUG] Logo Info:")
    print(f"        Total Video Time: {total_vid_time:.2f}s")
    print(f"        Logo 1 Time Range: "
        f"{fmt_time(logo_time_start_1)} - "
        f"{fmt_time(logo_time_start_1 + _LOGO_DISPLAY_DURATION)}")
    print(f"        Logo 2 Time Range: "
        f"{fmt_time(logo_time_end_1 - _LOGO_DISPLAY_DURATION)} - "
        f"{fmt_time(logo_time_end_1)}")
    print(f"        Logo Input Index in Filter: {logo_input_idx}")
    print(f"        Logo Opacity: {logo_opacity}")

    if os.path.exists(logo_path):

        filters.append(
            f"[{logo_input_idx}:v]"
            f"scale={logo_size},"
            f"format=rgba,"
            f"colorchannelmixer=aa={logo_opacity},"
            f"trim=duration={total_vid_time},"
            f"setpts=N/FRAME_RATE/TB"
            f"[logo_scaled]"
        )

        filters.append("[logo_scaled]split=2[logo1][logo2]")

        filters.append(
            f"{last_label}[logo1]"
            f"overlay=x={logo_x1}:y={logo_y1}:"
            f"enable='between(t,{logo_time_start_1},{logo_time_start_1 + _LOGO_DISPLAY_DURATION})':"
            f"eof_action=pass"
            f"[tmp_logo1]"
        )

        last_label = "[tmp_logo1]"

        filters.append(
            f"{last_label}[logo2]"
            f"overlay=x={logo_x2}:y={logo_y2}:"
            f"enable='between(t,{logo_time_end_1 - _LOGO_DISPLAY_DURATION},{logo_time_end_1})':"
            f"eof_action=pass"
            f"[tmp_logo2]"
        )

        last_label = "[tmp_logo2]"
    else:
        print(f"    [WARNING] Skipping logo overlay. File not found: {logo_path}")


    # --- SUBSCRIBE CALL TO ACTION ---
    sub_width = 640
    sub_height = 160
    sub_x = (screen_width - sub_width) / 2
    sub_y = (screen_height - sub_height) / 2

    sub_time_start_1 = t2
    sub_time_end_1 = t2 + _SUB_DISPLAY_DURATION

    sub_time_start_2 = t3
    sub_time_end_2 = min(total_vid_time, t3 + _SUB_DISPLAY_DURATION) # Đảm bảo không vượt quá tổng thời lượng video

    print(f"\n    [DEBUG] Subscribe Info:")
    print(f"        T2 (Info transition): {t2:.2f}s")
    print(f"        T3 (Channel transition): {t3:.2f}s")
    print(f"        Sub 1 Time Range: "
        f"{fmt_time(sub_time_start_1)} - "
        f"{fmt_time(sub_time_end_1)}")
    print(f"        Sub 2 Time Range: "
        f"{fmt_time(sub_time_start_2)} - "
        f"{fmt_time(sub_time_end_2)}")
    print(f"        Sub Input Index in Filter: {sub_input_idx}")

    if os.path.exists(sub_path):
        filters.append(
            f"[{sub_input_idx}:v]"
            f"format=rgba,"
            f"setpts=PTS-STARTPTS,"
            f"split=2[sub1][sub2]"
        )

        filters.append(
            f"{last_label}[sub1]"
            f"overlay=format=auto:"
            f"x={sub_x}:y={sub_y}:"
            f"enable='between(t,{sub_time_start_1},{sub_time_end_1})':"
            f"eof_action=pass"
            f"[tmp_sub1]"
        )

        last_label = "[tmp_sub1]"

        filters.append(
            f"{last_label}[sub2]"
            f"overlay=format=auto:"
            f"x={sub_x}:y={sub_y}:"
            f"enable='between(t,{sub_time_start_2},{sub_time_end_2})':"
            f"eof_action=pass"
            f"[tmp_sub2]"
        )

        last_label = "[tmp_sub2]"
    else:
        print(f"    [WARNING] Skipping subscribe overlay. File not found: {sub_path}")

    filters.append(f"{last_label}null[vout]")

    if audio_wav and os.path.exists(sub_path):
        delay1 = int(sub_time_start_1 * 1000)
        delay2 = int(sub_time_start_2 * 1000)

        filters.append(
            f"[{sub_input_idx}:a]"
            f"atrim=0:{_SUB_DISPLAY_DURATION},"
            f"asetpts=PTS-STARTPTS,"
            f"asplit=2[suba1][suba2]"
        )

        filters.append(
            f"[suba1]adelay={delay1}|{delay1}[subad1]"
        )

        filters.append(
            f"[suba2]adelay={delay2}|{delay2}[subad2]"
        )

        filters.append(
            f"[{audio_input_idx_val}:a]"
            f"[subad1]"
            f"[subad2]"
            f"amix=inputs=3:duration=longest[aout]"
        )

    # 7. LỆNH FFMPEG (Dùng d3d11va để tăng tốc)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "info", "-threads", "0", "-y"]
    for img in imgs_bg: cmd.extend(["-loop", "1", "-i", img])
    for mov in mov_inputs: cmd.extend(["-i", mov])

    # ĐỔI MỚI: Thêm audio_wav vào lệnh cmd TẠI VỊ TRÍ CHÍNH XÁC (index 8)
    if audio_wav and os.path.exists(audio_wav):
        cmd.extend(["-i", audio_wav])
    elif audio_wav: # Nếu audio_wav được định nghĩa nhưng file không tồn tại
        print(f"    [WARNING] Audio file not found: {audio_wav}. Video will be silent.")
        audio_input_idx_val = -1 # Đánh dấu là không có audio stream để map

    for item in overlay_data:
        # Chỉ thêm vào nếu file overlay thực sự tồn tại (đã kiểm tra ở trên)
        if os.path.exists(item["path"]):
            cmd.extend(["-loop", "1", "-i", item["path"]])
        else:
            print(f"    [WARNING] Missing overlay image, skipping: {item['path']}")

    # MỚI: Thêm input cho logo và sub (chỉ khi các file tồn tại)
    if os.path.exists(logo_path):
        cmd.extend(["-loop", "1", "-i", logo_path])
    else:
        print(f"    [WARNING] Logo file not found: {logo_path}. Skipping -i for logo.")

    if os.path.exists(sub_path):
        cmd.extend(["-stream_loop", "-1", "-i", sub_path])
    else:
        print(f"    [WARNING] Subscribe file not found: {sub_path}. Skipping -i for subscribe.")


    cmd.extend(["-filter_complex", ";".join(filters), "-map", "[vout]"])

    # CẬP NHẬT: Chỉ map audio nếu audio_wav tồn tại VÀ file audio_wav thực sự có stream audio
    if audio_wav and audio_input_idx_val != -1:
        # nếu có sub.mov
        if os.path.exists(sub_path):

            filters.append(
                f"[{audio_input_idx_val}:a]"
                f"[{sub_input_idx}:a]"
                f"amix=inputs=2:duration=longest:dropout_transition=0[aout]"
            )

            cmd.extend([
                "-map", "[aout]",
                "-c:a", "aac",
                "-b:a", "192k"
            ])

        else:
            cmd.extend([
                "-map", "[aout]",
                "-c:a", "aac",
                "-b:a", "192k"
            ])

        cmd.append("-shortest")
    elif audio_wav and audio_input_idx_val == -1: # Trường hợp audio_wav có tên nhưng file không tồn tại
        print(f"    [WARNING] No audio stream will be mapped because audio file was not found.")


    cmd.extend(hwgpu_args)

    if "-pix_fmt" not in HWGPU:
        cmd.extend(["-pix_fmt", "yuv420p"])

    if mode == "test" and time_range:
        if "-" in str(time_range):
            ss, te = str(time_range).split("-")
            cmd.extend(["-ss", ss, "-t", str(float(te)-float(ss))])
        else:
            print(f"    [WARNING] Invalid time_range format for 'test' mode: '{time_range}'. Expected 'start-end'. Skipping time trimming.")

    cmd.append(output)

    # --- IN RA LỆNH FFMPEG HOÀN CHỈNH ĐỂ DEBUG ---
    print(f"\n    [DEBUG] Full FFmpeg Command:\n{' '.join(cmd)}\n")
    # --- KẾT THÚC IN LỆNH ---

    try:
        subprocess.run(cmd, check=True)
        print(f"    --> [SUCCESS] Created: {output} (f_dur: {f_dur}s)")
        transcript_video()
    except Exception as e:
        print(f"    [ERROR] FFmpeg failed.")
        print(f"    [DEBUG] Command: {' '.join(cmd)}")
        print(f"    [DEBUG] Error: {e}")
    printf("\nSTEP 16 DONE\n")

def transcript_video():
    input_file  = "./audio_ffmpegs/fin_aud_0_cor.srt"
    output_file = "./build_video_final.srt"

    # REMOVE HIDDEN / INVISIBLE CHARACTERS
    def clean_text(text):
        # Unicode normalize
        text = unicodedata.normalize("NFKC", text)

        # Remove BOM
        text = text.replace("\ufeff", "")

        # Remove zero-width chars
        hidden_chars = [
            "\u200b",  # zero width space
            "\u200c",  # zero width non-joiner
            "\u200d",  # zero width joiner
            "\u2060",  # word joiner
            "\u00a0",  # non-breaking space
            "\u202a",
            "\u202b",
            "\u202c",
            "\u202d",
            "\u202e",
        ]

        for ch in hidden_chars:
            text = text.replace(ch, "")

        # Remove strange control chars
        text = re.sub(r"[\x00-\x08\x0B-\x1F\x7F]", "", text)

        return text.strip()

    # READ SRT
    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()

    content = clean_text(content)

    subtitles = list(srt.parse(content))

    # CLEAN ALL SUBS
    cleaned_subs = []

    for sub in subtitles:
        sub.content = clean_text(sub.content)

        # skip empty dummy subtitles
        if sub.content == "":
            continue

        cleaned_subs.append(sub)

    # RE-INDEX FROM 1
    for idx, sub in enumerate(cleaned_subs, start=1):
        sub.index = idx

    # WRITE OUTPUT
    output_srt = srt.compose(cleaned_subs)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(output_srt)

    print(f"\n[INFO] Exported: {output_file}\n")

#=======================================================================================================================
#=======================================================================================================================
#=======================================================================================================================
#=======================================================================================================================
#=======================================================================================================================
# SUB_FUNCTION
def sub_s0_move_old_data( audio_elabs=0, audio_ffmpeg=0, audio_ffmpegs=0, images=1,
    bk_file=0, fin_file=0, img_file=0 ):
    audio_elabs   = int(audio_elabs)
    audio_ffmpeg  = int(audio_ffmpeg)
    audio_ffmpegs = int(audio_ffmpegs)
    images        = int(images)
    bk_file       = int(bk_file)
    fin_file      = int(fin_file)
    img_file      = int(img_file)

    print("\n--- SUB STEP : MOVE OLD DATA ---")

    if not ( audio_elabs or audio_ffmpeg or audio_ffmpegs or images or
        bk_file or fin_file or img_file ):
        print("    --> No cleanup flags enabled")
        return

    # BACKUP
    date_str = datetime.now().strftime("%y%m%d_%H%M%S")
    src_dir = os.path.abspath("../0000_ezeng")
    #backup_base = r"C:\Users\CPH\Desktop\bk"
    backup_base = r"D:\Users\CPH\Desktop\bk"
    dest_dir = os.path.join(
        backup_base,
        f"0000_ezeng_{date_str}"
    )

    try:
        os.makedirs(backup_base, exist_ok=True)
        if os.path.exists(src_dir):
            print(f"    [BACKUP]")
            print(f"        FROM : {src_dir}")
            print(f"        TO   : {dest_dir}")
            shutil.copytree( src_dir, dest_dir, dirs_exist_ok=True )
            print("    [BACKUP] DONE")
        else:
            print(f"    [WARNING] Source not found : {src_dir}")
    except Exception as e:
        print(f"    [ERROR] Backup failed : {e}")

    # REMOVE DIR
    dirs_to_remove = []

    if audio_elabs:     dirs_to_remove.append("audio_elabs")
    if audio_ffmpeg:    dirs_to_remove.append("audio_ffmpeg")
    if audio_ffmpegs:   dirs_to_remove.append("audio_ffmpegs")
    if images:          dirs_to_remove.append("images")

    for d in dirs_to_remove:
        try:
            if os.path.isdir(d):
                shutil.rmtree(d)
                print(f"    [REMOVE DIR] {d}")
            else:
                print(f"    [SKIP DIR] {d}")
        except Exception as e:
            print(f"    [ERROR REMOVE DIR] {d} -> {e}")

    # REMOVE bk_*
    if bk_file:
        for f in glob.glob("bk_*"):
            try:
                if os.path.isfile(f):
                    os.remove(f)
                    print(f"    [REMOVE FILE] {f}")
            except Exception as e:
                print(f"    [ERROR REMOVE FILE] {f} -> {e}")

    # REMOVE fin_*
    if fin_file:
        for f in glob.glob("fin_*"):
            try:
                if os.path.isfile(f):
                    os.remove(f)
                    print(f"    [REMOVE FILE] {f}")
            except Exception as e:
                print(f"    [ERROR REMOVE FILE] {f} -> {e}")

    # REMOVE img1* img2* img3* img4*
    if img_file:
        patterns = [ "img1*", "img2*", "img3*", "img4*" ]
        for pattern in patterns:
            for f in glob.glob(pattern):
                try:
                    if os.path.isfile(f):
                        os.remove(f)
                        print(f"    [REMOVE IMG] {f}")
                except Exception as e:
                    print(f"    [ERROR REMOVE IMG] {f} -> {e}")

    print("--- CLEANUP COMPLETED ---\n")

def sub_s1_copy_4_img( img1="img1_HOOK.png", img2="img2_INFO.png", img3="img3_MAIN.png", img4="img4_BYE.png" ):
    working_dir = "./"
    download_dir = r"D:\Users\CPH\Downloads"

    print("\n--- SEARCHING PNG FILES IN DOWNLOAD DIR ---")

    # lấy tất cả file png
    png_files = [
        os.path.join(download_dir, f)
        for f in os.listdir(download_dir)
        if f.lower().endswith(".png")
    ]

    # kiểm tra đủ 4 file
    if len(png_files) < 4:
        print("[ERROR] Not enough PNG files in download folder")
        return
    elif len(png_files) > 4:
        print("[ERROR] A lot of PNG files in download folder")
        return

    # sort theo thời gian download / modified time
    png_files.sort(key=os.path.getmtime)

    # lấy 4 file mới nhất
    latest_4 = png_files[-4:]

    # sort lại theo thứ tự thời gian cũ -> mới
    latest_4.sort(key=os.path.getmtime)

    target_names = [img1, img2, img3, img4]

    print("\n--- RENAMING + COPYING FILES ---")

    renamed_paths = []
    # đổi tên ngay trong download_dir
    for src, new_name in zip(latest_4, target_names):
        new_src = os.path.join(download_dir, new_name)
        # xóa file cũ nếu tồn tại
        if os.path.exists(new_src):
            os.remove(new_src)
        os.rename(src, new_src)
        renamed_paths.append(new_src)
        print(f"[RENAMED] FROM: {src} TO: {new_src}")

    # copy sang working_dir
    for src in renamed_paths:
        dst = os.path.join( working_dir, os.path.basename(src) )
        shutil.copy2(src, dst)
        print(f"[COPIED] FROM: {src} TO: {dst}")

    print("\n--- COMPLETE TO COPY 4 IMAGE TO WORKING DIR ---\n")

def sub_s4_rm_bk_database():
    file_name = "./bk_database.whis"
    if os.path.exists(file_name):
        os.remove(file_name)
        print(f"[REMOVED] {file_name}")
    else:
        print(f"[NOT FOUND] {file_name}")

#=======================================================================================================================
#=======================================================================================================================
#=======================================================================================================================
#=======================================================================================================================
#=======================================================================================================================
# NOT_YET_USE
def separate_srt():
    script_yt_path = "./scripts.yt"
    master_srt_path = "./audio_ffmpegs/fin_aud_2ali.srt"
    output_dir = "./audio_ffmpegs"

    stage_map = {"HOOK": "1_HOOK", "INFO": "2_START", "START": "2_START", "MAIN": "3_MAIN", "BYE": "4_BYE"}

    if not os.path.exists(script_yt_path) or not os.path.exists(master_srt_path):
        print("    [ERROR] Thiếu file đầu vào!")
        return

    # --- BƯỚC 1: TRÍCH XUẤT TỪ SCRIPT (Giữ nguyên logic làm sạch) ---
    with open(script_yt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    script_words = []

    def detect_speaker(label):
        u = label.upper()
        tokens = [t for t in re.split(r"[^A-ZÀ-Ỹ0-9]+", u) if t]
        if any(t in {"WOMAN", "NU", "NỮ"} for t in tokens):
            return "woman"
        if any(t in {"MAN", "NAM"} for t in tokens):
            return "man"
        return None

    current_stage = None
    for line in lines:
        l = line.strip()
        if not l or any(l.startswith(x) for x in ["#", "scripts =", '"""']): continue
        if l.upper() in stage_map:
            current_stage = l.upper()
            continue
        if ":" in l and current_stage:
            parts = l.split(":", 1)
            speaker = detect_speaker(parts[0])
            # Xóa (0p8s), [], ...
            text_clean = re.sub(r'\(.*?\)', '', parts[1]).replace("[", "").replace("]", "").replace("...", " ")
            if speaker:
                for w in text_clean.split():
                    norm_w = re.sub(r'[^a-z0-9]', '', w.lower())
                    if norm_w:
                        script_words.append({'norm': norm_w, 'orig': w, 'key': f"{speaker}_{stage_map[current_stage]}"})

    # --- BƯỚC 2: TRÍCH XUẤT BLOCK TỪ SRT VÀ BỎ QUA DUMMY ---
    with open(master_srt_path, "r", encoding="utf-8") as f:
        srt_raw = f.read().strip()

    # Lấy toàn bộ block
    all_blocks = re.findall(r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n((?:.+\n?)+)", srt_raw)

    if len(all_blocks) > 0:
        print(f"    [INFO] Detected and removed the first Dummy block (Block 1).")
        all_blocks = all_blocks[1:] # BỎ QUA BLOCK ĐẦU TIÊN

    # Chuẩn hóa các block còn lại
    srt_list = []
    for b in all_blocks:
        norm_w = re.sub(r'[^a-z0-9]', '', b[2].lower().replace("[", "").replace("]", ""))
        srt_list.append({'norm': norm_w, 'raw': b})

    # --- BƯỚC 3: PHÂN PHỐI BLOCK ---
    results = {f"{sp}_{st}": [] for sp in ["man", "woman"] for st in set(stage_map.values())}
    script_idx = 0
    assigned_count = 0

    for srt_item in srt_list:
        found = False
        # Dò tìm trong 10 từ tiếp theo của kịch bản
        for i in range(script_idx, min(script_idx + 10, len(script_words))):
            if srt_item['norm'] == script_words[i]['norm']:
                target_key = script_words[i]['key']
                results[target_key].append(srt_item['raw'])
                script_idx = i + 1
                found = True
                assigned_count += 1
                break

        # Nếu không khớp hoàn toàn, gán đại vào Stage hiện tại để không mất block
        if not found and script_idx < len(script_words):
            target_key = script_words[script_idx]['key']
            results[target_key].append(srt_item['raw'])
            assigned_count += 1

    # --- BƯỚC 4: XUẤT 8 FILE ---
    print(f"\n{'='*60}")
    for key in sorted(results.keys()):
        blocks = results[key]
        with open(os.path.join(output_dir, f"{key}.srt"), "w", encoding="utf-8") as f:
            for i, b in enumerate(blocks, 1):
                f.write(f"{i}\n{b[1]}\n{b[2].strip()}\n\n")
        print(f"    --> [CREATED] {key:15} | {len(blocks):3} blocks")

    print(f"{'='*60}")
    print(f"    [SCRIPT] {len(script_words)} words | [SRT] (after removing DUMMY): {len(all_blocks)} blocks")
    print(f"    Matching results: {assigned_count}/{len(all_blocks)}")
    print("\n--- Separate SRT Finished ---\n")

def correct_pupcaps(in_path, out_path):
    import re
    import os

    if not os.path.exists(in_path):
        print(f"    [ERROR] File không tồn tại: {in_path}")
        return

    # Đọc nội dung file
    with open(in_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Regex giải thích:
    # \[         : Tìm dấu mở ngoặc [
    # ([^\]]+?)  : Group 1 - Lấy nội dung bên trong (từ ngữ)
    # [.,!?;:]+  : Tìm các dấu câu nằm ngay trước dấu đóng ngoặc
    # \]         : Tìm dấu đóng ngoặc ]
    # Thay thế bằng: [\1] (Chỉ giữ lại nội dung Group 1, bỏ qua phần dấu câu)

    corrected_content = re.sub(r'\[([^\]]+?)[.,!?;:]+\]', r'[\1]', content)

    # Lưu file mới
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(corrected_content)

    print(f"\n    --> [FIXED] REMOVED PUNCTUATION INSIDE BRACKETS: {os.path.basename(out_path)}\n")

def convert_full_timeline(silent_dir, file_srt_in, file_srt_out):
    """
    Hàm điều chỉnh:
    - Không chèn gap ở đầu timeline (Bắt đầu từ sub đầu tiên).
    - Lấp đầy khoảng trống giữa các sub bằng câu vừa đọc xong.
    - Thêm 0.5s gap ở cuối video.
    """
    input_path = os.path.join(silent_dir, file_srt_in)
    output_path = os.path.join(silent_dir, file_srt_out)

    try:
        # Giả định hàm parse_srt trả về list các dict có 'start', 'end', 'text'
        subs = parse_srt(input_path)
    except FileNotFoundError:
        print(f"    [ERROR] Không tìm thấy file {input_path}")
        return

    if not subs:
        print("    [WARNING] File SRT trống.")
        return

    print(f"    Processing: {file_srt_in} -> {file_srt_out}")

    with open(output_path, 'w', encoding='utf-8') as f:
        valid_index = 1
        last_clean_text = ""
        is_first_sub = True
        current_time = 0

        for sub in subs:
            clean_text = clean_weird_characters(sub['text']).strip()
            if not clean_text:
                continue

            # --- XỬ LÝ TIMELINE ĐẦU TIÊN (Yêu cầu 1) ---
            if is_first_sub:
                current_time = sub['start'] # Nhảy thẳng đến thời gian của sub đầu tiên
                is_first_sub = False
            else:
                # --- XỬ LÝ KHOẢNG TRỐNG (GAP) GIỮA CÁC CÂU ---
                gap = sub['start'] - current_time
                if gap > 1:
                    f.write(f"{valid_index}\n")
                    gap_end_time = sub['start'] - 1
                    f.write(f"{ms_to_time(current_time)} --> {ms_to_time(gap_end_time)}\n")

                    # Lấy text cũ đã lột ngoặc để lấp vào gap
                    gap_text = last_clean_text if last_clean_text else clean_text.replace('[', '').replace(']', '')
                    if not gap_text.strip(): gap_text = "."

                    f.write(f"{gap_text}\n\n")
                    valid_index += 1

            # --- GHI CÂU ĐANG ĐỌC THẬT SỰ ---
            f.write(f"{valid_index}\n")
            f.write(f"{ms_to_time(sub['start'])} --> {ms_to_time(sub['end'])}\n")
            f.write(f"{clean_text}\n\n")

            valid_index += 1
            current_time = sub['end']
            # Lưu lại text để lấp gap sau này (xóa ngoặc highlight)
            last_clean_text = clean_text.replace('[', '').replace(']', '')

        # --- XỬ LÝ KHOẢNG TRỐNG CUỐI CÙNG 0.5s (Yêu cầu 2) ---
        if current_time > 0:
            tail_gap_ms = 500 # 0.5 giây
            f.write(f"{valid_index}\n")
            f.write(f"{ms_to_time(current_time)} --> {ms_to_time(current_time + tail_gap_ms)}\n")
            f.write(f"{last_clean_text}\n\n")

    print(f"    --> [SUCCESSFULLY] Created: {file_srt_out}\n")

def clean_weird_characters(text):
    text = re.sub(r'[\xa0\u202f\u205f\u3000]', ' ', text)
    text = re.sub(r'[\u200b-\u200f\ufeff\u202a-\u202e\u2060-\u2064]', '', text)
    text = re.sub(r'[\x00-\x09\x0b\x0c\x0e-\x1f\x7f]', '', text)
    text = re.sub(r' +', ' ', text)
    return text.strip()

def parse_srt(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    blocks = content.split('\n\n')
    subs = []
    for block in blocks:
        lines = block.split('\n')
        if len(lines) >= 3:
            index = lines[0].strip()
            times = lines[1]
            text = "\n".join(lines[2:]).strip()
            if "dummy" in index.lower() or text == "":
                continue
            start_str, end_str = times.split(' --> ')
            subs.append({
                'start': time_to_ms(start_str),
                'end': time_to_ms(end_str),
                'text': text
            })
    return subs

def create_thumb():
    # CONFIG
    IMG_IN  = "img1_HOOK.jpg"
    IMG_OUT = "thumb.jpg"
    FONT_PATH = "C:/Windows/Fonts/arialbd.ttf"

    FONT_SIZE       = 124
    STROKE_SIZE     = 8
    MARGIN_X        = 20
    MARGIN_Y        = 0
    LINE_SPACING    = -10

    # LEFT_TITLE -------------------------------------------
    LEFT_TEXT = """Easy English

US-Iran
truce
faces
tension
"""

    # RIGHT_TITLE ------------------------------------------
    RIGHT_TEXT ="""

after
incident
in Strait
of Hormuz
"""

    # LOAD IMAGE
    img     = Image.open(IMG_IN).convert("RGB")
    draw    = ImageDraw.Draw(img)
    font    = ImageFont.truetype(FONT_PATH, FONT_SIZE)

    # DRAW LEFT TEXT
    draw.multiline_text(
        (MARGIN_X, MARGIN_Y),
        LEFT_TEXT,
        font=font,
        fill="yellow",
        stroke_width=STROKE_SIZE,
        stroke_fill="black",
        spacing=LINE_SPACING,
        align="left",
    )

    # CALCULATE RIGHT TEXT WIDTH
    bbox = draw.multiline_textbbox(
        (0, 0),
        RIGHT_TEXT,
        font=font,
        spacing=LINE_SPACING,
        align="right",
    )
    text_w = bbox[2] - bbox[0]

    # RIGHT ALIGN
    right_x = img.width - text_w - MARGIN_X

    # DRAW RIGHT TEXT
    draw.multiline_text(
        (right_x, MARGIN_Y),
        RIGHT_TEXT,
        font=font,
        fill="yellow",
        stroke_width=STROKE_SIZE,
        stroke_fill="black",
        spacing=LINE_SPACING,
        align="right",
    )

    # SAVE
    img.save(IMG_OUT)
    print(f"\n[DONE] {IMG_OUT}\n")



def print_help():
    help_text = """
# PYTHON_EzEng
    # step0: ---------------------------------------------> create SCRIPTS.YT, SEARCHES.YT, CHECK not ENG
        python scripts.py 0
            run_tts_step0
    # step1: ----------------------------------------------> TTS use elevenlabs, create AUDIO_ELABS dir
        python scripts.py 1         -> run_tts_step1 + Random Man Woman + Start_from_1
        python scripts.py 1 1 2 3   -> run_tts_step1 + Man1, Woman2 + Start_from_3
        python scripts.py 1 1 2 o3  -> run_tts_step1 + Man1, Woman2 + Only_3
    # step2: ---------------------------------------------> Add filter to all audio, create AUDIO_FFMPEG dir
        python scripts.py 2
            run_ffmpeg_step2
    # step3: ---------------------------------------------> Merge audio, insert SILENT, create AUDIO_FFMPEGS dir -final, HOOK + INFO + MAIN + BYE-
        python scripts.py 3 0.80 2 5
            run_silent_step3 + SPEED + GAP_NOR + GAP_BYE
    # step4: ---------------------------------------------> Create bk_database.whis, fin_aud_0.srt, fin_aud_0.txt
        python scripts.py 4
            run_srt_step4
*** *** *** *** RUN S_F4 to Remove bk_database.whis if need
    # step5: ---------------------------------------------> Create fin_aud_0_cor.srt, fin_aud_0_cor.txt + CHECK_WORDS
        python scripts.py 5
            run_srt_step5
    # step6: ---------------------------------------------> Create bk_wlongest, _1.srt, _1.txt + CHECK _0_cor.srt AND _1.srt
        python scripts.py 6
            run_srt_step6
    # step7: ---------------------------------------------> Create fin_aud_2.seg, fin_aud_2ali.seg, fin_aud_2ali.srt
        python scripts.py 7
            run_srt_step7
    # step8: ---------------------------------------------> Create _1pcap.srt + CHECK MATCH
        python scripts.py 8
            run_srt_step8
*** *** *** *** AUTOFIX fin_aud_2ali.srt AND rerun step8 (OR fix by hand fin_aud_1.srt AND rerun step7)
    # step9: ---------------------------------------------> Create _1pcap_lest.srt
        python scripts.py 9
            run_srt_step9
    # step_10: -------------------------------------------> fin_aud_1pcap_lest.MOV fin_aud_1pcap.MOV fin_aud_1pcap.MP4
        python scripts.py 10 test/full
            run_pupcaps_step10 test -> python scripts.py 10 full
*** *** *** *** RUN SubF10 to FIT the LONGEST caption
    # step11: --------------------------------------------> _2man/woman_lest.srt _2man/woman_lest.MOV _2man/woman_lest.MP4 _2man/woman.srt _2man/woman.MOV _2man/woman.MP4
        python scripts.py 11 test/full DEBUG=1 GENDER=man/woman
            run_pupcaps_step11 test -> python scripts.py 11 full
*** *** *** *** RUN SubF10 to FIT the LONGEST caption
    # step_12: -------------------------------------------> Collect illustration image, create IMAGES dir, choose_the_best_imgs
        python scripts_img.py 12
            asyncio.run(main(searches))
            bk_all_imgs()
            choose_the_best_imgs()
            copy_all_sel_imgs()
*** *** *** *** Base on searches.yt to select the correct IMAGE of VIDEO from images dir
*** *** *** *** TRIM JPG images have redundant part
    # step13: --------------------------------------------> Create time start/end of images (bk_img_time)
        python scripts_img.py 13
            time_start_img(searches)
    # step_14: -------------------------------------------> Detect 4 silent points (bk_4_silent)
        python scripts.py 14
            detect_4_silent("./audio_ffmpegs/fin_aud_1pcap.srt")
    # step15: --------------------------------------------> Scale images to 960*540
        python scripts.py 15
            scale_all_img(30)
    # step16: --------------------------------------------> build_video_final.mp4, build_video_final.srt
        python scripts.py 16
            build_video_final test/full
                test OUTPUT=out.mp4
                test 38-48 OUTPUT=out.mp4
                full OUTPUT=out.mp4'
            transcript_video()
    # step17: --------------------------------------------> TITLE.mp4, TITLE.jpg, TITLE.srt
        1. dùng GPT kiểm tra TITLE và lưu vào Z_LIST
        2. python scripts_img.py 17 1 -> create_thumb_wtext(num=1)
        3. rename and copy TITLE.mp4, TITLE.jpg, TITLE.srt, TITLE.eze to Mobile
        4. copy TITLE and ⚠️ Viewer Notice to WhatsApp
    #===========================================================================
    # long: ----------------------------------------------> CHECK_LONG
        python scripts.py long
    # help: ----------------------------------------------> HELP
        python scripts.py help
    ------\
    ------/ TITLE.mp4, TITLE.jpg, TITLE.srt, TITLE.eze
"""
    print(help_text)

#=======================================================================================================================
#=======================================================================================================================
#=======================================================================================================================
#=======================================================================================================================
#=======================================================================================================================
if __name__ == "__main__":
    DEBUG = 0
    GENDER = ""

    # Giá trị mặc định
    params = {
        "mode": "full",
        "time_range": None,
        "output": "build_video_final.mp4"
    }

    # Kiểm tra xem trong các tham số có "DEBUG=1" hay không (không phân biệt hoa thường)
    if any(arg.upper() == "DEBUG=1" for arg in sys.argv):
        DEBUG = 1
    if any(arg.upper() == "GENDER=MAN" for arg in sys.argv):
        GENDER = "man"
    elif any(arg.upper() == "GENDER=WOMAN" for arg in sys.argv):
        GENDER = "woman"

    if len(sys.argv) < 2:
        print_help()
    else:
        mode = sys.argv[1].lower()
        if mode == "0":
            run_tts_step0()
            # from scripts_img import check_searchs_var_v1
            # check_searchs_var_v1(searches)
        elif mode == "1":
            # Thay vì để "1" và "2", ta để None để kích hoạt logic random bên trong hàm
            m_c = sys.argv[2] if len(sys.argv) > 2 else None
            w_c = sys.argv[3] if len(sys.argv) > 3 else None
            try:
                s_i = sys.argv[4] if len(sys.argv) > 4 else 1
            except:
                s_i = 1
            run_tts_step1(m_c, w_c, s_i)
        elif mode == "2": run_ffmpeg_step2()
        elif mode == "3":
            # Tham số: [speed] [gap_sections] [gap_bye]
            sp_val = float(sys.argv[2]) if len(sys.argv) > 2 else 0.8
            g_sec  = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
            g_bye  = float(sys.argv[4]) if len(sys.argv) > 4 else 5.0
            run_silent_step3(sp_val, g_sec, g_bye)
        elif mode == "4": run_srt_step4()
        elif mode == "5": run_srt_step5()
        elif mode == "6":
            try:
                n_val = int(sys.argv[2]) if len(sys.argv) > 2 else 6
            except ValueError:
                print("    Warning: nword must be a number. Using default is 6.")
                n_val = 6
            run_srt_step6(n_val)
        elif mode == "7": run_srt_step7()
        elif mode == "8": run_srt_step8()
        elif mode == "9": run_srt_step9()
        elif mode == "10":
            params["s10mode"] = "full"
            params["fontsize"] = 88
            params["spacing"] = -5
            for arg in sys.argv[2:]:
                if arg.lower().startswith("s10mode="):
                    params["s10mode"] = arg.split("=")[1]
                elif arg.lower().startswith("fontsize="):
                    params["fontsize"] = arg.split("=")[1]
                elif arg.lower().startswith("spacing="):
                    params["spacing"] = arg.split("=")[1]
            run_pupcaps_step10(s10mode=params["s10mode"], fontsize=params["fontsize"], spacing=params["spacing"])
        elif mode == "11":
            params["s11mode"]  = "full"
            params["m_size"]   = 140
            params["w_size"]   = 140
            params["m_space"]  = -5
            params["w_space"]  = -5
            params["m_align"]  = "RIGHT"
            params["w_align"]  = "LEFT"
            params["m_anchor"] = 960
            params["w_anchor"] = 960
            for arg in sys.argv[2:]:
                if arg.lower().startswith("s11mode="):
                    params["s11mode"] = arg.split("=")[1]
                elif arg.lower().startswith("m_size="):
                    params["m_size"] = arg.split("=")[1]
                elif arg.lower().startswith("w_size="):
                    params["w_size"] = arg.split("=")[1]
                elif arg.lower().startswith("m_space="):
                    params["m_space"] = arg.split("=")[1]
                elif arg.lower().startswith("w_space="):
                    params["w_space"] = arg.split("=")[1]
                elif arg.lower().startswith("m_align="):
                    params["m_align"] = arg.split("=")[1]
                elif arg.lower().startswith("w_align="):
                    params["w_align"] = arg.split("=")[1]
                elif arg.lower().startswith("m_anchor="):
                    params["m_anchor"] = arg.split("=")[1]
                elif arg.lower().startswith("w_anchor="):
                    params["w_anchor"] = arg.split("=")[1]
            run_pupcaps_step11(s11mode=params["s11mode"], m_size=params["m_size"], w_size=params["w_size"],
                m_space=params["m_space"], w_space=params["w_space"],
                m_align=params["m_align"], w_align=params["w_align"], m_anchor=params["m_anchor"], w_anchor=params["w_anchor"])
        elif mode == "14": detect_4_silent("./audio_ffmpegs/fin_aud_1pcap.srt")
        elif mode == "15": scale_all_img(corner_radius=30)
        elif mode == "16":
            params["sub1_mode"] = "full"
            for arg in sys.argv[2:]:
                if arg.upper().startswith("OUTPUT="):
                    params["output"] = arg.split("=")[1]
                elif arg.lower() in ["test", "full"]:
                    params["sub1_mode"] = arg.lower()
                elif "-" in arg or (arg.isdigit() and len(arg) < 5):
                    params["time_range"] = arg
            # Gọi hàm với tham số đã bóc tách chính xác
            build_video_final(
                mode=params["sub1_mode"],
                time_range=params["time_range"],
                output=params["output"]
            )

        # UTINITY
        elif mode == "long": run_analyze_long()
        elif mode == "help": print_help()

        # TEST_ONLY
        elif mode == "debug_1" : remove_img_jpg()
        elif mode == "debug_2" : convert_1920_1080()
        elif mode == "debug_3" : check_match_scripts_and_finalsrt()
        elif mode == "debug_4" : printf("DEBUG_4")
        elif mode == "debug_5" : convert_final2alignseg_2_srt( "audio_ffmpegs/fin_aud_2ali.seg", "audio_ffmpegs/fin_aud_2ali.srt" )
        elif mode == "debug_6" : align_scripts_2_final2alignseg()
        elif mode == "debug_7" : build_mov_images(time_effect=0.5, output="build_mov_images.mov", MAN_POS_IMG="LEFT")
        elif mode == "debug_8" : separate_2_srt()
        elif mode == "debug_9" : transcript_video()
        elif mode == "debug_10": create_thumb()
        elif mode == "debug_11": run_srt_step9()

        # SUB_FUNC
        elif mode == "sub0":
            params["audio_elabs"]   = "1"
            params["audio_ffmpeg"]  = "1"
            params["audio_ffmpegs"] = "1"
            params["images"]        = "1"
            params["bk_file"]       = "1"
            params["fin_file"]      = "1"
            params["img_file"]      = "1"
            for arg in sys.argv[2:]:
                if arg.lower().startswith("audio_elabs="):
                    params["audio_elabs"] = arg.split("=")[1]
                elif arg.lower().startswith("audio_ffmpeg="):
                    params["audio_ffmpeg"] = arg.split("=")[1]
                elif arg.lower().startswith("audio_ffmpegs="):
                    params["audio_ffmpegs"] = arg.split("=")[1]
                elif arg.lower().startswith("images="):
                    params["images"] = arg.split("=")[1]
                elif arg.lower().startswith("bk_file="):
                    params["bk_file"] = arg.split("=")[1]
                elif arg.lower().startswith("fin_file="):
                    params["fin_file"] = arg.split("=")[1]
                elif arg.lower().startswith("img_file="):
                    params["img_file"] = arg.split("=")[1]
                elif arg.lower().startswith("img_file="):
                    params["img_file"] = arg.split("=")[1]
            # Call function
            sub_s0_move_old_data ( audio_elabs=params["audio_elabs"], audio_ffmpeg=params["audio_ffmpeg"],
                audio_ffmpegs=params["audio_ffmpegs"], images=params["images"],
                bk_file=params["bk_file"], fin_file=params["fin_file"], img_file=params["img_file"] )
        elif mode == "sub2": sub_s1_copy_4_img ()
        elif mode == "sub4": sub_s4_rm_bk_database()

        # COMBO
        elif mode == "sub6":
            run_tts_step1()
            run_ffmpeg_step2()
            run_silent_step3()
            run_srt_step4()
        elif mode == "sub7":
            run_srt_step5()
            run_srt_step6()
            run_srt_step7()
            run_srt_step8()
            run_srt_step8()
            run_srt_step9()
        elif mode == "sub8":
            run_tts_step1()
            run_ffmpeg_step2()
            run_silent_step3()
            run_srt_step4()
            #
            run_srt_step5()
            run_srt_step6()
            run_srt_step7()
            run_srt_step8()
            run_srt_step8()
            run_srt_step9()
        elif mode == "sub13":
            from scripts_img import time_start_img
            time_start_img(searches)
            detect_4_silent("./audio_ffmpegs/fin_aud_1pcap.srt")
            scale_all_img(corner_radius=30)
            build_video_final(
                mode="full",
                time_range=None,
                output="build_video_final.mp4"
            )

        elif mode == "sub10":
            params["s10mode"] = "full"
            params["fontsize"] = 84
            params["spacing"] = -5
            for arg in sys.argv[2:]:
                if arg.lower().startswith("s10mode="):
                    params["s10mode"] = arg.split("=")[1]
                elif arg.lower().startswith("fontsize="):
                    params["fontsize"] = arg.split("=")[1]
                elif arg.lower().startswith("spacing="):
                    params["spacing"] = arg.split("=")[1]
            run_pupcaps_step10(s10mode=params["s10mode"], fontsize=params["fontsize"], spacing=params["spacing"])
        elif mode == "sub11":
            params["s11mode"] = "full"
            params["m_size"]  = 140
            params["w_size"]  = 140
            params["m_space"] = -5
            params["w_space"] = -5
            params["m_align"] = "RIGHT"
            params["w_align"] = "LEFT"
            params["m_anchor"] = 960
            params["w_anchor"] = 960
            for arg in sys.argv[2:]:
                if arg.lower().startswith("s11mode="):
                    params["s11mode"] = arg.split("=")[1]
                elif arg.lower().startswith("m_size="):
                    params["m_size"] = arg.split("=")[1]
                elif arg.lower().startswith("w_size="):
                    params["w_size"] = arg.split("=")[1]
                elif arg.lower().startswith("m_space="):
                    params["m_space"] = arg.split("=")[1]
                elif arg.lower().startswith("w_space="):
                    params["w_space"] = arg.split("=")[1]
                elif arg.lower().startswith("m_align="):
                    params["m_align"] = arg.split("=")[1]
                elif arg.lower().startswith("w_align="):
                    params["w_align"] = arg.split("=")[1]
                elif arg.lower().startswith("m_anchor="):
                    params["m_anchor"] = arg.split("=")[1]
                elif arg.lower().startswith("w_anchor="):
                    params["w_anchor"] = arg.split("=")[1]
            run_pupcaps_step11(s11mode=params["s11mode"], m_size=params["m_size"], w_size=params["w_size"],
                m_space=params["m_space"], w_space=params["w_space"],
                m_align=params["m_align"], w_align=params["w_align"], m_anchor=params["m_anchor"], w_anchor=params["w_anchor"])

        else:
            print(f"ERROR: The parameter '{mode}' is invalid. Type 'python scripts.py help' for instructions.")
