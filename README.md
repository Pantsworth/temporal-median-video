# temporal-median-video

Python program for processing a temporal median filter effect across a set of frames from a video. 
<br><br>

## Installation
1. Install ffmpeg
2. Create a python virtual environment
    ```
    mkdir venv
    python3 -m venv venv
    source venv/bin/activate
    ```

3. Install requirements
    ```
    pip install -r requirements.txt
    ```

4. Run the code!


## Usage
```
python temporal_median.py -i "<set_of_frames>" -o "<output_path>" -l <number of frames to process> -offset <length of filter in frames> -simul <frames to process simultaneously>
```

Ex.
```
python temporal_median.py -i img/trimmed_saigon_1.mp4 -v
```


## Examples
### Surfing Example:

Original:

[<img src="img/gopro_surf_trim.gif" width="500px"/>](https://www.youtube.com/watch?v=LUGksGa4WJA)<br>
https://www.youtube.com/watch?v=LUGksGa4WJA

TMF:

[<img src="img/gopro_surf_tmf.gif" width="500px"/>](https://www.youtube.com/watch?v=6K8_iQOxo4w)<br>
https://www.youtube.com/watch?v=6K8_iQOxo4w

### Saigon Traffic Example:

Original: https://www.youtube.com/watch?v=8QCsQnr2w4w

TMF: https://www.youtube.com/watch?v=Yhy1uc9s8IU



## Similar Stuff
Similar to zo7's median-video (but that one is in C++ and requires OpenCV). 
https://github.com/zo7/median-video

