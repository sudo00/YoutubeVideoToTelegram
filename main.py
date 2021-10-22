
from pytube import YouTube
import requests
from moviepy.editor import VideoFileClip
import os.path
from transliterate import translit
import re
from telethon import TelegramClient
from telethon.tl.types import DocumentAttributeAudio, DocumentAttributeVideo
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from sys import stdout
from config import *
import pickle


def progress(current, total):
    stdout.write("\r" + str(f"{current * 100 / total:.1f}%"))
    stdout.flush()


def save_obj(obj, name):
    with open('obj/' + name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


def load_obj(name):
    with open('obj/' + name + '.pkl', 'rb') as f:
        return pickle.load(f)


def get_clean_word(word):
    word = translit(word, 'ru', reversed=True)
    word = re.sub('[^A-Za-z]', '', word)
    return word


def get_youtube_ids():
    video_ids = {}
   
    if os.path.isfile('obj/video_ids.pkl') == False:
        url = 'https://www.googleapis.com/youtube/v3/search?order=date&part=snippet&channelId=' + \
            YOUTUBE_CHANNEL_ID + '&maxResults=5000&key=' + YOUTUBE_API_KEY
        youtube_response = requests.get(url).json()

        while True:
            for video in youtube_response['items']:
                if 'videoId' in video['id']:
                    video_ids[video['id']['videoId']] = video['snippet']['title']
            if ('nextPageToken' in youtube_response) == False:
                break
            url = 'https://www.googleapis.com/youtube/v3/search?order=date&part=snippet&channelId=' + YOUTUBE_CHANNEL_ID + \
                '&maxResults=5000&key=' + YOUTUBE_API_KEY + \
                '&pageToken=' + youtube_response['nextPageToken']
            youtube_response = requests.get(url).json()

        save_obj(video_ids, 'video_ids')
    else:
        video_ids = load_obj('video_ids')

    return video_ids


def main():
    client = TelegramClient('session_name', API_ID, API_HASH)
    client.start()

    video_ids = get_youtube_ids()
    logvideo_ids = video_ids.copy()

    for videoId in reversed(video_ids):
        yt = YouTube('https://www.youtube.com/watch?v=' + videoId)
        video_title = video_ids[videoId]
        file_name = get_clean_word(video_title)

        print('Скачиваем видео - ' + video_title)
        yt.streams.get_highest_resolution().download(
            filename = file_name + '.mp4',
            output_path = './mp4'
        )

        print('Конвертируем в mp3...')
        video = VideoFileClip('./mp4/' + file_name + '.mp4')
        video.audio.write_audiofile('./mp3/' + file_name + '.mp3')

        print('Загружаем на канал с видео...')
        if os.path.isfile('./mp4/' + file_name + '.mp4'):
            metadata = extractMetadata(createParser('./mp4/' + file_name + '.mp4'))
            resp = client.send_file(
                entity = TELEGRAM_VIDEO_CHAT_ENTITY,
                file='./mp4/' + file_name + '.mp4',
                attributes=(DocumentAttributeVideo(
                (0, metadata.get('duration').seconds)[metadata.has('duration')],
                (0, metadata.get('width'))[metadata.has('width')],
                (0, metadata.get('height'))[metadata.has('height')]
                ),),
                progress_callback=progress
            )
            stdout.write("\n")
            video_message_id = resp.id

        print('Загружаем на канал с аудио...')
        if os.path.isfile('./mp3/' + file_name + '.mp3'):
            resp = client.send_file(
                entity = TELEGRAM_AUDIO_CHAT_ENTITY,
                file='./mp3/' + file_name + '.mp3',
                attributes=(DocumentAttributeAudio(
                    voice = False,
                    duration = 0,
                    title = video_title
                ),),
                progress_callback=progress
            )
            audio_message_id = resp.id

        print('Линкуем...')
        client.edit_message(
            entity = TELEGRAM_AUDIO_CHAT_ENTITY,
            message_id = audio_message_id,
            parse_mode = 'HTML',
            message = video_title + ' <a href="https://t.me/c/' + TELEGRAM_VIDEO_CHAT_ID +
            '/' + str(video_message_id) + '">[ССЫЛКА НА ВИДЕО]</a>'
        )

        client.edit_message(
            entity = TELEGRAM_VIDEO_CHAT_ENTITY,
            message_id = video_message_id,
            parse_mode = 'HTML',
            message = video_title + ' <a href="https://t.me/c/' + TELEGRAM_AUDIO_CHAT_ID +
            '/' + str(audio_message_id) + '">[ССЫЛКА НА АУДИО]</a>'
        )

        logvideo_ids.pop(videoId)
        save_obj(logvideo_ids, 'video_ids')

    input('Готово!')


if __name__ == '__main__':
    main()
