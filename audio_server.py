import pyaudio
import numpy as np
import time
import configparser
import requests
import os
import multiprocessing as mp
from multiprocessing.connection import Listener
from scipy import ndimage, interpolate
from datetime import datetime


class AudioServer:

    # configuration
    CHUNK_SIZE = 8192*4
    AUDIO_FORMAT = pyaudio.paInt16
    SAMPLE_RATE = 48000
    BUFFER_HOURS = 12
    AUDIO_SERVER_ADDRESS = ('localhost', 6000)
    PUSH_TIME_LIMIT = 50

    def __init__(self):
        self.audio_device = ''
        self.lock = mp.Lock()
        self.shared_audio = np.array([])
        self.shared_time = np.array([])
        self.shared_pos = 0
        self.pj_secret = ''
        self.ifttt_url = ''
        self.notification_link = ''
        self.notification_activationfile = '/tmp/enable_baby_notifications'
        self.was_quiet = True
        self.last_time_pushed = time.time()

    def getIndexForDevice(audio_device_name):
        """ get the index of a recording device with name audio_device_name """

        # open default audio input stream
        p = pyaudio.PyAudio()

        dev_index=-1
        dev_cnt = p.get_device_count()
        print('There are {} audio devices available.'.format(dev_cnt))
        for i in range(0,dev_cnt):
            # print the one which have maxInputChannels larger than 0
            info=p.get_device_info_by_index(i)
            if info['maxInputChannels'] >0:
                dev_name = info['name']
                sample_rate = info['defaultSampleRate']
                print('Index {}: {}, {}'.format(i, dev_name, sample_rate))
                if str(dev_name) == str(audio_device_name):
                    dev_index = i
                    print('Index {} selected as input.'.format(i))

        return dev_index;

    def callback(self, in_data,frame_count, time_info, status):
        """ callback function to stream audio, another thread. """

        callback_buffer = np.fromstring(in_data,dtype=np.int16)
        current_time = time.time()

        max_value = np.abs(callback_buffer).max()

        # acquire lock
        self.lock.acquire()

        # record current time
        self.shared_time[self.shared_pos] = current_time

            # record the maximum volume in this time slice
        self.shared_audio[self.shared_pos] = max_value
    #        if self.shared_pos %8 == 0:
    #            print('maxVal: {}'.format(np.max(audio)))

        # increment counter
        self.shared_pos = (self.shared_pos + 1) % len(self.shared_time)

        # release lock
        self.lock.release()
        return (callback_buffer, pyaudio.paContinue)



    def format_time_difference(time1, time2):
        time_diff = datetime.fromtimestamp(time2) - datetime.fromtimestamp(time1)

        return str(time_diff).split('.')[0]


    def process_requests(self):
        """ Handle requests from the web server. First get the latest data, and
         then analyse it to find the current noise state """

        listener = Listener(AudioServer.AUDIO_SERVER_ADDRESS)
        while True:
            conn = listener.accept()

            # get some parameters from the client
            parameters = conn.recv()

            # acquire lock
            self.lock.acquire()

            # convert to numpy arrays and get a copy of the data
            time_stamps = self.shared_time.copy()
            audio_signal = self.shared_audio.astype(np.float32)
            current_pos = self.shared_pos

            # release lock
            self.lock.release()

            # roll the arrays so that the latest readings are at the end
            buffer_len = time_stamps.shape[0]
            time_stamps = np.roll(time_stamps, shift=buffer_len-current_pos)
            audio_signal = np.roll(audio_signal, shift=buffer_len-current_pos)

            # normalise volume level
            audio_signal /= parameters['upper_limit']

            # apply some smoothing
            sigma = 4 * (AudioServer.SAMPLE_RATE / float(AudioServer.CHUNK_SIZE))
            audio_signal = ndimage.gaussian_filter1d(audio_signal, sigma=sigma, mode="reflect")

            # get the last hour of data for the plot and re-sample to 1 value per second
            hour_chunks = int(60 * 60 * (AudioServer.SAMPLE_RATE / float(AudioServer.CHUNK_SIZE)))
            xs = np.arange(hour_chunks)
            f = interpolate.interp1d(xs, audio_signal[-hour_chunks:])
            audio_plot = f(np.linspace(start=0, stop=xs[-1], num=3600))

            # ignore positions with no readings
            mask = time_stamps > 0
            time_stamps = time_stamps[mask]
            audio_signal = audio_signal[mask]

            # partition the audio history into blocks of type:
            #   1. noise, where the volume is greater than noise_threshold
            #   2. silence, where the volume is less than noise_threshold
            noise = audio_signal > parameters['noise_threshold']
            silent = audio_signal < parameters['noise_threshold']

            # join "noise blocks" that are closer together than min_quiet_time
            crying_blocks = []
            if np.any(noise):
                silent_labels, _ = ndimage.label(silent)
                silent_ranges = ndimage.find_objects(silent_labels)
                for silent_block in silent_ranges:
                    start = silent_block[0].start
                    stop = silent_block[0].stop

                    # don't join silence blocks at the beginning or end
                    if start == 0:
                        continue

                    interval_length = time_stamps[stop-1] - time_stamps[start]
                    if interval_length < parameters['min_quiet_time']:
                        noise[start:stop] = True

                # find noise blocks start times and duration
                crying_labels, num_crying_blocks = ndimage.label(noise)
                crying_ranges = ndimage.find_objects(crying_labels)
                for cry in crying_ranges:
                    start = time_stamps[cry[0].start]
                    stop = time_stamps[cry[0].stop-1]
                    duration = stop - start

                    # ignore isolated noises (i.e. with a duration less than min_noise_time)
                    if duration < parameters['min_noise_time']:
                        continue

                    # save some info about the noise block
                    crying_blocks.append({'start': start,
                                          'start_str': datetime.fromtimestamp(start).strftime("%H:%M:%S").lstrip('0'),
                                          'stop': stop,
                                          'duration': AudioServer.format_time_difference(start, stop)})

            # determine how long have we been in the current state
            time_current = time.time()
            time_crying = ""
            time_quiet = ""
            str_crying = "Baby noise for "
            str_quiet = "Baby quiet for "
            if len(crying_blocks) == 0:
                try:
                    time_quiet = str_quiet + AudioServer.format_time_difference(time_stamps[0], time_current)
                except IndexError as e:
                    print("Index error t={}, ts={}: {}".format(time_current,time_stamps[0],e))
                    return
            else:
                if time_current - crying_blocks[-1]['stop'] < parameters['min_quiet_time']:
                    time_crying = str_crying + AudioServer.format_time_difference(crying_blocks[-1]['start'], time_current)
                    self.babyNoiseDetected()
                else:
                    time_quiet = str_quiet + AudioServer.format_time_difference(crying_blocks[-1]['stop'], time_current)

                    self.babyQuietDetected()

            # return results to webserver
            results = {'audio_plot': audio_plot,
                       'crying_blocks': crying_blocks,
                       'time_crying': time_crying,
                       'time_quiet': time_quiet}
            conn.send(results)
            conn.close()

    def run_server(self):
        """ initialize audio server and provide audio samples to a webserver """

        dev_index = AudioServer.getIndexForDevice(self.audio_device)
        if dev_index==-1:
            print("No Device named {} found.".format(self.audio_device))
            exit(1)

        # figure out how big the buffer needs t o be to contain BUFFER_HOURS of audio
        buffer_len = int(AudioServer.BUFFER_HOURS * 60 * 60 * (AudioServer.SAMPLE_RATE / float(AudioServer.CHUNK_SIZE)))

        # create shared memory
        self.lock = mp.Lock()
        self.shared_audio = np.zeros((buffer_len,), dtype=np.int16)
        self.shared_time = np.zeros((buffer_len,), dtype=np.float64)
        self.shared_pos = 0

        # open default audio input stream
        p = pyaudio.PyAudio()

        stream = p.open(format=AudioServer.AUDIO_FORMAT, channels=1, rate=AudioServer.SAMPLE_RATE, input=True, frames_per_buffer=AudioServer.CHUNK_SIZE,
                    input_device_index=dev_index, stream_callback=self.callback)

        self.pushMessage("Babyphone started!")
        try:
            self.process_requests()
        except KeyboardInterrupt:
            print('Exiting...')

        # Unload audiostream and pyaudio
        stream.stop_stream()
        stream.close()
        p.terminate()
        self.pushMessage("Babyphone stopped!")
        exit(0)

    def babyNoiseDetected(self):
        """ Function to ensure that it was quied before sending a notification and limits the number of notifications per time"""
        if self.was_quiet == True and (time.time() - self.last_time_pushed) > AudioServer.PUSH_TIME_LIMIT and os.path.isfile(self.notification_activationfile):
            self.last_time_pushed = time.time()
            self.was_quiet = False
            self.pushMessage("Baby is crying.")

    def babyQuietDetected(self):
        self.was_quiet = True

    def pushMessage(self,message):
        if len(self.pj_secret) == 12:
            print("send notification through pushjet.")
            self.pushMessageViaPushjet(message)

        if len(self.ifttt_url) > 60:
            print("send notification through ifttt.")
            self.pushMessageViaIFTTT(message)
        


    def pushMessageViaPushjet(self,message):
        data = {
            "secret": str(self.pj_secret),
            "message": str(message),
            "title": "Baby Phone",
            "level": 1,
            "link": str(self.notification_link)
        }

        r = requests.post('https://api.pushjet.io/message', data=data)

        if r.status_code == requests.codes.ok:
            print("successfuly sent notification!")
        else:
            print("couldn't send notification!")
            print("code:"+ str(r.status_code))
            print("headers:"+ str(r.headers))
            print("content:"+ str(r.text))

    def pushMessageViaIFTTT(self,message):
        data = {
            "value1": str(message),
            "value2": ":-)",
            "value3": str(self.notification_link)
        }

        r = requests.post(self.ifttt_url, data=data)

        if r.status_code == requests.codes.ok:
            print("successfuly sent notification!")
        else:
            print("couldn't send notification!")
            print("code:"+ str(r.status_code))
            print("headers:"+ str(r.headers))
            print("content:"+ str(r.text))

    def getConfiguration(self):
        """ Read configuration parameters from config file """
        config = configparser.ConfigParser()
        config.read('babyphone.ini')

        noti = config['notification']
        self.pj_secret = noti['pushjet_secret']
        self.ifttt_url = noti['ifttt_url']
        self.notification_link = noti['link']

        ac = config['audio']
        self.audio_device = ac['device']


if __name__ == '__main__':
    audio_srv = AudioServer()
    audio_srv.getConfiguration()
    audio_srv.run_server()
