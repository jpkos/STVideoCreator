# -*- coding: utf-8 -*-
"""
Created on Mon Oct 17 10:21:44 2022

@author: jankos

Call video creator on list of video folders
"""

import video_creator as vc
import glob
import os
from dataclasses import dataclass
from multiprocessing import Pool
import argparse
#%%
@dataclass
class Arguments:
    frames: str
    eyedata: str
    framerate: int
    draw_gaze: bool
    draw_frame_n: bool
    draw_time: bool
    frame_range: list
    use_real_fps: bool
    video_name: str
    update_status_n: int

# Folder should contain a 'ScenePics' folder with the frames and the 'eyeData.csv'
# file with eye tracking data
def video_from_folder(folder):
    frame_folder = os.path.join(folder, 'ScenePics')
    eye_data_file = os.path.join(folder, 'eyeData.csv')
    video_name = os.path.basename(folder)
    args = Arguments(frames=frame_folder,
                     eyedata=eye_data_file,
                     video_name=video_name,
                     framerate=25,
                     draw_gaze=False,
                     draw_frame_n=True,
                     frame_range=None,
                     use_real_fps=True,
                     draw_time=True,
                     update_status_n=500)
    vc.create_video(args)
    
if __name__ == '__main__':
    """
    example use:
        python create_from_folders.py --folders 'seeTrueRecordings/participants/*' --run-parallel
    
    --folders is a string that is given to glob.glob() to find the folders. Therefore supports wildcard characters.
    E.g. the above path given to --folders returns all the folders inside'seeTrueRecordings/participants/'
    If we gave the path 'seeTrueRecordings/participants/P*', it would take all folders that start with P
    See https://docs.python.org/3/library/glob.html for more examples on use
    
    --run-parallel will start generating each video at the same time. more resource
    intensive, but given enough computational power should be much faster than generating
    each video sequentally
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--folders', type=str, help='pathname to folder that contains folders with seetrue recordings')
    parser.add_argument('--run-parallel', action='store_true', help='create all videos in parallel')
    args = parser.parse_args()
    folders = glob.glob(rf'{args.folders}')
    if args.run_parallel:
        pool = Pool()
        pool.map(video_from_folder, folders)
    else:
        for folder in folders:
            video_from_folder(folder)
    