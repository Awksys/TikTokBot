import imageio
import numpy as np 
import subprocess
import os
import random
import json

from moviepy.editor import *

from tiktokapipy.api import TikTokAPI
import asyncio

import cv2
import os

from datetime import datetime, timedelta

import moviepy.editor as mp
from moviepy.config import change_settings
from moviepy.editor import VideoFileClip, ColorClip, CompositeVideoClip, concatenate_videoclips

change_settings({"IMAGEMAGICK_BINARY": r"C:\\Program Files\\ImageMagick-7.1.1-Q16-HDRI\\magick.exe"})

import librosa

import time

import selenium.webdriver
import undetected_chromedriver as uc
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
from selenium.webdriver.chrome.options import Options

import requests

from pytube import Playlist, YouTube

import pandas as pd

import traceback

import shutil
import pickle
import re

import chromedriver_autoinstaller


def delete_files_in_directory(directory):
    try:
        for item in os.listdir(directory):
            path = os.path.join(directory, item)
            if os.path.isfile(path):
                try:
                    os.remove(path)
                except PermissionError:
                    pass
            elif os.path.isdir(path):
                try:
                    shutil.rmtree(path)
                except PermissionError:
                    pass
        print("All deletable files and directories in the directory have been deleted.")
    except Exception as e:
        print(f"Error deleting files and directories in directory {directory}: {e}")

def delete_file(name):
    try:
        if os.path.exists(f"{base_path}/Videos/{name}"):
            os.remove(f"{base_path}/Videos/{name}")
    except:
        print("can't delete file, waiting 5min")
        time.sleep(300)
        delete_file(name)

def get_drop_video(video_file):
    reader = imageio.get_reader(video_file)
    fps = reader.get_meta_data()['fps']
    print(fps)

    sum = 0
    count = 0
    frame_id = 0
    for frame in reader:
        frame_gris = frame.mean()
        lum = round(frame_gris*10)/10
        
        if lum > 0.1:
            sum += lum
            count += 1

        frame_id += 1
    
    mean = sum/count

    min_lum = 1000
    min_lum_time = 0
    max_lum = 0
    max_lum_time = 0

    frame_id = 0
    reader_iter = iter(reader)

    try:
        next_frame = next(reader_iter)
    except StopIteration:
        next_frame = None

    while next_frame is not None:
        frame = next_frame
        try:
            next_frame = next(reader_iter)
        except StopIteration:
            next_frame = None

        frame_gris = frame.mean()
        lum = round(frame_gris * 10) / 10

        if next_frame is not None:
            next_frame_gris = next_frame.mean()
            next_lum = round(next_frame_gris * 10) / 10
        else:
            next_lum = 0

        if (lum <= min_lum or lum <= mean / 100) and (max_lum == 0 or max_lum_time < 3):
            min_lum = lum
            min_lum_time = frame_id / fps
            max_lum = 0
        elif lum > max_lum and lum - max_lum > mean / 40:
            if next_lum > min_lum:
                max_lum = lum
                max_lum_time = frame_id / fps
        elif max_lum > mean / 1.5:
            break

        frame_id += 1

    print(min_lum_time, max_lum_time)

    delta = max_lum_time - min_lum_time

    duration = reader.get_meta_data()['duration']

    if 0 < delta < 3 and min(duration*0.8, 15) > min_lum_time > 1:
        return round((min_lum_time - 1/fps)*100)/100, min(round(delta*100)/100, 1.5)
    else:
        return 0, 0
    

def detect_beats(audio_file):
    y, sr = librosa.load(audio_file)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    return y, sr, beat_times, librosa.get_duration(y=y, sr=sr)

def compute_intensities(y, sr, timecodes, window=0.1):
    intensities = []
    for timecode in timecodes:
        start_sample = int((timecode - window / 2) * sr)
        end_sample = int((timecode + window / 2) * sr)
        start_sample = max(0, start_sample)
        end_sample = min(len(y), end_sample)
        intensity = np.sqrt(np.mean(y[start_sample:end_sample]**2)) 
        intensities.append(intensity)
    return intensities

def flash_beats(video_path, audio_path, output_path, flash_duration=0.1, fade_duration=0.04, 
                flash_height=940, flash_y_position=420, start_time=2.5, end_offset=0.5, intensity_window=0.1, factor_opacity=2):
    
    y, sr, all_timecodes, duration = detect_beats(audio_path)
    timecodes = [time for time in all_timecodes if start_time < time < duration - end_offset]

    if len(timecodes) > 15:
        return False
    
    intensities = compute_intensities(y, sr, timecodes, window=intensity_window)

    print(timecodes, intensities)
    
    video = VideoFileClip(video_path).without_audio()
    clips = []
    last_time = 0

    for timecode, intensity in zip(timecodes, intensities):
        if timecode > last_time:
            clips.append(video.subclip(last_time, timecode))
        
        flash_opacity = np.clip(intensity*factor_opacity, 0.1, 0.9) 
        flash = ColorClip(size=(video.w, flash_height), color=(0, 0, 0), duration=flash_duration)
        flash = (flash.set_opacity(flash_opacity)
                      .set_fps(video.fps)
                      .set_position(("center", flash_y_position))
                      .fadein(fade_duration)
                      .fadeout(fade_duration))
        
        flash_clip = CompositeVideoClip([video.subclip(timecode, timecode + flash_duration), flash])
        clips.append(flash_clip)
        
        last_time = timecode + flash_duration

    if last_time < video.duration:
        clips.append(video.subclip(last_time, video.duration))

    final_video = concatenate_videoclips(clips)
    final_video.write_videofile(output_path, codec="libx264")

    return True


def rendering(id, index, path_file, video_type, ext, this_audio):
    global video_len

    def get_video_duration(video_path):
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        duration = float(result.stdout)
        return duration

    def set_index(index):
        nb_files = len(os.listdir(f'{base_path}/R_videos/Long_extracts'))
        if index and index < nb_files:
            return index
        else:
            return random.randint(1,nb_files)

    def select_base_vid(video_type):
        global video_len
        index = set_index(None)

        while index in slowed and video_type == "spedup":
            index = set_index(None)

        while index in spedup and video_type == "slowed":
            index = set_index(None)

        file = f"{base_path}/R_videos/Long_extracts/long_video_{index}.mp4"
        base_vid_len = get_video_duration(file)

        if base_vid_len < video_len:
            file, base_vid_len = select_base_vid(video_type)

        return file, base_vid_len
    
    if ext == "mp4":
        start_time_mp3 = 0
        video_len = get_video_duration(f"{base_path}/{path_file}")
        
        try:
            drop_time, fade_duration_sec_1 = get_drop_video(f"{base_path}/{path_file}") 
        except:
            print("error video drop detection")
            return

        file, base_vid_len = select_base_vid(video_type)
    else:
        try:
            video_type = this_audio["video_type"]
            start_time_mp3 = this_audio["start_time"]
            end_time_mp3 = this_audio["end_time"]
            audio_len = get_video_duration(f"{base_path}/{path_file}")

            if end_time_mp3 > audio_len:
                end_time_mp3 = audio_len

            video_len = end_time_mp3 - start_time_mp3
            drop_time = this_audio["drop_time"] - start_time_mp3
            fade_duration_sec_1 = this_audio["fade_duration"]
            index_long = this_audio["index_long_vid"]

            set_index(index_long)
            file = f"{base_path}/R_videos/Long_extracts/long_video_{index_long}.mp4"
            base_vid_len = get_video_duration(file)

        except NameError as e:
            print("wrong data mp3", e)
            return 

    print(drop_time, video_len)

    if video_len < max_video_len:

        if drop_time > 0:
            if fade_duration_sec_1 < fade_duration_1:
                fade_duration_sec_1 = fade_duration_1
            fade_duration_sec_2 = 0.5
        else:
            fade_duration_sec_1 = 0.75
            fade_duration_sec_2 = 0.75
            drop_time = 0.1

        cut_time = 0.1
        if video_len < 59 or video_len > 60.5 + cut_time:
            video_len -= cut_time   

        start_time = random.uniform(0, base_vid_len - (video_len-drop_time))

        subprocess.run(f'ffmpeg -y -ss {start_time} -i {file} -t {video_len - drop_time} -c copy {base_path}/Videos/ref_vid.mp4 -hide_banner -loglevel error')

        subprocess.run(f'ffmpeg -f lavfi -i color=c=black:s=1080x1920:r=60:d={drop_time} -t {drop_time} -pix_fmt yuv420p -tune stillimage {base_path}/Videos/black.mp4 -hide_banner -loglevel error')
        subprocess.run(f'ffmpeg -i {base_path}/Videos/ref_vid.mp4 -vf "fade=in:0:{fade_duration_sec_1*60},fade=out:{(video_len-drop_time)*60-fade_duration_sec_2*60}:{fade_duration_sec_2*60}" {base_path}/Videos/ref_vid_faded.mp4 -hide_banner -loglevel error')

        subprocess.run(f'ffmpeg -i {base_path}/Videos/black.mp4 -i {base_path}/Videos/ref_vid_faded.mp4 -t {video_len} -filter_complex "[0:v] [1:v] concat=n=2:v=1:a=0 [v]" -map "[v]" -c:v libx264 -c:a copy {base_path}/Videos/video_final.mp4 -hide_banner -loglevel error')

        if os.path.exists(f"video{index}_HQ.mp4"):
            path_file = f"video{index}_HQ.mp4"

        subprocess.run(f'ffmpeg -y -i {base_path}/{path_file} -ss {start_time_mp3} -t {video_len} -af "afade=t=in:st=0:d={fade_duration_sec_1},afade=t=out:st={start_time_mp3+video_len-fade_duration_sec_2}:d={fade_duration_sec_2}, dynaudnorm" {base_path}/Videos/audio_final.mp3 -hide_banner -loglevel error')

        video_file = f"{base_path}/Videos/video_final.mp4"

        if video_len < 30:
            try:
                if flash_beats(start_time=drop_time, factor_opacity=factor_opacity, video_path=f"{base_path}/Videos/video_final.mp4", audio_path=f"{base_path}/Videos/audio_final.mp3", output_path=f"{base_path}/Videos/video_final_flash.mp4"):
                    video_file = f"{base_path}/Videos/video_final_flash.mp4"
            except NameError as e:
                print("error flash", e)

        def end_edit(video_type):
            clip = VideoFileClip(video_file).without_audio()
            
            if video_type == "slowed":
                chosen_title = title[0]
            if video_type == "spedup":
                chosen_title = title[1]
            if video_type == "best":
                chosen_title = title[2]

            if video_type == "slowed":
                sp_index = len(used_videos_slowed)
            if video_type == "spedup":
                sp_index = len(used_videos_spedup)
            if video_type == "best":
                sp_index = len(used_videos_best)
        
            text_clip = TextClip(chosen_title, font=f'{base_path}/Fonts/Ghastly Panic.ttf', color='white', kerning=space_title, fontsize=size_title)
            text_clip_shadow = TextClip(chosen_title, font=f'{base_path}/Fonts/Ghastly Panic.ttf', color='black', kerning=space_title, fontsize=size_title)
            part = TextClip(f'Pt.{sp_index+1}', font=f'{base_path}/Fonts/Ghastly Panic.ttf', color='white', kerning=space_title, fontsize=size_title)
            part_shadow = TextClip(f'Pt.{sp_index+1}', font=f'{base_path}/Fonts/Ghastly Panic.ttf', color='black', kerning=space_title, fontsize=size_title)

            def setup_effects(e, opacity):
                e = e.set_opacity(opacity)
                e = e.set_start(drop_time)
                e = e.set_duration(video_len-drop_time)
                e = e.crossfadein(fade_duration_sec_1/2)
                e = e.crossfadeout(fade_duration_sec_2)
                return e

            text_clip = setup_effects(text_clip, 1)
            text_clip_shadow = setup_effects(text_clip_shadow, 0.6)
            part = setup_effects(part, 1)
            part_shadow = setup_effects(part_shadow, 0.6)

            video_size = clip.size
            text_size = text_clip.size
            text_position = ((video_size[0] - text_size[0]) // 2, (video_size[1] - text_size[1]) // 2 - space_y_title)
            text_clip = text_clip.set_position(text_position)
            text_clip_shadow = text_clip_shadow.set_position((text_position[0] + 5, text_position[1] + 5))

            part_size = part.size
            part_position = ((video_size[0] - part_size[0]) // 2, (video_size[1] - part_size[1]) // 2 + space_y_title)
            part = part.set_position(part_position)
            part_shadow = part_shadow.set_position((part_position[0] + 4, part_position[1] + 4))
        
            final_clip = CompositeVideoClip([clip, text_clip_shadow, part_shadow, text_clip, part])
            
            final_clip = final_clip.set_duration(clip.duration)

            final_clip.write_videofile(f'{base_path}/Videos/output.mov', codec='libx264', audio=False)
            
            clip.close()


        if title[0] != "":
            end_edit(video_type)
            video_file = f"{base_path}/Videos/output.mov"

        subprocess.run(f'ffmpeg -i {video_file} -i {base_path}/Videos/audio_final.mp3 -map 0:v -map 1:a -c:v copy -c:a aac -strict experimental {base_path}/Videos/{index}.mov -hide_banner -loglevel error') #-shortest -af aresample=async=1 

        if video_type == "slowed":
            used_videos_slowed.append(str(id))
            with open(base_path + '/Used_videos_slowed.py', 'w') as f:
                json.dump(used_videos_slowed, f)

        if video_type == "spedup":
            used_videos_spedup.append(str(id))
            with open(base_path + '/Used_videos_spedup.py', 'w') as f:
                json.dump(used_videos_spedup, f)

        if video_type == "best":
            used_videos_best.append(str(id))
            with open(base_path + '/Used_videos_best.py', 'w') as f:
                json.dump(used_videos_best, f)

        used_songs.append(str(id))
        with open(base_path + '/Used_videos_3.py', 'w') as f:
            json.dump(used_songs, f)


def detect_type(playlist_title, vid_title):
    slowed_words = ["slowed", "slow"]
    spedup_words = ["spedup", "speed", "sped"]

    slowed_count = 0
    spedup_count = 0

    for word in slowed_words:
        if word.lower() in vid_title:
            slowed_count += 1
        if word.lower() in playlist_title:
            slowed_count += 1

    for word in spedup_words:
        if word.lower() in vid_title:
            spedup_count += 1
        if word.lower() in playlist_title:
            spedup_count += 1
    
    if slowed_count > 0 and spedup_count == 0:        
        return "slowed"
    elif spedup_count > 0 and slowed_count == 0:
        return "spedup"
    else:
        return "best"


        
def get_video(research_user):
    try:
        print(research_user)

        time.sleep(5)

        try:
            driver2.minimize_window()
            driver2.maximize_window()
        except:
            pass

        time.sleep(5)

        driver2.get(f"https://www.tiktok.com/@{research_user}")

        time.sleep(5)

        try:
            body = WebDriverWait(driver2, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

            for _ in range(12):
                body.send_keys(Keys.PAGE_DOWN)
                time.sleep(random.randint(2,3))
        
        except:
            print("error scroll")

        def extract_video_id(tiktok_link):
            match = re.search(r'/video/(\d+)', tiktok_link)
            if match:
                return match.group(1)
            else:
                return None

        def parse_views(views_text):
            if 'M' in views_text:
                return int(float(views_text.replace('M', '').replace(',', '')) * 1000000)
            elif 'K' in views_text:
                return int(float(views_text.replace('K', '').replace(',', '')) * 1000)
            else:
                return int(views_text.replace(',', ''))

        def get_video_url():
            time.sleep(10)
            
            try:
                elements = WebDriverWait(body, 15).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//*[contains(@class, 'DivItemContainer')]"))
                )
            except:
                users_list.remove(research_user)
                print("deleting user", research_user)
                print("error searching for video")
                return None, None

            possible_vids = []
            views_sum = 0
            count = 1
            delta = timedelta(days=0)

            views_list = []

            for element in elements:    
                try:
                    views = WebDriverWait(element, 10).until(EC.presence_of_element_located((By.XPATH, ".//strong[@data-e2e='video-views']"))).text

                    #views = element.find_element(By.CSS_SELECTOR, "strong[data-e2e='video-views']").text
                    views_int = parse_views(str(views))

                    views_list.append(views_int)
                    views_sum += views_int

                except:
                    pass
                
            #print(views_list, views_sum/len(views_list), len(views_list))

            for count, element in enumerate(elements):
                
                try:
                    link = element.find_element(By.CSS_SELECTOR, "a[href]")
                    url = str(link.get_attribute("href"))
                    views = views_list[count]

                    #vid_desc = str(element.find_element(By.CSS_SELECTOR, "a[title]").get_attribute("title"))
                except:
                    continue

                mute_icons = element.find_elements(By.XPATH, ".//*[contains(@class, 'DivMuteIconContainer')]")

                if mute_icons:
                    continue
                
                if count%5 == 0:
                    if count == 35 and delta.days > 0:
                        ratio = 35/delta.days
                    elif count > 35:
                        delta = timedelta(days=int(count/ratio))        
                    else:
                        try:
                            with TikTokAPI() as api:
                                video = api.video(url)

                                create_time_str = str(video.create_time).split('+')[0]

                                date = datetime.strptime(create_time_str, "%Y-%m-%d %H:%M:%S")
                                date_now = datetime.now()
                                delta = date_now - date

                                #print(delta.days)           
                        except:
                            time.sleep(10)

                if delta.days > 180:
                    break

                vid_id = extract_video_id(url)

                if ((views > min_views and views > (views_sum/len(views_list))*1.5) or (views > min_views/2 and views > (views_sum/len(views_list))*2)) and (delta.days > 3 or count < 3) and vid_id not in used_songs and vid_id != None:
                    possible_vids.append(vid_id)  

            def get_desc(chosen_id):
                driver2.get(f"https://www.tiktok.com/@xxx/video/{chosen_id}")

                time.sleep(5)

                try:
                    element = driver2.find_element(By.CSS_SELECTOR, '[data-e2e="browse-video-desc"]')
                except:
                    print("no desc", f"https://www.tiktok.com/@xxx/video/{chosen_id}")

                cumulated_text = ""
                sub_elements = element.find_elements(By.XPATH, ".//*")
                for sub_element in sub_elements:
                    text = sub_element.text.strip()
                    if text and not text in cumulated_text:  
                        cumulated_text += text + " "

                return cumulated_text.strip()

            if len(possible_vids) > 0:    

                chosen_id = random.choice(possible_vids)

                return chosen_id, detect_type([], get_desc(chosen_id))
            else:
                return None, None

        vid_id, vid_type = get_video_url()

    except NameError as e:
        print("error with user", research_user, e)
        return None, None

    return vid_id, vid_type


def full_download(index, url, ext):
    
    path_file = f"Videos/video{index}.{ext}"

    if ext == "mp4":
        subprocess.run(f'yt-dlp -o "{base_path}/{path_file}" --format "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" {url}')

        #subprocess.run(f'yt-dlp -o {base_path}/Videos/full_vid.mkv --format "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" {url}')
        #subprocess.run(f'ffmpeg -y -i "{base_path}/Videos/full_vid.mkv" -c:v libx264 -preset slow -crf 23 -c:a copy "{base_path}/{path_file}"')
        #os.remove(f"{base_path}/Videos/full_vid.mkv")

    else:
        subprocess.run(f'yt-dlp -o {base_path}/{path_file} --extract-audio --audio-format mp3 {url}')

    time.sleep(180)
    print("downloaded !")
    
    return path_file
    

def find_video(index):
    try:
        vid_id = None
        while vid_id == None:
            username = random.choice(users_list)
            vid_id, vid_type = get_video(username)
            
            time.sleep(15)

        print(vid_id, vid_type)
        url = f"https://www.tiktok.com/@xxx/video/{vid_id}"

        path_file = full_download(index, url, "mp4")

        if os.path.exists(f"{base_path}/{path_file}"):
            rendering(vid_id, index, path_file, vid_type, "mp4", None)

    except Exception as e:
        print(e)
        traceback.print_exc()

    time.sleep(60)
    delete_file("black.mp4")
    delete_file("video_final.mp4")
    delete_file("video_final_flash.mp4")
    delete_file(f"video{index}.mp3")
    delete_file("audio_final.mp3")
    delete_file("ref_vid.mp4")
    delete_file("ref_vid_faded.mp4")
    delete_file("output.mov")
    delete_file(f"video{index}.mp4")
    delete_file(f"video{index}_HQ.mp4")

def paste_content(driver, el, content):
    driver.execute_script(
      f'''
const text = `{content}`;
const dataTransfer = new DataTransfer();
dataTransfer.setData('text/plain', text);
const event = new ClipboardEvent('paste', {{
  clipboardData: dataTransfer,
  bubbles: true
}});
arguments[0].dispatchEvent(event)
''',
      el)        

def get_element(xPath):
    try:
        time.sleep(5)
        element = WebDriverWait(driver1, 30).until(EC.presence_of_element_located((By.XPATH, xPath)))
        print("ok")
        time.sleep(5)
        return element
    except:
        print("Couldn't find element with this XPath")

def set_tags(index):
    for id in used_videos_slowed:
        if used_songs[index] in id:
            return tags[0]
    
    for id in used_videos_spedup:
        if used_songs[index] in id:
            return tags[1]
        
    return tags[2]

def get_index(index):
    for id in used_videos_slowed:
        if used_songs[index] in str(id):
            return used_videos_slowed.index(id)

    for id in used_videos_spedup:
        if used_songs[index] in str(id):
            return used_videos_spedup.index(id)  

    for id in used_videos_best:
        if used_songs[index] in str(id):
            return used_videos_best.index(id)  

    return index    

    
def change_title(text_area, index):
    try:
        try:
            text_area.click()
            time.sleep(5)
            driver1.execute_script("arguments[0].click();", text_area)
        except:
            return True

        time.sleep(2)
        text_area.send_keys(Keys.CONTROL + "a") 
        text_area.send_keys(Keys.DELETE)
        time.sleep(2)
        
        audios = read_audios(audios_path)

        name = None
        author = None

        for index_audio, audio in enumerate(audios):
            audio_url = audio["url"]
            if used_songs[index] in audio_url and audio["created"] == "Yes":
                name, _ = extract_music_info(audio_url)
                author = audio["author_name"]
                break

        sentences = ["This song 🎧", "This song >>", f"Part {get_index(index) + 1}", "🎧🖤", "This vibe 🎧", "Vibes 🎵"]
        
        if author:
            chosen_sentence = author
        elif name:
            chosen_sentence = f"{author} - {name}"
        else:
            chosen_sentence = sentences[random.randint(0,5)]

        string_variable = f"{chosen_sentence} | {datetime.now().strftime('%H:%M')} | "

        paste_content(driver1, text_area, string_variable)
        time.sleep(2)
        os.system('echo %s| clip' % set_tags(index))
        text_area.send_keys(Keys.CONTROL + "v") 

        if author:
            reset_audios(index_audio)
    
    except Exception as e:
        print("Error:", e)


def Upload(video_path, index):
    try:
        print("Upload...")

        time.sleep(5)

        try:
            driver1.minimize_window()
            driver1.maximize_window()
        except:
            pass

        time.sleep(5)

        try:
            driver1.refresh()
        except:
            time.sleep(300)
            driver1.refresh()

        time.sleep(10)

        try:
            #iframe = driver1.find_element(By.TAG_NAME, "iframe")
            iframe = driver1.find_element(By.CSS_SELECTOR, 'iframe[src*="https://www.tiktok.com/tiktokstudio/upload"]')
            driver1.switch_to.frame(iframe)
        except:
            print("error with iframe")

        time.sleep(5)

        try:
            republish_button = driver1.find_element(By.XPATH, "//button[.//span[contains(text(), 'Téléverser')]]")

            republish_button.click()
            time.sleep(5)
            driver1.execute_script("arguments[0].click();", republish_button)
        except:
            print("no republish rebutton")
            driver1.get("https://www.tiktok.com/tiktokstudio/upload?from=creator_center")
            time.sleep(10)
        
        try:
            video_input = driver1.find_element(By.CSS_SELECTOR, "input[type='file']")
            video_input.send_keys(video_path)
        except Exception as e:
            print(e)

        time.sleep(300)

        text_input = driver1.find_element(By.CSS_SELECTOR, "div[class='public-DraftStyleDefault-block public-DraftStyleDefault-ltr']")

        change_title(text_input, index)

        publish_button = driver1.find_element(By.XPATH, "//div[contains(text(),'Publier')]")

        try:
            publish_button.click()
            time.sleep(5)
            driver1.execute_script("arguments[0].click();", publish_button)
        except:
            print("error publish button")

        driver1.switch_to.default_content() 

        return "Uploaded!"
    except:
        
        driver1.refresh()

        return "Failed"

def read_audios(file_path):
    if not os.path.exists(file_path):
        return []
    
    with open(file_path, 'r') as file:
        data = json.load(file)
    
    return data.get('audios', [])

def save_audios(file_path, audios):
    with open(file_path, 'w') as file:
        json.dump({"audios": audios}, file, indent=4)

def extract_music_info(url):
    if "tiktok.com/music" in url:
        pattern = r'music/([^/?]+)-(\d+)(?:\?|$)'
    elif "drive.google.com/file/d/" in url:
        pattern = r'file/d/([^/]+)'
    else:
        return None, None
    
    match = re.search(pattern, url)
    
    if match:
        if "tiktok.com/music" in url:
            music_name = match.group(1)
            music_id = match.group(2)
            return music_name, music_id
        elif "drive.google.com/file/d/" in url:
            file_id = match.group(1)
            return  None, file_id
    
    return None, None

def extract_video_id(url):
    pattern = r'video/(\d+)(?:\?|$)'
    match = re.search(pattern, url)
    
    if match:
        video_id = match.group(1)
        return video_id
    
    return None

def reset_audios(index_audio):
    global audios

    if len(audios) > 1:
        audios.remove(audios[index_audio])
        save_audios(audios_path, audios)
        return 0
    else:
        audios = [
            {
                "url": "",
                "start_time": 0,
                "end_time": 1000,
                "drop_time": 0,
                "fade_duration": 0.25,
                "index_long_vid": 1000,
                "video_type": "best",
                "author_name": "",
                "created": "No"
            }
        ]

        save_audios(audios_path, audios)
        return 1
        
    

def get_videos(nb): 
    global audios

    audios = read_audios(audios_path)

    i=len(audios)

    print(f"Downloading {nb + i - len(os.listdir(base_path + '/Videos'))} videos, starting with video {len(used_songs)}")

    while len(os.listdir(base_path + '/Videos')) < nb + i:
        delete_files_in_directory("C:/Users/ServeurA/AppData/Local/Temp") 

        index = len(used_songs)

        audios = read_audios(audios_path)
    
        i=0
        while i < len(audios) and audios[i]["created"] == "Yes":
            i+=reset_audios(i)

        if i < len(audios):
            this_audio = audios[i]
            url = this_audio["url"]
        else:
            url = ""

        if url != "" and random.randint(1,2) == 1:
            id = int(time.time())
            ext = "mp3"

            path_file = full_download(index, url, ext, id)

            if os.path.exists(f"{base_path}/{path_file}"):
                rendering(id, index, path_file, audios[0]["video_type"], ext, this_audio)
                audios[0]["created"] = "Yes"

            delete_file("black.mp4")
            delete_file("video_final.mp4")
            delete_file("video_final_flash.mp4")
            delete_file(f"video{index}.mp3")
            delete_file("audio_final.mp3")
            delete_file("ref_vid.mp4")
            delete_file("ref_vid_faded.mp4")
            delete_file("output.mov")
            delete_file(f"{base_path}/{path_file}")
            delete_file(f"audio{index}.mp3")
            
            save_audios(audios_path, audios)

        else:
            find_video(index)

        time.sleep(300)


def reresh_params():
    global params, tags, users_list, title, space_title, size_title, space_y_title, fade_duration_1, min_views, used_songs, used_videos_slowed, used_videos_spedup, used_videos_best, max_video_len, url_yt_playlists, slowed, spedup, factor_opacity
    
    with open(base_path + '/Used_videos_slowed.py', 'r') as f:
        used_videos_slowed = json.load(f)

    with open(base_path + '/Used_videos_spedup.py', 'r') as f:
        used_videos_spedup = json.load(f)

    with open(base_path + '/Used_videos_best.py', 'r') as f:
        used_videos_best = json.load(f)

    with open(base_path + '/Used_videos_3.py', 'r') as f:
        used_songs = json.load(f)

    with open(base_path + '/Params_bot.py', 'r') as f:
        params = json.load(f)

    tags = params[2]
    users_list = params[3]
    title = params[5]
    space_title = params[6]
    size_title = params[7]
    space_y_title = params[8]
    fade_duration_1 = params[9]
    min_views = params[10]
    max_video_len = params[11]
    url_yt_playlists = params[12]
    video_types_list = params[13]
    slowed = video_types_list[0]
    spedup = video_types_list[1]
    factor_opacity = params[14]

    global audios_path
    audios_path = f"{base_path}/audios_params.json"


def set_cookies(driver, cookies_path):
    try:
        cookies = pickle.load(open(cookies_path, "rb"))

        driver.delete_all_cookies()
        
        for cookie in cookies:
            driver.add_cookie(cookie)

        driver.refresh()

    except FileNotFoundError:
        print("Le fichier de cookies n'a pas été trouvé. 2 min avant la creation du fichier cookies...")
        time.sleep(120)
        cookies = driver.get_cookies()
        pickle.dump(cookies, open(cookies_path, "wb"))

    time.sleep(5)


def setup():
    global driver1, driver2

    os.system('taskkill /F /IM chrome.exe /T')
    time.sleep(10)

    #chromedriver_path = r"C:/Users/ServeurA/Desktop/TikTok_Upload_bot/chromedriver.exe"

    chromedriver_path = chromedriver_autoinstaller.install()

    options2 = selenium.webdriver.ChromeOptions()
    options2.add_argument("--disable-search-engine-choice-screen")

    driver2 = uc.Chrome(options2, driver_executable_path=chromedriver_path, headless=False)
    driver2.set_page_load_timeout(300)
    driver2.maximize_window()
    
    driver2.get('https://www.tiktok.com/')
    set_cookies(driver2, f"{base_path}/Cookies/www.tiktok.com_cookies_2.pkl")

    time.sleep(5)

    driver2.get(f'https://www.tiktok.com/@{random.choice(users_list)}')

    options1 = selenium.webdriver.ChromeOptions()
    options1.add_argument("--disable-search-engine-choice-screen")

    driver1 = uc.Chrome(options1, driver_executable_path=chromedriver_path, headless=False)
    driver1.set_page_load_timeout(300)
    driver1.maximize_window()

    driver1.get('https://www.tiktok.com/tiktokstudio/upload?from=creator_center')
    set_cookies(driver1, f"{base_path}/Cookies/www.tiktok.com_cookies_1.pkl")



base_path = r"C:\Users\adrien\Desktop\ADRIEN\autres\Auto_Upload_TikTok".replace(os.sep, '/')

reresh_params()

setup()

get_videos(6)
#time.sleep(7200)


while True:
    reresh_params()

    if datetime.now().hour < 8 and datetime.now().hour >= 2: 
        get_videos(params[0])

    while datetime.now().hour < params[1] and datetime.now().hour > 2:
        time.sleep(60)
        reresh_params()

    print("Uploading videos...")
    video_uploaded = 0

    while len(os.listdir(base_path + '/Videos')) > 0 and video_uploaded < params[0]:

        reresh_params()

        file_list = [f for f in os.listdir(base_path + '/Videos') if f.endswith(".mov")]
        sorted_list = sorted(file_list, key=lambda x: int(os.path.splitext(x)[0]))

        file = sorted_list[0]
        index = int(os.path.splitext(file)[0])
        
        local_path = "Videos/" + file
        video_path = base_path + "/" + local_path

        print("Upload: " + video_path)

        upload = Upload(video_path, index)
        print(upload)

        if upload == "Uploaded!":
            os.remove(f"{base_path}/Videos/{file}")
            video_uploaded += 1
            print("Wait")
            time.sleep(random.randint(params[4][0], params[4][1]))
        else:
            time.sleep(300)
        
    while not (datetime.now().hour < 8 and datetime.now().hour >= 2):
        time.sleep(60)

