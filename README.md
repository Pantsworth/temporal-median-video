# temporal-median-video

Python program for processing a temporal median filter effect across a set of frames from a video. 
<br><br>
**Usage:**

`python temporal_median.py -i "<set_of_frames>" -o "<output_path>" -l <number of frames to process> -offset <length of filter in frames> -simul <frames to process simultaneously> `

<br>
**Example:**

Original:
<img src="img/gopro_surf_trim.gif" width="500px"/>

TMF:
<img src="img/gopro_surf_tmf.gif" width="500px"/>


[![Gopro Surfing](https://img.youtube.com/vi/6K8_iQOxo4w/0.jpg)](https://www.youtube.com/watch?v=6K8_iQOxo4w)

https://www.youtube.com/watch?v=6K8_iQOxo4w

<br>

**Dependencies:**

[PIL] (http://www.pythonware.com/products/pil/)
[Numpy] (http://www.numpy.org/)

<br>

**Prior Works:**

Similar to zo7's median-video (but that one is in C++ and requires OpenCV). 
https://github.com/zo7/median-video

