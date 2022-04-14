import json

from api import NetEase
import langid
import argparse
import re
import os


def process_lyric(lyric):
    result = ''
    line_list = []
    for idx, line in enumerate(lyric):
        # 转换全角空格
        line = line.replace('\u3000', ' ')
        # 跳过说明
        if idx < 6 and ('作词' in line or '作詞' in line or '歌词' in line or '作曲' in line or '编曲' in line or
                        '編曲' in line or '原曲' in line or '歌曲' in line or '演唱' in line or '歌：' in line or
                        '歌 ：' in line or '歌:' in line or '歌 :' in line or 'Vocal' in line or '歌唱' in line or
                        '曲绘' in line or '曲繪' in line):
            continue
        # 去除时间标记，括号，英文字母
        line = re.sub(r'\[([0-9]|\.|:)*?\]|(\(.*?\))|(（.*?）)|[A-z]', '', line)
        parses = line.split()
        len_parses = len(parses)
        if len_parses == 0:
            continue
        # 把句子分解为左边是日语，右边不是日语
        for i in range(0, len_parses + 1):
            if i == len_parses:
                line = (line, '')
                break
            if langid.classify(' '.join(parses[i:]))[0] != 'ja':
                line = (' '.join(parses[0:i]), ' '.join(parses[i:]))
                break
        line_list.append(line)
    if len(line_list) == 0:
        return ''

    # 统计含日文句子的数目和每个句子尾部为非日语的数目
    ja_num = 0
    not_ja_num = 0
    for line in line_list:
        if line[0] != '':
            ja_num += 1
        if line[1] != '':
            not_ja_num += 1

    # 只有一点点日语，可能不是日语歌
    if ja_num / len(line_list) < 0.1:
        return ''
    # 如果每个句子尾部为非日语的数目占比大于0.5，很大可能为翻译
    is_with_trans = not_ja_num / len(line_list) > 0.5
    for line in line_list:
        if line[0] == '':
            continue
        if is_with_trans:
            result += line[0].strip() + '\n'
        else:
            result += ' '.join(line).strip() + '\n'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--song-list', nargs='+', type=int, default=[], help="歌单id (一个或多个)")
    parser.add_argument('-d', '--save-dir', type=str, default="out", help="输出路径")
    parser.add_argument('-c', '--ctn', action='store_true', help="继续上次")
    args = parser.parse_args()
    print(args)

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

    a = NetEase()
    while last_song_list_index < len(args.song_list):
        songs = a.playlist_songlist(args.song_list[last_song_list_index])
        while last_song_index < len(songs):
            song_id = songs[last_song_index]['id']
            lyric = process_lyric(a.song_lyric(song_id))
            if lyric != '':
                print(f"{last_song_list_index} {last_song_index} , id: {song_id}")
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
