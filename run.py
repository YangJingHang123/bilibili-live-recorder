from Live import BiliBiliLive
import os
import subprocess
import sys
import requests
import time
import config
import utils
import multiprocessing
from update import update

NOT_START = 0
RECORDING = 1


class NotcallableError(Exception):
    pass


class BiliBiliLiveRecorder(BiliBiliLive):
    def __init__(self, room_id, check_interval=30, on_stop=None):
        super().__init__(room_id)
        self.print = utils.print_log
        self.next_status = utils.next_status
        self.check_interval = check_interval
        self.on_stop = on_stop

    def check(self, interval, blocking=True):
        try:
            room_info = self.get_room_info()
            print(room_info)
            if room_info['status']:
                self.print(self.room_id, room_info['roomname'])
                return self.get_live_urls()
            else:
                if not blocking:
                    return None  # need refactor
        except Exception as e:
            self.print(self.room_id, 'Error:' + str(e))

    def record(self, record_url, output_filename):
        try:
            self.print(self.room_id, '√ 正在录制...')
            headers = dict()
            headers['Accept-Encoding'] = 'identity'
            headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko'
            resp = requests.get(record_url, stream=True, headers=headers)
            with open(output_filename, "ab+") as f:
                for chunk in resp.iter_content(chunk_size=1024):
                    f.write(chunk) if chunk else None
                    f.flush()
        except Exception as e:
            self.print(self.room_id, 'Error while recording:' + str(e))

    def run(self):
        status = NOT_START
        c_filename = None
        while True:
            try:
                urls = self.check(interval=self.check_interval, blocking=False)

                if urls is None and status == NOT_START:  # just wait
                    self.print(self.room_id, '等待开播')
                    time.sleep(self.check_interval)

                if urls and status == NOT_START:  # start recording
                    status = self.next_status(status, True)
                    filename = utils.generate_filename(self.room_id)
                    c_filename = os.path.join(os.getcwd(), 'files', filename)
                    self.print(self.room_id, '开始录制' + c_filename)
                    self.record(urls[0], c_filename)

                if urls and status == RECORDING:  # recording
                    self.record(urls[0], c_filename)

                if urls is None and status == RECORDING:  # stream end
                    self.print(self.room_id, '录制完成' + c_filename)
                    status = self.next_status(status, True)
                    subprocess.run(
                        'ffmpeg -y -i {c_filename} -c:a copy -c:v copy {final_name}'.format(c_filename=c_filename, final_name=c_filename.split('.')[0]+'_final.mp4'),
                        shell=True,
                        stderr=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL)
                    print("ffmpeg done.")
                    try:
                        if callable(self.on_stop):
                            self.on_stop(c_filename.split('.')[
                                         0]+'_final.mp4')  # callback
                        elif self.on_stop is not None:
                            raise NotcallableError('on_stop is not callable')
                    except Exception as e:
                        self.print(
                            self.room_id, 'Error while calling on_stop callback' + str(e))

            except Exception as e:
                self.print(
                    self.room_id, 'Error while checking or recording:' + str(e))
                status = self.next_status(status, False)


if __name__ == '__main__':
    print(sys.argv)
    if len(sys.argv) == 2:
        input_id = [str(sys.argv[1])]
    elif len(sys.argv) == 1:
        input_id = config.rooms
    else:
        raise ValueError('请检查输入的命令是否正确 例如：python3 run.py 10086')

    file_path = os.path.join(os.getcwd(), 'files')
    if not os.path.exists(file_path):
        os.mkdir(file_path)

    mp = multiprocessing.Process
    tasks = [mp(target=BiliBiliLiveRecorder(room_id, on_stop=update).run)
             for room_id in input_id]
    for i in tasks:
        i.start()
    for i in tasks:
        i.join()
