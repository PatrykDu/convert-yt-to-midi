# run_convert.py
from convert import convert

START_VIDEO = 5
END_VIDEO = 150
VIDEO_LINK = "https://www.youtube.com/watch?v=nQj9ZMcaLtA"

convert(
    "videos/MyVideo.mp4",
    False,
    output="out.mid",
    start=START_VIDEO,
    end=END_VIDEO,
    keyboard_height=0.85,
    threshold=5,
    bpm=60
)
