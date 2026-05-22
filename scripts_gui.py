# -*- coding: utf-8 -*-
# @Author: Cao Phi Ho
# @Date:   2026/04/08, 21:35
# @Last Modified by:   CPH
# @Last Modified time: 2026/05/22, 03:47
# @Last Modified time: 2026/04/08, 21:35 Create file

import tkinter as tk
from tkinter import ttk
import subprocess
import threading
import queue

import os, sys, io

os.environ["PYTHONIOENCODING"] = "utf-8"


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
        return 1, 1, 1
    elif test_encoder("h264_qsv"):
        return 1, 0, 0
    elif test_encoder("h264_nvenc"):
        return 1, 0, 0
    else:
        return 0, 0, 0

GPU, AMD, HOME = detect_gpu()
printf("GPU: ", GPU,"; ", "AMD: ", AMD,"; ", "HOME: ", HOME)


# ===== CONFIG =====
exe_py      = "python"
SCRIPT_1    = "scripts.py"
SCRIPT_2    = "scripts_img.py"

BTN_W   = 6
HIST_H  = 1

# ===== COMMANDS (cmd, info) =====
MAIN_COMMANDS = [ # Đổi tên thành MAIN_COMMANDS
    ("python scripts.py 0",                     "step0 : Create SCRIPTS.YT, SEARCHES.YT, CHECK not ENG"),
    ("python scripts.py 1",                     "step1 : TTS use elevenlabs, create AUDIO_ELABS dir"),
    ("python scripts.py 2",                     "step2 : Add filter to all audio, create AUDIO_FFMPEG dir"),
    ("python scripts.py 3 0.80 2 5",            "step3 : Insert SILENT, merge audio, create AUDIO_FFMPEGS dir -final, HOOK + INFO + MAIN + BYE-"),
    ("python scripts.py 4",                     "step4 : Create bk_database.whis, fin_aud_0.srt, fin_aud_0.txt"),
    ("python scripts.py 5",                     "step5 : Create fin_aud_0_cor.srt, fin_aud_0_cor.txt + CHECK_WORDS"),
    ("python scripts.py 6",                     "step6 : Create bk_wlongest, _1.srt, _1.txt + CHECK _0_cor.srt AND _1.srt"),
    ("python scripts.py 7",                     "step7 : Create fin_aud_2.seg, fin_aud_2ali.seg, fin_aud_2ali.srt"),
    ("python scripts.py 8",                     "step8 : Create _1pcap.srt + CHECK MATCH"),
    ("python scripts.py 9",                     "step9 : Create _1pcap_lest.srt"),
    ("python scripts.py 10 s10mode=test",       "step10: Create fin_aud_1pcap_lest.MOV, [DEFAULT] fontsize=88, spacing=-5"),
    ("python scripts.py 10 s10mode=full",       "step10: Create fin_aud_1pcap.MOV fin_aud_1pcap.MP4, [DEFAULT] fontsize=88, spacing=-5"),
    ("python scripts.py 11 s11mode=test",       "step11: Create _2man/woman_lest.srt _2man/woman_lest.MOV _2man/woman_lest.MP4, [DEFAULT] m_size=140 w_size=140 m_space=-5 w_space=-5 m_align='RIGHT' w_align='LEFT' m_anchor=960 w_anchor=960 GENDER=\"\""),
    ("python scripts.py 11 s11mode=full",       "step11: Create _2man/woman.srt _2man/woman.MOV _2man/woman.MP4, [DEFAULT] m_size=140 w_size=140 m_space=-5 w_space=-5 m_align='RIGHT' w_align='LEFT' m_anchor=960 w_anchor=960 GENDER=\"\""),
    ("python scripts_img.py 12",                "step12: Collect illustration image, create IMAGES dir, USE: python scripts_img.py 12"),
    ("python scripts_img.py 13",                "step13: Create time START/END of images (bk_img_time)"),
    ("python scripts.py 14",                    "step14: Detect 4 silent points (bk_4_silent)"),
    ("python scripts.py 15",                    "step15: Scale images to 960*540"),
    ("python scripts.py 16",                    "step16: CREATE FINAL_FULL VIDEO"),
    ("python scripts_img.py 17",                "step17: CREATE THUMBNAIL, USE: python scripts_img.py 17"),
]
NUM_MAIN = len(MAIN_COMMANDS) # Số lượng lệnh chính

# ===== SUB COMMANDS (cmd, info) ===== # Danh sách lệnh phụ
SUB_COMMANDS = [
    ("python scripts.py sub0",                  "sub_s0: Moving Old Data & Backup", "audio_elabs=1 audio_ffmpeg=1 audio_ffmpegs=1 bk_file=1 fin_file=1 img_file=1 images=1"),
    ("python scripts_img.py sub1",              "sub_s1: Check Searchs Var is match with scripts", ""),
    ("python scripts.py sub2",                  "sub_s2: Rename 4 img in DL, copy 4 img to WD", ""),
    ("python scripts.py sub3",                  "NO_SUBFUNC: PLEASE_DECLARATION", ""),
    ("python scripts.py sub4",                  "sub_s4: Remove bk_database.whis", ""),
    ("python scripts.py sub5",                  "NO_SUBFUNC: PLEASE_DECLARATION", ""),
    ("python scripts.py sub6",                  "COMBO: step 1/2/3/4", ""),
    ("python scripts.py sub7",                  "COMBO: step 5/6/7/8-8/9", ""),
    ("python scripts.py sub8",                  "COMBO: step 1/2/3/4/5/6/7/8-8/9", ""),
    ("python scripts.py sub9",                  "NO_SUBFUNC: PLEASE_DECLARATION", ""),
    ("python scripts.py sub10 s10mode=test",    "ss_10: Create fin_aud_1pcap_lest.MOV", "fontsize=88 spacing=-5"),
    ("python scripts.py sub10 s10mode=full",    "ss_10: Create fin_aud_1pcap.MOV fin_aud_1pcap.MP4", "fontsize=88 spacing=-5"),
    ("python scripts.py sub11 s11mode=test",    "ss_11: Create _2man/woman_lest.srt _2man/woman_lest.MOV _2man/woman_lest.MP4", "m_size=140 w_size=140 m_space=-5 w_space=-5 m_align=\"RIGHT\" w_align=\"LEFT\" m_anchor=960 w_anchor=960 GENDER=\"\""),
    ("python scripts.py sub11 s11mode=full",    "ss_11: Create _2man/woman.srt _2man/woman.MOV _2man/woman.MP4", "m_size=140 w_size=140 m_space=-5 w_space=-5 m_align=\"RIGHT\" w_align=\"LEFT\" m_anchor=960 w_anchor=960 GENDER=\"\""),
    ("python scripts.py sub12",                 "NO_SUBFUNC: PLEASE_DECLARATION", ""),
    ("python scripts.py sub13",                 "COMBO: step 13/14/15/16 -> FINAL_FULL VIDEO", ""),
    ("python scripts.py sub14",                 "NO_SUBFUNC: PLEASE_DECLARATION", ""),
    ("python scripts.py sub15",                 "NO_SUBFUNC: PLEASE_DECLARATION", ""),
    ("python scripts.py sub16",                 "NO_SUBFUNC: PLEASE_DECLARATION", ""),
    ("python scripts_img.py 18",                 "step18: CREATE DESCRIPTION", ""),
]
NUM_SUB = len(SUB_COMMANDS) # Số lượng lệnh phụ

# ===== GLOBAL =====
log_q = queue.Queue()

# Trạng thái được chia thành 'main' và 'sub'
state = {
    'main': {i: {"proc": None, "count": 0, "status": "IDLE"} for i in range(NUM_MAIN)},
    'sub':  {i: {"proc": None, "count": 0, "status": "IDLE"} for i in range(NUM_SUB)}
}

# Tương tự cho enabled
enabled = {
    'main': {i: False for i in range(NUM_MAIN)},
    'sub':  {i: False for i in range(NUM_SUB)}
}
en_all = False

# Các widget sẽ được chia thành main và sub
en_btn = {'main': {}, 'sub': {}}
btn = {'main': {}, 'sub': {}}
status_lbl = {'main': {}, 'sub': {}}
prog = {'main': {}, 'sub': {}}
hist = {'main': {}, 'sub': {}}


def toggle_en_all():

    global en_all

    en_all = not en_all

    color = "yellow" if en_all else "SystemButtonFace"

    en_all_btn.config(bg=color)

    # ===== MAIN =====
    for i in en_btn['main']:

        enabled['main'][i] = en_all
        en_btn['main'][i].config(bg=color)

    # ===== SUB =====
    for i in en_btn['sub']:

        enabled['sub'][i] = en_all
        en_btn['sub'][i].config(bg=color)

    log(f"[ENALL] {'ON' if en_all else 'OFF'}")


# ===== LOG =====
def log(msg):
    log_q.put(msg)


def update_log():
    while not log_q.empty():
        msg = log_q.get()
        global_log.insert(tk.END, msg + "\n")
        global_log.see(tk.END)
    root.after(100, update_log)


# ===== STATE =====
def set_state(func_type, i, st):

    state[func_type][i]["status"] = st
    state[func_type][i]["proc"] = None

    count = state[func_type][i]["count"]

    # text hiển thị
    txt = f"{st}|{count}"

    # MAIN
    if func_type == 'main':

        if st == "IDLE":
            prog['main'][i]['value'] = 0

        elif st == "BUSY":
            prog['main'][i]['value'] = 50

        elif st == "DONE":
            prog['main'][i]['value'] = 100

        prog_text[i]['text'] = txt

    # SUB
    else:

        if st == "IDLE":
            prog['sub'][i]['value'] = 0

        elif st == "BUSY":
            prog['sub'][i]['value'] = 50

        elif st == "DONE":
            prog['sub'][i]['value'] = 100

        prog_text_sub[i]['text'] = txt

    if st in ["DONE", "IDLE"]:
        state[func_type][i]["proc"] = None


# def update_status():
#     Cập nhật trạng thái cho cả main và sub functions
#     for i in range(NUM_MAIN):
#         status_lbl['main'][i].config(
#             text=f"{state['main'][i]['status']} | {state['main'][i]['count']}"
#         )
#     for i in range(NUM_SUB):
#         status_lbl['sub'][i].config(
#             text=f"{state['sub'][i]['status']} | {state['sub'][i]['count']}"
#         )


# ===== INFO =====
def show_info(func_type, i):
    if func_type == 'sub':
        # Lấy tuple 3 phần tử từ SUB_COMMANDS
        cmd, log_info, args = SUB_COMMANDS[i]

        # 1. In ra GLOBAL LOG: Chỉ in phần log_info
        log(f"[SUB{i}] {log_info}")

        # 2. In ra ScrolledText (arg_text): In log_info kèm cụm ", ARG: " và phần args
        arg_text.delete("1.0", tk.END)  # Xóa nội dung cũ
        combined_info = f"{args}"
        arg_text.insert(tk.END, combined_info)
    else:
        # Đối với MAIN_COMMANDS (vẫn dùng cấu trúc 2 phần tử như cũ)
        log(f"[MAIN{i}] {MAIN_COMMANDS[i][1]}")
        arg_text.delete("1.0", tk.END)


# ===== ADD: TOGGLE EN =====
def toggle_en(func_type, i):
    # Sử dụng func_type để truy cập đúng enabled và en_btn
    enabled[func_type][i] = not enabled[func_type][i]

    if enabled[func_type][i]:
        en_btn[func_type][i].config(bg="yellow")
    else:
        en_btn[func_type][i].config(bg="SystemButtonFace")


# ===== RUN =====
def run_func(func_type, i):
    if not enabled[func_type][i]:
        log(f"[{func_type.upper()}{i}] SKIPPED: Not enabled.")
        return

    commands_list = MAIN_COMMANDS if func_type == 'main' else SUB_COMMANDS
    base_cmd = commands_list[i][0] # Lấy chuỗi lệnh

    # LẤY ARGUMENTS TỪ Ô NHẬP LIỆU (Phần mới)
    extra_args = arg_text.get("1.0", tk.END).strip()
    final_cmd = f"{base_cmd} {extra_args}" if extra_args else base_cmd

    printf("base_cmd: ", base_cmd)
    printf("extra_args: ", extra_args)
    printf("final_cmd: ", final_cmd)

    def task():
        try:
            set_state(func_type, i, "BUSY")
            log(f"[BUSY] {final_cmd}")

            process = subprocess.Popen(
                final_cmd, shell=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, encoding='utf-8'
            )
            state[func_type][i]["proc"] = process

            for line in process.stdout:
                msg = line.strip()
                #hist[func_type][i].insert(tk.END, msg + "\n")
                #hist[func_type][i].see(tk.END)
                log(f"[{func_type.upper()}{i}] {msg}")

            process.wait()
            state[func_type][i]["count"] += 1
            set_state(func_type, i, "DONE")
        except Exception as e:
            log(f"[ERROR] {str(e)}")
            set_state(func_type, i, "IDLE")

    threading.Thread(target=task, daemon=True).start()


# ===== STOP =====
def stop_func(func_type, i):
    p = state[func_type][i]["proc"]
    if p and p.poll() is None:
        p.terminate()
        set_state(func_type, i, "IDLE")
        log(f"[STOP-{func_type.upper()}{i}]")


# ===== RESET =====
def reset_all():

    global en_all

    # ===== MAIN =====
    for i in range(NUM_MAIN):

        p = state['main'][i]["proc"]

        if p and p.poll() is None:
            p.terminate()

        # reset state
        state['main'][i] = {
            "proc": None,
            "count": 0,
            "status": "IDLE"
        }

        # reset UI
        set_state('main', i, "IDLE")

        # disable
        enabled['main'][i] = False

        if i in en_btn['main']:
            en_btn['main'][i].config(bg="SystemButtonFace")


    # ===== SUB =====
    for i in range(NUM_SUB):

        p = state['sub'][i]["proc"]

        if p and p.poll() is None:
            p.terminate()

        # reset state
        state['sub'][i] = {
            "proc": None,
            "count": 0,
            "status": "IDLE"
        }

        # reset UI
        set_state('sub', i, "IDLE")

        # disable
        enabled['sub'][i] = False

        if i in en_btn['sub']:
            en_btn['sub'][i].config(bg="SystemButtonFace")


    # reset ENALL
    en_all = False
    en_all_btn.config(bg="SystemButtonFace")

    # clear text
    arg_text.delete("1.0", tk.END)

    # clear log
    global_log.delete("1.0", tk.END)

    log("=== RESET ALL ===")


# ===== GUI =====
root = tk.Tk()
root.title("Pipeline GUI (Tuple Commands)")
root.geometry("800x800") # Tăng chiều cao để chứa các hàng Sub-Func mới

# opacity 85%
if HOME==1:
    root.attributes('-alpha', 1.0)
else:
    root.attributes('-alpha', 0.25)

main_frame = tk.Frame(root) # Khung cho các chức năng chính
main_frame.pack()

# --- Main Functions Widgets ---
# btn = {'main': {}, 'sub': {}}
# status_lbl = {'main': {}, 'sub': {}}
# prog = {'main': {}, 'sub': {}}
# hist = {'main': {}, 'sub': {}}

# Dòng bắt đầu của các widget chính
main_row_offset = 0

# ===== ROW 0: FUNC (MAIN) =====
#for i in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 14, 15, 16, 17, 18, 19]:
for i in [0, 4]:
    btn['main'][i] = tk.Button(main_frame, text=f"F{i}", width=BTN_W, command=lambda i=i: run_func('main', i))
    btn['main'][i].grid(row=main_row_offset + 0, column=i, padx=1, pady=1)

i=0
tk.Button(main_frame, text=f"checkEN", width=BTN_W, command=lambda i=i: show_info('main', i)).grid(row=main_row_offset + 1, column=i)

i=4
tk.Button(main_frame, text=f"cre_whis", width=BTN_W, command=lambda i=i: show_info('main', i)).grid(row=main_row_offset + 1, column=i)

# i = 10
# btn['main'][i] = tk.Button(main_frame, text=f"F10-test", width=BTN_W, command=lambda i=i: run_func('main', i))
# btn['main'][i].grid(row=main_row_offset + 0, column=i, padx=1, pady=1)

# i = 11
# btn['main'][i] = tk.Button(main_frame, text=f"F10-full", width=BTN_W, command=lambda i=i: run_func('main', i))
# btn['main'][i].grid(row=main_row_offset + 0, column=i, padx=1, pady=1)

# i = 12
# btn['main'][i] = tk.Button(main_frame, text=f"F11-test", width=BTN_W, command=lambda i=i: run_func('main', i))
# btn['main'][i].grid(row=main_row_offset + 0, column=i, padx=1, pady=1)

# i = 13
# btn['main'][i] = tk.Button(main_frame, text=f"F11-full", width=BTN_W, command=lambda i=i: run_func('main', i))
# btn['main'][i].grid(row=main_row_offset + 0, column=i, padx=1, pady=1)

# i = 14
# btn['main'][i] = tk.Button(main_frame, text=f"F12", width=BTN_W, command=lambda i=i: run_func('main', i))
# btn['main'][i].grid(row=main_row_offset + 0, column=i, padx=1, pady=1)
i=14
tk.Button(main_frame, text=f"images", width=BTN_W, command=lambda i=i: show_info('main', i)).grid(row=main_row_offset + 1, column=i)

# i = 15
# btn['main'][i] = tk.Button(main_frame, text=f"F13", width=BTN_W, command=lambda i=i: run_func('main', i))
# btn['main'][i].grid(row=main_row_offset + 0, column=i, padx=1, pady=1)

# i = 16
# btn['main'][i] = tk.Button(main_frame, text=f"F14", width=BTN_W, command=lambda i=i: run_func('main', i))
# btn['main'][i].grid(row=main_row_offset + 0, column=i, padx=1, pady=1)

# i = 17
# btn['main'][i] = tk.Button(main_frame, text=f"F15", width=BTN_W, command=lambda i=i: run_func('main', i))
# btn['main'][i].grid(row=main_row_offset + 0, column=i, padx=1, pady=1)

# i = 18
# btn['main'][i] = tk.Button(main_frame, text=f"F16", width=BTN_W, command=lambda i=i: run_func('main', i))
# btn['main'][i].grid(row=main_row_offset + 0, column=i, padx=1, pady=1)

# i = 19
# btn['main'][i] = tk.Button(main_frame, text=f"F17", width=BTN_W, command=lambda i=i: run_func('main', i))
# btn['main'][i].grid(row=main_row_offset + 0, column=i, padx=1, pady=1)
i=19
tk.Button(main_frame, text=f"thumb", width=BTN_W, command=lambda i=i: show_info('main', i)).grid(row=main_row_offset + 1, column=i)

# ===== ROW 1: INFO (MAIN) =====
#for i in range(NUM_MAIN):
#for i in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 14, 15, 16, 17, 18, 19]:
# for i in [4]:
#     tk.Button(main_frame, text=f"info", width=BTN_W,
#               command=lambda i=i: show_info('main', i)).grid(row=main_row_offset + 1, column=i)

# ===== ADD: ROW 2 EN (MAIN) =====
#for i in range(NUM_MAIN):
#for i in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 14, 15, 16, 17, 18, 19]:
for i in [0, 4]:
    en_btn['main'][i] = tk.Button(main_frame, text="EN", width=BTN_W,
                           command=lambda i=i: toggle_en('main', i))
    en_btn['main'][i].grid(row=main_row_offset + 2, column=i)

# ===== ROW 3: STOP (MAIN) =====
# for i in range(NUM_MAIN):
#     tk.Button(main_frame, text=f"Stop", width=BTN_W, bg="red",
#               command=lambda i=i: stop_func('main', i)).grid(row=main_row_offset + 3, column=i)

# # ===== ROW 4: STATUS (MAIN) =====
# for i in range(NUM_MAIN):
#     status_lbl['main'][i] = tk.Label(main_frame, text="IDLE|0", width=BTN_W)
#     status_lbl['main'][i].grid(row=main_row_offset + 4, column=i)

# # ===== ROW 5: PROGRESS (MAIN) =====
# for i in range(NUM_MAIN):
#     prog['main'][i] = ttk.Progressbar(main_frame, length=60)
#     prog['main'][i].grid(row=main_row_offset + 4, column=i)

# ===== ROW 5: PROGRESS (MAIN) =====
prog_frame = {}
prog_text  = {}

for i in range(NUM_MAIN):
    # frame chứa cả progress + text
    prog_frame[i] = tk.Frame(main_frame, width=60, height=20)
    prog_frame[i].grid(row=main_row_offset + 5, column=i)

    # progressbar
    prog['main'][i] = ttk.Progressbar( prog_frame[i], length=60, mode='determinate' )
    prog['main'][i].place(x=0, y=0, width=60, height=20)

    # text overlay
    prog_text[i] = tk.Label( prog_frame[i], text="IDLE|0", font=("Arial", 7) )
    prog_text[i].place(relx=0.5, rely=0.5, anchor="center")

# ===== ROW 6: HISTORY (MAIN) =====
# for i in range(NUM_MAIN):
#     hist['main'][i] = tk.Text(main_frame, height=HIST_H, width=BTN_W)
#     hist['main'][i].grid(row=main_row_offset + 6, column=i)


# --- Sub-Functions Frame ---
# Tạo một Frame riêng biệt cho các Sub-Functions
sub_frame = tk.Frame(root)
sub_frame.pack(pady=1) # Thêm padding giữa Main và Sub

# Dòng bắt đầu của các widget phụ (đảm bảo không bị chồng lấn với main_frame)
sub_row_offset = 0


# ===== ROW 0: SUB-FUNC =====
# for i in range(NUM_SUB):
#     btn['sub'][i] = tk.Button(sub_frame, text=f"SubF{i}", width=BTN_W, command=lambda i=i: run_func('sub', i))
#     btn['sub'][i].grid(row=sub_row_offset + 0, column=i, padx=1, pady=1)
i = 0
btn['sub'][i] = tk.Button(sub_frame, text=f"Be_F0", width=BTN_W, bg="cyan", command=lambda i=i: run_func('sub', i))
btn['sub'][i].grid(row=sub_row_offset + 0, column=i, padx=1, pady=1)

i=0
tk.Button(sub_frame, text=f"mv_old", width=BTN_W, command=lambda i=i: show_info('sub', i)).grid(row=sub_row_offset + 1, column=i)

i = 1
btn['sub'][i] = tk.Button(sub_frame, text=f"Af_F0_1", width=BTN_W, bg="cyan", command=lambda i=i: run_func('sub', i))
btn['sub'][i].grid(row=sub_row_offset + 0, column=i, padx=1, pady=1)

i=1
tk.Button(sub_frame, text=f"check", width=BTN_W, command=lambda i=i: show_info('sub', i)).grid(row=sub_row_offset + 1, column=i)

i = 2
btn['sub'][i] = tk.Button(sub_frame, text=f"Af_F0_2", width=BTN_W, bg="cyan", command=lambda i=i: run_func('sub', i))
btn['sub'][i].grid(row=sub_row_offset + 0, column=i, padx=1, pady=1)

i=2
tk.Button(sub_frame, text=f"mv_img", width=BTN_W, command=lambda i=i: show_info('sub', i)).grid(row=sub_row_offset + 1, column=i)

i = 4
btn['sub'][i] = tk.Button(sub_frame, text=f"Af_F4", width=BTN_W, bg="cyan", command=lambda i=i: run_func('sub', i))
btn['sub'][i].grid(row=sub_row_offset + 0, column=i, padx=1, pady=1)
i=4
tk.Button(sub_frame, text=f"rm_whis", width=BTN_W, command=lambda i=i: show_info('sub', i)).grid(row=sub_row_offset + 1, column=i)

i = 6
btn['sub'][i] = tk.Button(sub_frame, text=f"C_1234", width=BTN_W, bg="red", command=lambda i=i: run_func('sub', i))
btn['sub'][i].grid(row=sub_row_offset + 0, column=i, padx=1, pady=1)
i = 7
btn['sub'][i] = tk.Button(sub_frame, text=f"5678-89", width=BTN_W, bg="red", command=lambda i=i: run_func('sub', i))
btn['sub'][i].grid(row=sub_row_offset + 0, column=i, padx=1, pady=1)
i = 8
btn['sub'][i] = tk.Button(sub_frame, text=f"C_1->9", width=BTN_W, bg="red", command=lambda i=i: run_func('sub', i))
btn['sub'][i].grid(row=sub_row_offset + 0, column=i, padx=1, pady=1)

i = 10
btn['sub'][i] = tk.Button(sub_frame, text=f"SF10-test", width=BTN_W, bg="cyan", command=lambda i=i: run_func('sub', i))
btn['sub'][i].grid(row=sub_row_offset + 0, column=i, padx=1, pady=1)

i = 11
btn['sub'][i] = tk.Button(sub_frame, text=f"SF10-full", width=BTN_W, bg="cyan", command=lambda i=i: run_func('sub', i))
btn['sub'][i].grid(row=sub_row_offset + 0, column=i, padx=1, pady=1)

i = 12
btn['sub'][i] = tk.Button(sub_frame, text=f"SF11-test", width=BTN_W, bg="cyan", command=lambda i=i: run_func('sub', i))
btn['sub'][i].grid(row=sub_row_offset + 0, column=i, padx=1, pady=1)

i = 13
btn['sub'][i] = tk.Button(sub_frame, text=f"SF11-full", width=BTN_W, bg="cyan", command=lambda i=i: run_func('sub', i))
btn['sub'][i].grid(row=sub_row_offset + 0, column=i, padx=1, pady=1)

i = 15
btn['sub'][i] = tk.Button(sub_frame, text=f"13/4/5/6", width=BTN_W, bg="red", command=lambda i=i: run_func('sub', i))
btn['sub'][i].grid(row=sub_row_offset + 0, column=i, padx=1, pady=1)
i=15
tk.Button(sub_frame, text=f"video", width=BTN_W, command=lambda i=i: show_info('sub', i)).grid(row=sub_row_offset + 1, column=i)

i = 19
btn['sub'][i] = tk.Button(sub_frame, text=f"F18", width=BTN_W, bg="cyan", command=lambda i=i: run_func('sub', i))
btn['sub'][i].grid(row=sub_row_offset + 0, column=i, padx=1, pady=1)
i=19
tk.Button(sub_frame, text=f"title", width=BTN_W, command=lambda i=i: show_info('sub', i)).grid(row=sub_row_offset + 1, column=i)


# ===== ROW 1: SUB-INFO =====
# for i in range(NUM_SUB):
#     tk.Button(sub_frame, text=f"sinfo", width=BTN_W, command=lambda i=i: show_info('sub', i)).grid(row=sub_row_offset + 1, column=i)
i=6
tk.Button(sub_frame, text=f"step1->4", width=BTN_W, command=lambda i=i: show_info('sub', i)).grid(row=sub_row_offset + 1, column=i)
i=7
tk.Button(sub_frame, text=f"step5->9", width=BTN_W, command=lambda i=i: show_info('sub', i)).grid(row=sub_row_offset + 1, column=i)
i=8
tk.Button(sub_frame, text=f"step1->9", width=BTN_W, command=lambda i=i: show_info('sub', i)).grid(row=sub_row_offset + 1, column=i)

i=10
tk.Button(sub_frame, text=f"sinfo", width=BTN_W, command=lambda i=i: show_info('sub', i)).grid(row=sub_row_offset + 1, column=i)

i=11
tk.Button(sub_frame, text=f"sinfo", width=BTN_W, command=lambda i=i: show_info('sub', i)).grid(row=sub_row_offset + 1, column=i)

i=12
tk.Button(sub_frame, text=f"sinfo", width=BTN_W, command=lambda i=i: show_info('sub', i)).grid(row=sub_row_offset + 1, column=i)

i=13
tk.Button(sub_frame, text=f"sinfo", width=BTN_W, command=lambda i=i: show_info('sub', i)).grid(row=sub_row_offset + 1, column=i)


# ===== ADD: ROW 2 SUB-EN =====
# for i in range(NUM_SUB):
#     en_btn['sub'][i] = tk.Button(sub_frame, text="SEN", width=BTN_W, command=lambda i=i: toggle_en('sub', i))
#     en_btn['sub'][i].grid(row=sub_row_offset + 2, column=i)
i=0
en_btn['sub'][i] = tk.Button(sub_frame, text="SEN", width=BTN_W, command=lambda i=i: toggle_en('sub', i))
en_btn['sub'][i].grid(row=sub_row_offset + 2, column=i)

i=1
en_btn['sub'][i] = tk.Button(sub_frame, text="SEN", width=BTN_W, command=lambda i=i: toggle_en('sub', i))
en_btn['sub'][i].grid(row=sub_row_offset + 2, column=i)

i=2
en_btn['sub'][i] = tk.Button(sub_frame, text="SEN", width=BTN_W, command=lambda i=i: toggle_en('sub', i))
en_btn['sub'][i].grid(row=sub_row_offset + 2, column=i)

i=4
en_btn['sub'][i] = tk.Button(sub_frame, text="SEN", width=BTN_W, command=lambda i=i: toggle_en('sub', i))
en_btn['sub'][i].grid(row=sub_row_offset + 2, column=i)

i=6
en_btn['sub'][i] = tk.Button(sub_frame, text="SEN", width=BTN_W, command=lambda i=i: toggle_en('sub', i))
en_btn['sub'][i].grid(row=sub_row_offset + 2, column=i)
i=7
en_btn['sub'][i] = tk.Button(sub_frame, text="SEN", width=BTN_W, command=lambda i=i: toggle_en('sub', i))
en_btn['sub'][i].grid(row=sub_row_offset + 2, column=i)
i=8
en_btn['sub'][i] = tk.Button(sub_frame, text="SEN", width=BTN_W, command=lambda i=i: toggle_en('sub', i))
en_btn['sub'][i].grid(row=sub_row_offset + 2, column=i)


i=10
en_btn['sub'][i] = tk.Button(sub_frame, text="SEN", width=BTN_W, command=lambda i=i: toggle_en('sub', i))
en_btn['sub'][i].grid(row=sub_row_offset + 2, column=i)

i=11
en_btn['sub'][i] = tk.Button(sub_frame, text="SEN", width=BTN_W, command=lambda i=i: toggle_en('sub', i))
en_btn['sub'][i].grid(row=sub_row_offset + 2, column=i)

i=12
en_btn['sub'][i] = tk.Button(sub_frame, text="SEN", width=BTN_W, command=lambda i=i: toggle_en('sub', i))
en_btn['sub'][i].grid(row=sub_row_offset + 2, column=i)

i=13
en_btn['sub'][i] = tk.Button(sub_frame, text="SEN", width=BTN_W, command=lambda i=i: toggle_en('sub', i))
en_btn['sub'][i].grid(row=sub_row_offset + 2, column=i)

i=15
en_btn['sub'][i] = tk.Button(sub_frame, text="SEN", width=BTN_W, command=lambda i=i: toggle_en('sub', i))
en_btn['sub'][i].grid(row=sub_row_offset + 2, column=i)

i=19
en_btn['sub'][i] = tk.Button(sub_frame, text="SEN", width=BTN_W, command=lambda i=i: toggle_en('sub', i))
en_btn['sub'][i].grid(row=sub_row_offset + 2, column=i)


# ===== ROW 3: SUB-STOP =====
# for i in range(NUM_SUB):
#     tk.Button(sub_frame, text=f"S_Stop", width=BTN_W, bg="red",
#               command=lambda i=i: stop_func('sub', i)).grid(row=sub_row_offset + 3, column=i)

# # ===== ROW 4: SUB-STATUS =====
# for i in range(NUM_SUB):
#     status_lbl['sub'][i] = tk.Label(sub_frame, text="IDLE|0", width=BTN_W)
#     status_lbl['sub'][i].grid(row=sub_row_offset + 4, column=i)

# # ===== ROW 5: SUB-PROGRESS =====
# for i in range(NUM_SUB):
#     prog['sub'][i] = ttk.Progressbar(sub_frame, length=60)
#     prog['sub'][i].grid(row=sub_row_offset + 4, column=i)

# ===== ROW 4: SUB STATUS + PROGRESS =====
prog_frame_sub = {}
prog_text_sub  = {}

for i in range(NUM_SUB):
    # container
    prog_frame_sub[i] = tk.Frame(sub_frame, width=60, height=20)
    prog_frame_sub[i].grid(row=sub_row_offset + 4, column=i)

    # progress bar
    prog['sub'][i] = ttk.Progressbar( prog_frame_sub[i], length=60, mode='determinate' )
    prog['sub'][i].place( x=0, y=0, width=60, height=20 )

    # overlay text
    prog_text_sub[i] = tk.Label( prog_frame_sub[i], text="IDLE|0", font=("Arial", 7) )
    prog_text_sub[i].place( relx=0.5, rely=0.5, anchor="center" )


# ===== ROW 6: SUB-HISTORY =====
# for i in range(NUM_SUB):
#     hist['sub'][i] = tk.Text(sub_frame, height=HIST_H, width=BTN_W)
#     hist['sub'][i].grid(row=sub_row_offset + 6, column=i)


# CHÈN Ô NHẬP LIỆU VÀO GIỮA SUB_FRAME VÀ BOTTOM_FRAME
arg_label = tk.Label(root, text="--- Arguments / Guide / Log Input ---", fg="blue", font=("Arial", 10, "bold"))
arg_label.pack(pady=(1, 0))

# ScrolledText để nhập tham số (ví dụ: audio_elabs=1 ...)
arg_text = tk.Text(root, height=1, width=180, font=("Consolas", 10))
arg_text.pack(pady=1)


# ===== RESET / ENALL (Dùng chung cho cả Main và Sub) =====
bottom_frame = tk.Frame(root)
bottom_frame.pack(pady=1)

tk.Button(bottom_frame, text="RESET", bg="red", fg="white", width=10, command=reset_all).pack(side="left", padx=5)
en_all_btn = tk.Button(bottom_frame, text="EnAll", width=10, command=toggle_en_all)
en_all_btn.pack(side="left", padx=5)

# Global Log
global_log = tk.Text(root, height=28, width=160, bg="#f0f0f0")
global_log.pack()

update_log()
#update_status()
root.mainloop()
