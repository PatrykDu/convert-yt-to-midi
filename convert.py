#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
import getopt
import cv2
import numpy as np
from mido import Message, MidiFile, MidiTrack, MetaMessage, bpm2tempo
from pytube import YouTube
from main import VIDEO_LINK



# ——— default settings ———
__activationThreshold = 30
__minKeyWidth         = 3
__start               = 0
__end                 = -1
__output              = "out.mid"
__keyboardHeight      = 0.85
__keyPositions        = []
__defaultValues       = []
__middleC             = 0
# ————————————————————————

def __extractKeyPositions(brightness_row):
    global __keyPositions, __defaultValues
    __keyPositions.clear()
    __defaultValues.clear()
    max_b = max(brightness_row)
    min_b = min(brightness_row)
    white_th = min_b + (max_b - min_b)*0.6
    black_th = min_b + (max_b - min_b)*0.4

    in_white = in_black = False
    start_i  = 0
    for i, b in enumerate(brightness_row):
        # detect whites
        if b > white_th:
            if not (in_white or in_black):
                in_white = True
                start_i  = i
        else:
            if in_white:
                in_white = False
                if i - start_i > __minKeyWidth:
                    pos = (start_i + i)//2
                    __keyPositions.append(pos)
                    __defaultValues.append(brightness_row[pos])
        # detect blacks
        if b < black_th:
            if not (in_black or in_white):
                in_black = True
                start_i  = i
        else:
            if in_black:
                in_black = False
                if i - start_i > __minKeyWidth:
                    pos = (start_i + i)//2
                    __keyPositions.append(pos)
                    __defaultValues.append(brightness_row[pos])
    print(f"Wykryto {len(__keyPositions)} klawiszy.")

def __labelKeys(brightness_row):
    global __middleC
    candidates = []
    for i in range(len(__defaultValues)-6):
        seq = __defaultValues[i:i+7]
        if (seq[0] > __activationThreshold and seq[1] > __activationThreshold and
            seq[2] < __activationThreshold and seq[3] > __activationThreshold and
            seq[4] < __activationThreshold and seq[5] > __activationThreshold and
            seq[6] > __activationThreshold):
            candidates.append(i+1)
    if not candidates:
        print("Nie wykryto poprawnej klawiatury.")
        sys.exit(2)
    __middleC = candidates[len(candidates)//2]
    print("Middle C jako index:", __middleC)

def __getPressedKeys(current):
    return [
        1 if abs(current[i] - __defaultValues[i]) > __activationThreshold else 0
        for i in range(len(current))
    ]

def __print_usage():
    print("Usage: main.py <youtube-url|'file.mp4'> "
          "-o <output.mid> -s <start_sec> -e <end_sec> "
          "-t <threshold> -k <keyboard_height> -b <bpm>")

def __parse_options(argv):
    global __start, __end, __output, __activationThreshold, __keyboardHeight, __bpm
    __bpm = 120

    try:
        opts, args = getopt.getopt(
            argv[1:], "ho:s:e:k:t:b:",
            ["help","output=","start=","end=","keyboard_height=","threshold=","bpm="]
        )
    except getopt.GetoptError:
        __print_usage(); sys.exit(1)

    for opt, arg in opts:
        if opt in ("-h","--help"):
            __print_usage(); sys.exit(0)
        elif opt in ("-o","--output"):
            __output = arg
        elif opt in ("-s","--start"):
            __start = float(arg)
        elif opt in ("-e","--end"):
            __end = float(arg)
        elif opt in ("-k","--keyboard_height"):
            __keyboardHeight = float(arg)
        elif opt in ("-t","--threshold"):
            __activationThreshold = int(arg)
        elif opt in ("-b","--bpm"):
            __bpm = int(arg)

    if not args:
        __print_usage(); sys.exit(1)
    return args[0]

def convert(video, is_url,
            output, start, end,
            keyboard_height, threshold, bpm):
    global __activationThreshold, __keyboardHeight
    __activationThreshold = threshold
    __keyboardHeight     = keyboard_height

    # Cleanup
    pycache_patch = os.path.join(os.path.dirname(__file__), "__pycache")
    videos_patch = os.path.join(os.path.dirname(__file__), "videos")
    outmid_patch = os.path.join(os.path.dirname(__file__), "out.mid")
    if os.path.exists(pycache_patch):
        shutil.rmtree(pycache_patch)
    if os.path.exists(videos_patch):
        shutil.rmtree(videos_patch)
    if os.path.exists(outmid_patch):
        os.remove(outmid_patch)

    subprocess.run([
        "yt-dlp",
        "-f", "mp4",
        "-o", "videos/MyVideo.mp4",
        VIDEO_LINK
    ])

    # — przygotuj plik MIDI z jednym trackiem —
    mid    = MidiFile()
    track  = MidiTrack()
    mid.tracks.append(track)
    mid.ticks_per_beat = 480

    # name + tempo
    track.append(MetaMessage('track_name',  name='Piano',  time=0))
    track.append(MetaMessage('set_tempo',   tempo=bpm2tempo(bpm), time=0))

    # — open or download video —
    if is_url:
        print("Downloading video…")
        yt     = YouTube(video)
        stream = yt.streams.filter(progressive=True, file_extension='mp4')\
                           .order_by('resolution').desc().first()
        stream.download('videos/')
        safe   = yt.title.replace("/","_").replace("|","_")
        path   = f"videos/{safe}.mp4"
    else:
        path = video

    cap     = cv2.VideoCapture(path)
    success, frame = cap.read()
    if not success:
        sys.exit(f"Cannot open video: {path}")
    fps     = cap.get(cv2.CAP_PROP_FPS)
    h, w, _ = frame.shape
    print(f"Processing {h}p @ {fps:.2f}fps, BPM={bpm}…")

    kb_y       = int(h * keyboard_height)
    start_fr   = int(start * fps)
    end_fr     = int(end * fps) if end>0 else float('inf')
    last_state = []
    last_time  = start_fr
    frame_idx  = 0

    # — frames analysis —
    while success and frame_idx <= end_fr:
        row = frame[kb_y]
        brightness = [np.mean(row[x]) for x in range(w)]

        if frame_idx == start_fr:
            __extractKeyPositions(brightness)
            __labelKeys(brightness)
            last_state = [0]*len(__keyPositions)

        if frame_idx >= start_fr:
            pressed = __getPressedKeys([brightness[pos] for pos in __keyPositions])
            for i, cur in enumerate(pressed):
                if cur != last_state[i]:
                    note = 60 - __middleC + i
                    dt = int((frame_idx - last_time)
                             * mid.ticks_per_beat * bpm
                             / (60 * fps))
                    if cur:
                        track.append(Message('note_on', note=note, velocity=64, time=dt))
                    else:
                        track.append(Message('note_off', note=note, velocity=127, time=dt))
                    last_time = frame_idx
            last_state = pressed

        success, frame = cap.read()
        frame_idx += 1

    # ending
    track.append(MetaMessage('end_of_track', time=0))
    mid.save(output)
    print("Saved →", output)


if __name__ == "__main__":
    video = __parse_options(sys.argv)
    is_url = not video.lower().endswith('.mp4')
    convert(
      video, is_url,
      output=__output,
      start=__start,
      end=__end,
      keyboard_height=__keyboardHeight,
      threshold=__activationThreshold,
      bpm=__bpm
    )
