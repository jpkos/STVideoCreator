# STVideoCreator
Scripts for generating annotated videos from eye tracker data

Takes video frames and eye tracking data from the SeeTrue eye tracker (https://www.seetruetechnologies.com/) and combines them into a video. You can draw annotations such as the time stamp, frame number, and gaze cursor into the frame. Time stamps and frame numbers help when working with some other data in addition to the eye tracker data.

Example use (run on command line):
> python video_creator.py --frames recording/ScenePics --eyedata recording/ScenePics.csv --draw-gaze --draw-frame-n --frame-range 300 600 --use-real-fps --draw-time

This will write the frames from range 300 to 600 into video, with the gaze cursor (--draw-gaze argument), time stamp (--draw-time argument) and frame number in the upper left corner (--draw-frame-n) default frame rate is 25 frames/second, but if --use-real-fps is given, then each frame's duration is read from the eyeData.csv file (default column ' Time Stamp ') output video is saved as ScenePics.mp4

The create_from_folder.py script allows creating multiple videos in parallel. This can save time if enough computational resources are available. See the documentation in the python file for more information.
