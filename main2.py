import argparse
import os
import signal
import sys
import time

from bs4 import BeautifulSoup
import requests
import langid
import pickle


def quit_(signum, frame):
    print("中断")
    save()
    sys.exit()


def get_lyric(idx: int):
    req = requests.get(f"https://www.uta-net.com/song/{idx}")
    bs = BeautifulSoup(req.text, 'lxml')
    info = bs.find("div", class_="song-infoboard")
    if info is None:
        return None
    name = info.find('h2').text
    if args.show:
        print(f"{idx:08d}:\t{name}")

    lyric_div = bs.find("div", id="kashi_area")
    if lyric_div is None:
        return None
    lyric = ""
    for s in lyric_div.contents:
        if s.name == "br":
            lyric += "\n"
        else:
            lyric += s.text.replace('\u3000', ' ')
    lyric_lines = lyric.split("\n")
    line_num = len(lyric_lines)
    for i in range(0, line_num):
        s = lyric_lines[i]
        if s is None:
            continue
        if i != line_num - 1 and s.startswith("(") and s.endswith(")") and langid.classify(lyric_lines[i + 1])[
            0] != 'ja':
            lyric_lines[i] = s[1:-1]
            lyric_lines[i + 1] = None
    return [name, "\n".join([s for s in lyric_lines if isinstance(s, str)])]


def save():
    print(f"save {len(songs)} songs")
    with open(args.output_file, "wb") as f:
        pickle.dump(songs, f)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, quit_)
    signal.signal(signal.SIGTERM, quit_)

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--start-id', type=int, default=0, help="开始id")
    parser.add_argument('-n', '--max-song-num', type=int, default=300000, help="歌词最大数量")
    parser.add_argument('-o', '--output-file', type=str, default="out.pkl", help="输出路径")
    parser.add_argument('-v', '--show', action='store_true', help="打印过程")
    parser.add_argument('-c', '--ctn', action='store_true', help="继续上次")
    args = parser.parse_args()
    print(args)

    songs = []
    if args.ctn and os.path.exists(args.output_file):
        with open(args.output_file, 'rb') as f:
            songs = pickle.load(f)
            args.start_id = songs[-1]["id"] + 1

    last_time = time.time()

    for i in range(args.start_id, args.start_id + args.max_song_num):
        lyric = get_lyric(i)
        if lyric is None:
            continue
        if lyric[1] != "" and 6 < lyric[1].count('\n') < 150:
            songs.append({"id": i, "name": lyric[0], "lyric": lyric[1]})
        if time.time() - last_time > 5:
            save()
            last_time = time.time()
    save()
