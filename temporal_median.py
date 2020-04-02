from __future__ import print_function

import argparse
import numpy
import os
import glob
import sys

from timeit import default_timer as timer
from multiprocessing import Process, Pool


from PIL import Image
import imageio

IMAGE_EXTENSIONS = ["*.tiff", "*.tif", "*.jpeg", "*.png", "*.jpg", "*.dng"]
MOVIE_EXTENSIONS = ["*.mp4", "*.mov"]


def get_frame_data(input_data, frame_number):
    """ Gets the frame with the specified index """
    if isinstance(input_data, list):
        return Image.open(input_data[frame_number])
    return input_data.get_data(frame_number)


def get_number_of_frames(input_data):
    if isinstance(input_data, list):
        return len(input_data)
    return round(input_data.get_meta_data()['fps'] * input_data.get_meta_data()['duration']) -1


def make_a_glob(root_dir):
    """ Creates a glob of images from specified path. Checks for JPEG, PNG, TIFF, DNG

    Args:
        root_dir (str): path to a video or directory of images

    Returns:
        (list, imageio.core.format.Reader): glob of images from input path
    """
    # video file, return here
    if os.path.isfile(root_dir):
        return imageio.get_reader(root_dir)

    # start hunting for an image sequence
    if not os.path.exists(root_dir):
        raise IOError("No such path: %s" % root_dir)

    if not root_dir.endswith("/"):
        root_dir += "/"

    input_data = glob.glob(root_dir + "*.tif")

    for ext in IMAGE_EXTENSIONS:
        if len(input_data) == 0:
            input_data = glob.glob(root_dir + ext)
            if len(input_data) == 0:
                input_data = glob.glob(root_dir + ext.upper())
            if ext == IMAGE_EXTENSIONS[(len(IMAGE_EXTENSIONS)-1)] and len(input_data) == 0:
                raise IOError("No images found in directory: %s" % root_dir)
        else:
            break

    print("First image is: " + input_data[0])
    print("Number of frames found: ", len(input_data))
    return input_data


def get_frame_limit(limit_frames, globsize):
    """ Determines a limit on the number of frames

    Args:
        limit_frames:
        globsize:

    Returns:
        int: total frames to run TMF on
    """
    if limit_frames != -1:
        if globsize > limit_frames:
            total_frames = limit_frames
            print("Frames limited to ", limit_frames)
        else:
            print("Frame limit of ", limit_frames, "is higher than total # of frames: ", globsize)
            total_frames = globsize
    else:
        total_frames = globsize

    return total_frames


def make_output_dir(output_dir):
    """ Creates uniquely-named new folder along specified path

    Args:
        output_dir: output path

    Returns:
        str: path to new folder
    """
    if not output_dir.endswith("/"):
        output_dir += "/"

    output_path = output_dir

    # **************************** make a new directory to write new image sequence ************************
    slitscan_current = 0
    while os.path.exists(output_path + "tmf" + str(slitscan_current) + "/"):
        slitscan_current += 1

    os.mkdir(output_path + "tmf" + str(slitscan_current) + "/")
    frame_path = output_path + "tmf" + str(slitscan_current) + "/"
    print("Made directory: ", frame_path)
    return frame_path


def do_sizing(input_data):
    if isinstance(input_data, list):
        first = Image.open(input_data[0])
        width, height = first.size
        print("width is: ", width, " height is: ", height)
    else:
        return input_data.get_meta_data()['size']
    return width, height


# handy code by Vladimir Ignatyev, found here: https://gist.github.com/vladignatyev/06860ec2040cb497f0f3
def progress(count, total, suffix=''):
    """ Creates and displays a progress bar in console log.

    Args:
        count: parts completed
        total: parts to complete
        suffix: any additional descriptors
    """
    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '=' * filled_len + '-' * (bar_len - filled_len)

    sys.stdout.write('[%s] %s%s ...%s\r' % (bar, percents, '%', suffix))
    sys.stdout.flush()


def temporal_median_filter_multi2(input_data, output_dir, limit_frames, output_format, frame_offset=8, simultaneous_frames=8):
    """
    Uses multiprocessing to efficiently calculate a temporal median filter across set of input images.

    DIAGRAM:
    f.o = offset (you actually get 2x what you ask for)
    s.o = simultaneous offset (cuz we do multiple frames at the SAME TIME)
    randframes = we make some random frames for before/after so that we don't run out of frames to use

                   |_____________________total frames______________________|
    randframes_----0      |--f.o----|s.o|---f.o---|


    Args:
        input_data: globbed input directory
        output_dir: path to output
        limit_frames: put a limit on the number of frames
        output_format: select PNG, TIFF, or JPEG (default)
        frame_offset: Number of frames to use for median calculation
        simultaneous_frames: Number of frames to process simultaneously
    Returns:
        str: path to final frames
    """
    start2 = timer()
    frame_path = make_output_dir(output_dir)
    width, height = do_sizing(input_data)
    total_frames = get_frame_limit(limit_frames, get_number_of_frames(input_data))

    median_array = numpy.zeros((frame_offset+simultaneous_frames+frame_offset, height, width, 3),numpy.uint8)

    for frame in range(frame_offset):
        median_array[frame, :, :, :] = numpy.random.randint(low=0, high=255, size=(height, width, 3))

    # read all the frames into big ol' array
    for frame_number in range(simultaneous_frames+frame_offset):
        next_im = get_frame_data(input_data, frame_number)
        next_array = numpy.array(next_im, numpy.uint8)
        del next_im
        median_array[frame_offset+frame_number, :, :, :] = next_array
        del next_array

    #                |_____________________total frames______________________|
    # randframes_----0      |--f.o----|s.o|---f.o---|
    # whole_array = numpy.zeros((total_frames, height, width, 3), numpy.uint8)

    p = Pool(processes=8)
    current_frame = 0
    filtered_array = numpy.zeros((simultaneous_frames, height, width, 3), numpy.uint8)

    while current_frame < total_frames:
        if current_frame == 0:
            pass
        else:
            median_array = numpy.roll(median_array, -simultaneous_frames, axis=0)
            for x in range(simultaneous_frames):
                if (current_frame+frame_offset+x) > total_frames:
                    next_array = numpy.random.randint(low=0, high=255, size=(height, width, 3))
                else:
                    next_im = get_frame_data(input_data, frame_offset+current_frame+x)
                    next_array = numpy.array(next_im, numpy.uint8)
                median_array[frame_offset+frame_offset+x, :, :, :] = next_array

        slice_list = []
        for x in range(simultaneous_frames):
            if (x+current_frame) > total_frames:
                break
            else:
                slice_list.append(median_array[x:(x+frame_offset+frame_offset)])

        # calculate medians in our multiprocessing pool
        results = p.map(median_calc, slice_list)

        for frame in range(len(results)):
            filtered_array[frame, :, :, 0] = results[frame][0]
            filtered_array[frame, :, :, 1] = results[frame][1]
            filtered_array[frame, :, :, 2] = results[frame][2]
            img = Image.fromarray(filtered_array[frame, :, :, :])
            frame_name = frame_path + str(current_frame+frame) + "." + output_format
            img.save(frame_name, format=output_format)
        progress(current_frame, total_frames)
        current_frame += simultaneous_frames

    end2 = timer()
    print("\nTotal Time was: %.02f sec. %.02f sec per frame." % (end2-start2, ((end2-start2)/total_frames)))
    return frame_path


def median_calc(median_array):
    return numpy.median(median_array[:, :, :, 0], axis=0), \
           numpy.median(median_array[:, :, :, 1], axis=0), \
           numpy.median(median_array[:, :, :, 2], axis=0)


def make_a_video(output_dir, output_format, name):
    """ Use ffmpeg to make a video out of our cool frames
    
    Args:
        output_dir (str): 
        output_format (str): 
        name (str): 

    Returns:
        None
    """
    if not output_dir.endswith("/"):
        output_dir += "/"
    os.system('ffmpeg -r 24 -i ' + output_dir + '%d.' + output_format + ' -c:v libx264 ' + output_dir + name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser._optionals.title = 'arguments'

    parser.add_argument("-i", "--input_dir",
                        help="Input directory. Set of frames or a single video. Tests for frames first.", required=True)
    parser.add_argument("-o", "--output_dir", default=os.getcwd(),
                        help="Path for output frames (optional) Default: Subdir of input)")
    parser.add_argument("-offset", "--frame_offset", default=8, type=int,
                        help="Number of Frames to use for TMF (optional)")
    parser.add_argument("-l", "--frame_limit", default=-1, type=int,
                        help="Limit number of frames to specified int (optional)")
    parser.add_argument("-format", "--output_format", default="JPEG", help="Output image format. (optional)")
    parser.add_argument("-simul", "--simultaneous_frames",type=int, default="8",
                        help="Number of frames to process on each iteration (faster performance using more cores)")
    parser.add_argument("-v", "--video", action="store_true", default=False, dest="video",
                        help="Optional: Encode h.264 video of resulting frames. Defaults to False.")

    args = parser.parse_args()
    output_path = temporal_median_filter_multi2(
        make_a_glob(args.input_dir),
        args.output_dir,
        args.frame_limit,
        args.output_format,
        args.frame_offset,
        args.simultaneous_frames
    )

    if args.video:
        make_a_video(output_path, args.output_format, "TMF.mp4")
