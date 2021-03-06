import re,os,time
from ffmpy import FFmpeg
from shutil import rmtree
import requests
import base64,json
from Crypto.Cipher import AES
from queue import Queue
from threading import Thread
from argparse import ArgumentParser
###############
# 初始化
q = Queue(10000)
headers = {
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36 Edg/91.0.864.59'
}

downsize = 0
Missions_completed = 0
preallsize = 0
time_start = time.time()

######################

class m3u8infos:
    def __init__(self):
        pass

    def getkey(self,method):
        if self.key != '':
            return self.key
        keyurl = re.findall('URI="(.+?)"',self.m3u8text)[0]

        # 本地设置的b64key
        if 'base64:' in keyurl:
            b64key = re.findall('base64:(.+)',keyurl)[0]
            return b64key

        requests.packages.urllib3.disable_warnings()
        key = requests.get(url=keyurl,headers=headers,verify=False).content
        b64key = base64.b64encode(key).decode()
        if method == 'AES-128':
            return b64key

    def getiv(self,method):
        if self.iv != '':
            return self.iv
        if method == 'AES-128':
            iv = b'0000000000000000'
            b64iv = base64.b64encode(iv).decode()
            return b64iv

    def check_title(self,title):
        title = re.sub(r"\\/:*?\"<>|:\(\) ", "", title)[-64:]
        if os.path.exists(f'{self.workDir}/{title}.mp4'):
            title += '(1)'
            title = self.check_title(title)
        return title

    def start(self,m3u8,workDir,name,key,iv,m3u8BaseUrl,enableDel,showLogs):
        # http://****.m3u8
        if ':\\' not in m3u8:
            if name == '':
                self.title = m3u8.split('?')[0].split('/')[-1].replace('.m3u8', '')
            else:
                self.title = name
            requests.packages.urllib3.disable_warnings()
            self.m3u8text = requests.get(url=m3u8, headers=headers, verify=False).text
            self.m3u8BaseUrl = '/'.join(m3u8.split('?')[0].split('/')[:-1]) + '/'
        # C:\Users\happy\Downloads\v.f230 (1).m3u8
        else:
            if name == '':
                self.title = m3u8.split('\\')[-1].replace('.m3u8', '')
            else:
                self.title = name
            # \ / : * ？ " < > |
            with open(f'{m3u8}', 'r') as f:
                self.m3u8text = f.read()
            self.m3u8BaseUrl = m3u8BaseUrl
        self.workDir = workDir
        self.title = self.check_title(self.title)
        self.title = self.title.replace(':','').replace(' ','')
        if os.path.exists(self.workDir) == False:
            os.makedirs(self.workDir)

        if os.path.exists(f'{self.workDir}/{self.title}') == False:
            print(f'{self.workDir}/{self.title}')
            os.makedirs(f'{self.workDir}/{self.title}')

            os.makedirs(f'{self.workDir+"/"+self.title}/Part_0')
        self.tsurls = re.findall('#EXTINF.+\n(.+?)\n', self.m3u8text)
        self.count = len(self.tsurls)

        # 判读是否加密及加密类型
        if 'METHOD=' in self.m3u8text:
            self.method = re.findall('METHOD=(.+?),', self.m3u8text)[0]
            self.key = key
            self.iv = iv
            if self.method == 'AES-128':
                self.key = self.getkey(self.method)
                self.iv = self.getiv(self.method)
            elif self.method == 'SAMPLE-AES-CTR':
                print('不支持 SAMPLE-AES-CTR 解密，下载完后自动二进制合并')
                self.key = ''
                self.iv = ''
        else:
            self.method = ''
            self.key = ''
            self.iv = ''

        segments = []
        for i in range(len(self.tsurls)):
            segment = {
                'title':self.title,
                "index": i,
                "method": self.method,
                "key": self.key,
                "iv": self.iv,
                "segUrl": f'{self.m3u8BaseUrl}{self.tsurls[i]}' if 'http' not in self.tsurls[i] else f'{self.tsurls[i]}'
            }
            segments.append(segment)
        self.meta = {
            'title': self.title,
            'm3u8': m3u8,
            'm3u8BaseUrl': self.m3u8BaseUrl,
            'enableDel':enableDel,
            'showLogs':showLogs,
            'm3u8Info': {
                'count': self.count,
                'segments': segments
            }
        }
        print(f'{self.title} Download Start.')
        with open(f'{self.workDir}/{self.title}/meta.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(self.meta, indent=4))
        return self.meta

class Consumer(Thread):
    def __init__(self,title,workDir,count,retries,enableDel,showLogs):
        Thread.__init__(self)
        self.title = title
        self.workDir = workDir
        self.count = count
        self.retries = retries
        self.enableDel = enableDel
        self.showLogs = showLogs

    def run(self):
        while True:
            # 检查队列中是否还有链接
            if q.qsize() == 0:
                break
            self.ts_download(q.get())

    def ts_download(self, segment):
        global downsize
        global Missions_completed
        global preallsize

        # 下载
        index = str(segment['index']).zfill(6)
        for i in range(self.retries):
            try:
                requests.packages.urllib3.disable_warnings()
                response = requests.get(url=segment['segUrl'], headers=headers, timeout=5,stream=True,verify=False)
                ts = response.content
                if response.status_code == 200:
                    break
            except:
                if self.showLogs:
                    print(f'\r\t{index}.ts requests failed {i + 1} times.')
                time.sleep(1)
                if i == self.retries-1:
                    ts = b''
        if segment['method'] == 'AES-128':
            key = base64.b64decode(segment['key'])
            if len(key) != 16:
                print('The key is wrong!')
            iv = base64.b64decode(segment['iv'])

            cryptor = AES.new(key=key, mode=AES.MODE_CBC,iv=iv)

            ts = cryptor.decrypt(ts)

        with open(f'{self.workDir}/{self.title}/Part_0/{index}.ts', 'wb') as f:
            f.write(ts)

        # 进度条
        downsize += ts.__sizeof__()
        Missions_completed += 1
        preallsize = downsize * self.count / Missions_completed

        if Missions_completed == self.count:
            # arg = 'copyb' if segment['method'] == 'SAMPLE-AES-CTR' else 'normal'
            self.combine()

    def combine(self):
        """
        二进制合并视频
        转码
        """
        # print('\t视频合并中……',end='')
        filelist = [fr"{self.workDir}/{self.title}/Part_0/{str(i).zfill(6)}.ts" for i in range(self.count)]

        for ts_po in filelist:
            with open(fr"{self.workDir}/{self.title}/{self.title}.ts", 'ab') as f:
                with open(ts_po, 'rb') as t:
                    f.write(t.read())
        # 检查合并是否完成
        if os.path.exists(fr"{self.workDir}/{self.title}/{self.title}.ts") == True:
            # print('\t合并完成！', end='')
            # print('\t视频转码……', end='')
            self.ffmpeg(input_path=fr'{self.workDir}/{self.title}/{self.title}.ts',
                        output_path=fr'{self.workDir}/{self.title}.mp4')
            # print('\t转码成功！', end='')

        if self.enableDel == True:
            self.del_after_done()

    def ffmpeg(self,input_path,output_path):
        ff = FFmpeg(inputs={input_path: None}, outputs={output_path: '-c copy -loglevel panic'})
        ff.run()

    def del_after_done(self):
        rmtree(rf'{self.workDir}\{self.title}', ignore_errors=True)
        # if os.path.exists(rf'{os.path.abspath("")}\{self.title}') == False:
            # print('\t删除分片成功！')

def process_bar(title,count):
    global Missions_completed,preallsize,downsize
    while Missions_completed <= count:
        end = time.time()
        speed = downsize / (end - time_start)
        if speed == 0.0:
            speed = 0.1
        ETA = (preallsize - downsize) / speed
        m, s = divmod(int(ETA), 60)
        ETA = f'{m} m {s} s'
        number = int(round(Missions_completed / count * 100, 2) / 2)
        mat = "{:70}{:8}{:20}{:10}{:10}"
        print(mat.format(
            f"\r{'#' * number+'-'*(50-number)} {str(round(Missions_completed / count * 100, 2))+'%'}",
            f"[{Missions_completed}/{count}]",
            f"[{round(downsize / 1024 / 1024, 2)}Mb/{round(preallsize / 1024 / 1024, 2)}Mb]",
            f"{round(speed / 1024 / 1024, 2)}Mb/s",
            f"{ETA}"),
            end='')

        if Missions_completed == count:
            break
        time.sleep(0.5)


def run(m3u8,workDir='./',name='',b64key='',b64iv='',enableDel=True,m3u8BaseUrl='',showLogs=False,Threads=16,retries=16):
    meta = m3u8infos().start(m3u8,workDir,name, b64key, b64iv, m3u8BaseUrl, enableDel,showLogs)

    title = meta['title']
    count = meta['m3u8Info']['count']

    segments = meta['m3u8Info']['segments']
    for segment in segments:
        q.put(segment)
    for i in range(Threads):
        t = Consumer(title,workDir,count,retries,enableDel,showLogs)
        t.start()
    # 进度条线程
    t = Thread(target=process_bar, args=[title,count])
    t.start()
    while t.is_alive():
        time.sleep(2)
    print('\n')

if __name__ == '__main__':
    parser = ArgumentParser(
        prog="https://github.com/Nchujx/m3u8down",
        description=("M3U8 streaming video download script,this is python version.")
    )
    parser.add_argument("-m3u8", help="视频地址：网络链接或本地文件链接")
    parser.add_argument("-name", default='', help="视频名称")
    parser.add_argument("-workDir",default='./')
    parser.add_argument("-b64key", default='', help="自定义key:base64编码")
    parser.add_argument("-b64iv", default='', help="自定义iv:base64编码")
    parser.add_argument("-enableDel", default=True, help="下载完后删除多余文件", type=bool)
    parser.add_argument("-m3u8BaseUrl", default='', help="链接前缀:用于补全链接")
    parser.add_argument("-showLogs", default=False, help="显示错误日志")
    args = parser.parse_args()
    run(m3u8=args.m3u8, name=args.name,workDir=args.workDir,b64key=args.b64key, b64iv=args.b64iv, enableDel=args.enableDel,
        m3u8BaseUrl=args.m3u8BaseUrl, showLogs=args.showLogs)

    # m3u8 = r"https://video.gdt.ablesky.com/nod/coursecontent/2020/06/30/5ff9274c-0d2c-427c-9c3b-7084e5dbe5a6.mp4/index.m3u8?userName=GUEST&uuid=521e1723-6f36-496a-95d4-8cd1313400e5&isRec=0&st=P4c5AhVh9_XzmdPkPpJMGg&e=1626309310"
    # run(m3u8=m3u8,workDir='小班课',name='123（）', b64key='',b64iv='',enableDel=True,m3u8BaseUrl='',showLogs=False,Threads=16,retries=16)
