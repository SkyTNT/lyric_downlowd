import json
import sys
import time

from api import NetEase
import langid
import argparse
import re
import os
import signal


def quit_(signum, frame):
    print("中断")
    try:
        with open(args.save_dir + '/songs.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(downloaded_songs))
    except Exception as e:
        print(e)
    sys.exit()


def process_lyric(lyric):
    result = ''
    line_list = []
    break_num = 0
    eng_num = 0
    zh_num = 0
    ja_num = 0
    not_ja_num = 0
    only_ja_num = 0
    only_not_ja_num = 0
    both_num = 0
    lyric_len = len(lyric)
    for idx, line in enumerate(lyric):
        # 转换全角空格
        line = line.replace('\u3000', ' ')
        # 跳过说明
        if (idx <= 10 or idx >= lyric_len - 10) and re.search(
                r'(词|詞|曲|唱|歌|唄|译|譯|((V|v)ocal)|(曲(绘|繪))|(合(音|唱)))\s*(:|：)',
                line) is not None:
            continue
        # 去除时间标记
        line = re.sub(r'\[([0-9]|\.|:)*?]', '', line)
        # print(line)
        # 可能出现奇怪的分隔符
        line = re.sub(r'/|\\|\||,|，|【|】|『|』|〖|〗|<|>|\[|]|-|―|—', ' ', line)
        # 分段
        if line == '':
            break_num += 1
            line_list.append(('>brk', ''))
        if re.search(r'[A-z]', line) is not None:
            eng_num += 1
        # 去除括号文字，英文字母及特殊字符
        line = re.sub(r'(\(.*?\))|(（.*?）)|[!-/]|[:-~]', '', line)

        parses = line.split()
        len_parses = len(parses)
        if len_parses == 0:
            continue
        # 把句子分解为左边是日语，右边不是日语
        parse_lang = []
        for p in parses:
            parse_lang.append(langid.classify(p)[0])
        pos = 0
        while pos < len_parses and parse_lang[pos] == 'ja':
            pos += 1
        line = (' '.join(parses[0:pos]), ' '.join(parses[pos:]))
        line_list.append(line)
        # 统计
        if line[0] != '>brk':
            if langid.classify(line[1])[0] == 'zh':
                zh_num += 1
            if line[0] != '':
                ja_num += 1
                if line[1] == '':
                    only_ja_num += 1
            if line[1] != '':
                not_ja_num += 1
                if line[0] == '':
                    only_not_ja_num += 1
            if line[0] != '' and line[1] != '':
                both_num += 1
        # print(line)

    if (len(line_list) - break_num) == 0:
        return ''
    # 排除日英混合
    if eng_num / (len(line_list) - break_num) >= 0.3:
        return ''

    ja_rate = ja_num / (len(line_list) - break_num)
    not_ja_rate = not_ja_num / (len(line_list) - break_num)
    zh_rate = zh_num / (len(line_list) - break_num)

    only_ja_rate = only_ja_num / (len(line_list) - break_num)
    only_not_ja_rate = only_not_ja_num / (len(line_list) - break_num)
    both_rate = both_num / (len(line_list) - break_num)

    if ja_rate < 0.3:
        return ''

    need_break = False
    for line in line_list:
        # 跳过非纯日语下的无日语行
        if only_ja_rate <= 0.7 and line[0] == '':
            continue
        # 分段
        if line[0] == '>brk':
            if need_break:
                result += '\n'
            need_break = False
            continue
        else:
            need_break = True

        if only_ja_rate > 0.7:
            result += ' '.join(line).strip() + '\n'
        elif both_rate > 0.8 and zh_rate > 0.8:
            result += line[0].strip() + '\n'
        elif 0.6 > only_ja_rate > 0.4 and abs(only_not_ja_rate - only_ja_rate) < 0.1 and 0.56 > zh_rate > 0.45:
            result += ' '.join(line).strip() + '\n'
    return result.strip()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, quit_)
    signal.signal(signal.SIGTERM, quit_)

    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--song-list', nargs='+', type=int, default=[], help="歌单id (一个或多个)")
    parser.add_argument('-d', '--save-dir', type=str, default="out", help="输出路径")
    parser.add_argument('-c', '--ctn', action='store_true', help="继续上次")
    args = parser.parse_args()
    print(args)

    downloaded_songs = []
    last_song_list_index = 0
    last_song_index = 0
    num = 0
    if not os.path.exists(args.save_dir):
        os.mkdir(args.save_dir)
    if args.ctn and os.path.exists(args.save_dir + '/last.json'):
        try:
            with open(args.save_dir + '/last.json', 'r', encoding='utf-8') as f:
                last = json.loads(f.read())
                args.song_list = last['song_list']
                last_song_list_index = last['lid']
                last_song_index = last['sid']
                num = last['num']
        except Exception as e:
            print(e)
    if os.path.exists(args.save_dir + '/songs.json'):
        try:
            with open(args.save_dir + '/songs.json', 'r', encoding='utf-8') as f:
                downloaded_songs = json.loads(f.read())
        except Exception as e:
            print(e)

    a = NetEase()
    # print(process_lyric(a.song_lyric(644688)))
    # 28707396 26124515 26219552 28545793 860337 27672105 644688
    while last_song_list_index < len(args.song_list):
        songs = a.playlist_songlist(args.song_list[last_song_list_index])
        print(f"song list {last_song_list_index}")
        while last_song_index < len(songs):
            song_id = songs[last_song_index]['id']
            if song_id in downloaded_songs:
                last_song_index += 1
                continue
            print(f"song list {last_song_list_index} song {last_song_index} , id: {song_id}")
            lyric = process_lyric(a.song_lyric(song_id))
            if lyric != '':
                downloaded_songs.append(song_id)
                print('  '.join(lyric.split('\n')))
                with open(args.save_dir + '/last.json', 'w', encoding='utf-8') as f:
                    f.write(json.dumps(
                        {'song_list': args.song_list, 'lid': last_song_list_index, 'sid': last_song_index, 'num': num}))
                with open(args.save_dir + f'/{num:08d}.txt', 'w', encoding='utf-8') as f:
                    f.write(lyric)
                num += 1
            last_song_index += 1
        last_song_list_index += 1
        last_song_index = 0
    with open(args.save_dir + '/songs.json', 'w', encoding='utf-8') as f:
        f.write(json.dumps(downloaded_songs))
