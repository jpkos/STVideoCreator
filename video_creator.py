# -*- coding: utf-8 -*-
"""
Created on Fri Oct 14 14:47:52 2022

@author: jankos

For creating videos from SeeTrue eye tracker frames and eyeData.csv files.
To ensure that the eye tracker data is matched with the frames correctly,
the script reads the current frame number from eyeData.csv file, then
matches it with the frame number that was read from the frame file name.
This is probably not the fastest option for creating the videos.

As of now, SeeTrue stores frames with the name 'frame_<frame number>.jpeg', e.g.
'frame_1415.jpeg'. This script uses regular expressions to find the <frame number> (e.g.'1415') part
and converts it to int.
If file naming format changes, then script has to be modified. It also assumes that
frames are stored as jpeg.

Videos are created using the av library, which is a wrapper for the ffmpeg program.

jani.koskinen@uef.fi

"""


import cv2
import pandas as pd
import glob
import re
import argparse
import os
import time
import av
from fractions import Fraction
import numpy as np
#%%
TIME_BASE = 1000 #SeeTrue data given as milliseconds or 1/1000 of sec
#names of relevant columns in eyedata.csv (note: old seetrue recordings did not name columns)
COL_REGARD_X = ' Point Of Regard X '
COL_REGARD_Y = ' Point Of Regard Y '
COL_SCENE_PIC = 'Frame Number '
COL_TIME_STAMP = ' Time Stamp '
#%%
def get_frame_paths_df(folder):
    frames = glob.glob(os.path.join(folder, '*.jpeg')) #seeTrue saves frames as jpeg
    frame_numbers = [int(re.findall('frame_(\d+).jpeg', x)[0]) for x in frames] #get frame numbers from file names
    df = pd.DataFrame({'file':frames, COL_SCENE_PIC:frame_numbers})
    df = df.sort_values(by=COL_SCENE_PIC).reset_index(drop=True)
    return df

def create_video_writer(video_name, framerate, width, height, timebase=1000):
    container = av.open(f'{video_name}.mp4', mode='w')
    stream = container.add_stream('mpeg4', rate=framerate)
    stream.width = width
    stream.height = height
    stream.pix_fmt = 'yuv420p'
    stream.codec_context.time_base = Fraction(1, timebase) #millisec
    return container, stream

def get_eyedata_df(args):
    eye_data = pd.read_csv(args.eyedata, sep=';')
    if COL_REGARD_X not in eye_data.columns: #Quick hack to deal with missing frame names in old seetrue files
        eye_data = pd.DataFrame(data=eye_data.values,
                                columns=[COL_SCENE_PIC, COL_TIME_STAMP,
                                                    COL_REGARD_X, COL_REGARD_Y,
                                                    'S1', 'S2', 'S3', 'S4', 'S5'])
    eye_data = eye_data.replace(to_replace=' -nan(ind) ', value=-1)
    eye_data[[COL_REGARD_X, COL_REGARD_Y]] = eye_data[[COL_REGARD_X, COL_REGARD_Y]].astype(float)
    eye_data['time_str'] = (pd.to_datetime(eye_data[COL_TIME_STAMP], unit='ms').
                            dt.strftime('%H:%M:%S:%f').str[:-3])
    if args.frame_range is not None:
        eye_data = eye_data[eye_data[COL_SCENE_PIC].between(args.frame_range[0],
                                                            args.frame_range[1]-1)]
    return eye_data

#%%
def create_video(args):
    # Load eye tracker data from eyeData.csv
    eye_data = get_eyedata_df(args)
    frame_length = eye_data[COL_SCENE_PIC].max() - eye_data[COL_SCENE_PIC].min() + 1
    print(f'Creating video from {args.frames}')
    print(f'Total frames to be written: {frame_length}')
    # Get frame paths and create video writer    
    frame_paths = get_frame_paths_df(args.frames)
    args.update_status_n = min(args.update_status_n,
                               int(frame_length//2),
                               int(len(frame_paths)//2))
    frame = cv2.imread(frame_paths['file'].iloc[0])
    height, width, _ = frame.shape
    if args.video_name == '':
        video_name = os.path.basename(args.frames)
    else:
        video_name = args.video_name
    container, stream = create_video_writer(video_name,
                                            args.framerate,
                                            width,
                                            height,
                                            TIME_BASE)
    # Eyedata file has gaze location as ratio, convert to pixels
    if args.draw_gaze:
        eye_data[COL_REGARD_X] = (eye_data[COL_REGARD_X]*width).astype(int)
        eye_data[COL_REGARD_Y] = (eye_data[COL_REGARD_Y]*height).astype(int)
    # Start writing video    
    total_time = 0
    written_frames = 0
    time_left = 0
    start_time_total = time.time()
    if args.use_real_fps:
        time_stamps = (eye_data[COL_TIME_STAMP] - eye_data[COL_TIME_STAMP].min()).values
    else:
        print(f'Output video will have framerate of {args.framerate} fps.\n'
              'If you want to use the actual recording duration with variable frame rate,\n'
              'run this script with the command --use-real-fps')
        time_step = (1/args.framerate)*TIME_BASE
        time_stamps = [s*time_step for s in range(len(eye_data))]
    write_times = np.zeros(len(eye_data)+1)
    combined = eye_data.merge(frame_paths, how='left', on=COL_SCENE_PIC)
    combined['file'] = combined['file'].fillna('')
    for i, row in combined.iterrows():
        start_time_frame = time.time()
        if not row['file'] == '':
            frame = cv2.imread(row['file'])
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if args.draw_gaze:
                gaze_x = row[COL_REGARD_X]
                gaze_y = row[COL_REGARD_Y]
                frame = cv2.circle(frame, (gaze_x, gaze_y), radius=5,
                                   color=(255,255,0), thickness=2)
            if args.draw_frame_n:
                frame = cv2.putText(frame, str(row[COL_SCENE_PIC]), (25,15), 
                                    cv2.FONT_HERSHEY_COMPLEX, 0.5, (0,255,255), 1, 1)
            if args.draw_time:
                frame = cv2.putText(frame, row['time_str'], (25,35), 
                                    cv2.FONT_HERSHEY_COMPLEX, 0.5, (0,255,255), 1, 1)
            frame = av.VideoFrame.from_ndarray(frame, format="rgb24")
        frame.pts = time_stamps[i]
        for packet in stream.encode(frame):
            container.mux(packet)
        written_frames += 1
        write_time = (time.time() - start_time_frame)
        write_times[written_frames] = write_time
        if written_frames%args.update_status_n==0:
            write_rate_mean = 1/np.mean(write_times[written_frames-args.update_status_n:written_frames])
            time_left = (frame_length-written_frames)/write_rate_mean
            print(f'{video_name} writing frame: {row[COL_SCENE_PIC]+1} '
                  f'(approx. {(write_rate_mean):.0f} frames/sec)'
                  f' Estimated time left: {time_left:.0f} s', end='\r')
    total_time = time.time() - start_time_total
    print(f'\nvideo saved as {video_name}.mp4')
    print(f'elapsed time {total_time:.4f} s')
    print(f'total written frames {written_frames}')
    for packet in stream.encode():
        container.mux(packet)
    container.close()
    
#%%
if __name__=='__main__':
    """
    Example use (run on command line):
        python video_creator.py --frames recording/ScenePics --eyedata recording/ScenePics.csv --draw-gaze --draw-frame-n --frame-range 300 600 --use-real-fps
        This will write the frames from range 300 to 600 into video, 
        with the gaze cursor (--draw-gaze argument) 
        and frame number in the upper left corner (--draw-frame-n)
        default frame rate is 25 frames/second
        if --use-real-fps is given, then each frame duration is read from the
        eyeData.csv file (default column ' Time Stamp ')
        output video is saved as ScenePics.mp4
        
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--frames', type=str, help='path to folder with frames', required=True)
    parser.add_argument('--eyedata', type=str, help='path to csv file with eye data', required=True)
    parser.add_argument('--framerate', type=int, default=25, help='output video frame rate as fps')
    parser.add_argument('--draw-gaze', action='store_true', help='draw gaze location to frame')
    parser.add_argument('--draw-frame-n', action='store_true', help='draw frame number to frame')
    parser.add_argument('--draw-time', action='store_true', help='print recording time from eyeData.csv to frame')
    parser.add_argument('--frame-range', nargs='+', type=int, help='create video from range of frames')
    parser.add_argument('--use-real-fps', action='store_true', help='read frame durations from eyeData.csv')
    parser.add_argument('--video-name', type=str, default='', help='output video name, default is frame folder name')
    parser.add_argument('--update-status-n', type=int, default=1000, help='print status after every n written frames')
    args = parser.parse_args()
    
    create_video(args)