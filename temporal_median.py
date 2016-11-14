import numpy, os, glob
import sys
from PIL import Image
from timeit import default_timer as timer
from multiprocessing import Process, Pool
import argparse


def make_a_glob(root_dir):
    """
    Creates a glob of images from specified path. Checks for JPEG, PNG, TIFF, DNG
    :param root_dir: path to set of images
    :return: glob of images from input path
    """
    if not os.path.exists(root_dir):
        raise IOError("No such path: %s" % root_dir)

    if not root_dir.endswith("/"):
        root_dir += "/"

    dir_glob = glob.glob(root_dir + "*.tif")
    extension_list = ["*.tiff", "*.tif", "*.jpeg", "*.png", "*.jpg", "*.dng"]

    for ext in extension_list:
        if len(dir_glob) == 0:
            dir_glob = glob.glob(root_dir + ext)
            if len(dir_glob) == 0:
                dir_glob = glob.glob(root_dir + ext.upper())
            if ext == extension_list[(len(extension_list)-1)] and len(dir_glob) == 0:
                raise IOError("No images found in directory: %s" % root_dir)
        else:
            break

    print "First image is: " + dir_glob[0]
    print "Number of frames found: ", len(dir_glob)
    return dir_glob


def get_frame_limit(limit_frames, globsize):
    """
    Determines a limit on the number of frames
    :param limit_frames:
    :param globsize:
    :return:
    """
    if limit_frames != -1:
        if globsize > limit_frames:
            total_frames = limit_frames
            print "Frames limited to ", limit_frames
        else:
            print "Frame limit of ", limit_frames, "is higher than total # of frames: ", globsize
            total_frames = globsize
    else:
        total_frames = globsize

    return total_frames


def make_output_dir(output_dir):
    """
    Creates uniquely-named new folder along specified path
    :param output_dir: output path
    :return: path to new folder
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
    print "Made directory: ", frame_path
    return frame_path


def do_sizing(dir_glob):
    first = Image.open(dir_glob[0])
    width, height = first.size
    print "width is: ", width," height is: ", height
    return width, height


# handy code by Vladimir Ignatyev, found here: https://gist.github.com/vladignatyev/06860ec2040cb497f0f3
def progress(count, total, suffix=''):
    """
    Creates and displays a progress bar in console log.
    :param count: parts completed
    :param total: parts to complete
    :param suffix: any additional descriptors
    :return:
    """
    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '=' * filled_len + '-' * (bar_len - filled_len)

    sys.stdout.write('[%s] %s%s ...%s\r' % (bar, percents, '%', suffix))
    sys.stdout.flush()


def temporal_median_filter(dir_glob, output_dir, limit_frames, output_format):
    frame_path = make_output_dir(output_dir)
    width, height = do_sizing(dir_glob)
    total_frames = get_frame_limit(limit_frames, len(dir_glob))

    print "\n"

    # for each iteration:
    #   delete oldest frame.
    #   add new frame
    #   do median calculations
    #   write to filtered_array, save result.

    frame_offset = 8
    whole_array = numpy.zeros((frame_offset+frame_offset+1, height, width, 3), numpy.uint8)

    for frame_number in xrange(frame_offset+frame_offset+1):
        next_im = Image.open(dir_glob[frame_number])
        next_array = numpy.array(next_im, numpy.uint8)
        del next_im
        whole_array[frame_number, :, :, :] = next_array
        del next_array
        progress(frame_number, total_frames)

    median_array = whole_array[0:frame_offset+frame_offset+1, :, :, :]

    for frame_number in range(total_frames):
        start = timer()
        if frame_number == 0:
            pass
        elif (frame_number + frame_offset) >= total_frames:
            median_array = median_array[1:,:,:,:]
        else:
            next_im = Image.open(dir_glob[frame_offset+frame_offset+frame_number])
            next_array = numpy.array(next_im, numpy.uint8)
            median_array = numpy.roll(median_array, -1, axis=0)
            median_array[frame_offset+frame_offset, :, :, :] = next_array

        # low = frame_number - frame_offset
        # high = frame_number + frame_offset
        # if frame_number-frame_offset <= 0:
        #     low = 0
        # if frame_number+frame_offset+frame_offset >= total_frames:
        #     high = total_frames
        #
        # print low, high
        filtered_array = numpy.zeros((height, width, 3), numpy.uint8)

        start2 = timer()
        filtered_array[:, :, 0] = numpy.median(median_array[:,:,:,0], axis=0)
        filtered_array[:, :, 1] = numpy.median(median_array[:,:,:,1], axis=0)
        filtered_array[:, :, 2] = numpy.median(median_array[:,:,:,2], axis=0)
        end2 = timer()
        print "Median array calc: %s" % (end2-start2)

        img = Image.fromarray(filtered_array)
        frame_name = frame_path + str(frame_number) + "." + output_format
        img.save(frame_name, format=output_format)
        progress(frame_number, total_frames)
        end = timer()
        print "Time required: %s seconds" % (end-start)


def temporal_median_filter_multi2(dir_glob, output_dir, limit_frames, output_format, frame_offset=8, simultaneous_frames=8):
    """
    Uses multiprocessing to efficiently calculate a temporal median filter across set of input images.

    DIAGRAM:
    f.o = offset (you actually get 2x what you ask for)
    s.o = simultaneous offset (cuz we do multiple frames at the SAME TIME)
    randframes = we make some random frames for before/after so that we don't run out of frames to use

                   |_____________________total frames______________________|
    randframes_----0      |--f.o----|s.o|---f.o---|


    :param dir_glob: globbed input directory
    :param output_dir: path to output
    :param limit_frames: put a limit on the number of frames
    :param output_format: select PNG, TIFF, or JPEG (default)
    :param frame_offset: Number of frames to use for median calculation
    :param simultaneous_frames: Number of frames to process simultaneously
    :return:
    """
    start2 = timer()
    frame_path = make_output_dir(output_dir)
    width, height = do_sizing(dir_glob)
    total_frames = get_frame_limit(limit_frames, len(dir_glob))

    median_array = numpy.zeros((frame_offset+simultaneous_frames+frame_offset, height, width, 3),numpy.uint8)

    for frame in range(frame_offset):
        median_array[frame, :, :, :] = numpy.random.randint(low=0, high=255, size=(height, width, 3))

    # read all the frames into big ol' array
    for frame_number in xrange(simultaneous_frames+frame_offset):
        next_im = Image.open(dir_glob[frame_number])
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
                    next_im = Image.open(dir_glob[frame_offset+current_frame+x])
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
    print "\nTotal Time was: %.02f sec. %.02f sec per frame." % (end2-start2, ((end2-start2)/total_frames))


def median_calc(median_array):
    return numpy.median(median_array[:,:,:,0], axis=0), numpy.median(median_array[:,:,:,1], axis=0), numpy.median(median_array[:,:,:,2], axis=0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser._optionals.title = 'arguments'

    parser.add_argument("-i", "--input_dir",
                        help="Input directory. Set of frames or a single video. Tests for frames first.", required=True)
    parser.add_argument("-o", "--output_dir", default="None",
                        help="Path for output frames (optional) Default: Subdir of input)")
    parser.add_argument("-offset", "--frame_offset", default=8, type=int, help="Number of Frames to use for TMF (optional)")
    parser.add_argument("-l", "--frame_limit", default=-1, type=int,
                        help="Limit number of frames to specified int (optional)")
    parser.add_argument("-format", "--output_format", default="JPEG", help="Output image format. (optional)")
    parser.add_argument("-simul", "--simultaneous_frames",type=int, default="8",
                        help="Number of frames to process on each iteration (faster performance using more cores)")

    args = parser.parse_args()
    temporal_median_filter_multi2(make_a_glob(args.input_dir), args.output_dir, args.frame_limit, args.output_format, args.frame_offset, args.simultaneous_frames)