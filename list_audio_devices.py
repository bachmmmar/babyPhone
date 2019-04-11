#!/usr/bin/python3
import pyaudio


if __name__ == '__main__':
    p = pyaudio.PyAudio()

    input_dev_cnt=0
    dev_cnt = p.get_device_count()
    print('There are {} audio devices.'.format(dev_cnt))
    for i in range(0,dev_cnt):
        # print the one which have maxInputChannels larger than 0
        info=p.get_device_info_by_index(i)
        if info['maxInputChannels'] >0:
            input_dev_cnt=input_dev_cnt+1
            print('    Name "{}"'.format(info['name']))
    print('and {} are input devices.'.format(input_dev_cnt))
