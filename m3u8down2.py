import re,os,time
from shutil import rmtree
import requests
import base64,json
from Crypto.Cipher import AES
from queue import Queue
from threading import Thread
import platform

system = platform.system()
q = Queue(10000)

title = ''
count = 0
enabledel = True

preallsize = 0
downsize = 0
start = time.time()
speed = 0
Missions_completed = 0

headers = {
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36 Edg/91.0.864.59'
}

pad = lambda s: s + (16 - len(s)) * b"\0"
# 获取m3u8文件基本信息
class m3u8infos:
    def __init__(self,m3u8,name,key,iv,m3u8BaseUrl,enableDel):
        global title
        global count
        global enabledel
        enabledel = enableDel

        # http://****.m3u8
        if ':\\' not in m3u8:
            if name == '':
                self.title = m3u8.split('?')[0].split('/')[-1].replace('.m3u8', '')
            else:
                self.title = name
            requests.packages.urllib3.disable_warnings()
            self.m3u8text = requests.get(url=m3u8, headers=headers,verify=False).text
            self.m3u8BaseUrl = '/'.join(m3u8.split('?')[0].split('/')[:-1]) + '/'
        # C:\Users\happy\Downloads\v.f230 (1).m3u8
        else:
            if name == '':
                self.title = m3u8.split('\\')[-1].replace('.m3u8','')
            else:
                self.title = name
        # \ / : * ？ " < > |
            with open(f'{m3u8}','r') as f:
                self.m3u8text = f.read()
            self.m3u8BaseUrl = m3u8BaseUrl
        self.title = re.sub(r"\\/:*?\"<>| ", "", self.title)[-64:]

        if os.path.exists(self.title) == False:
            os.makedirs(self.title)
        self.tsurls = re.findall('#EXTINF.+\n(.+?)\n',self.m3u8text)
        self.count = len(self.tsurls)
        title = self.title
        count = self.count
        # 判读是否加密及加密类型
        if 'METHOD=' in self.m3u8text:
            self.method = re.findall('METHOD=(.+?),',self.m3u8text)[0]
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
                "count":self.count,
                "method": self.method,
                "key": self.key,
                "iv": self.iv,
                "segUrl": f'{self.m3u8BaseUrl}{self.tsurls[i]}' if 'http' not in self.tsurls[i] else f'{self.tsurls[i]}'
            }
            segments.append(segment)
        self.meta = {
            'm3u8':m3u8,
            'm3u8BaseUrl':self.m3u8BaseUrl,
            'm3u8Info':{
                'count':self.count,
                'segments':segments
            }
        }
        print(f'{self.title} m3u8文件解析完成……')
        with open(f'{self.title}/meta.json','w',encoding='utf-8') as f:
            f.write(json.dumps(self.meta,indent=4))

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

    def putsegments(self):
        segments = self.meta['m3u8Info']['segments']
        for segment in segments:
            q.put(segment)

# 多线程 下载ts 解密
class Consumer(Thread):
    def run(self):
        while True:
            # 检查队列中是否还有链接
            if q.qsize() == 0:
                break
            self.ts_download(q.get())

    def ts_download(self, segment):
        # 声明全局变量
        global preallsize
        global downsize
        global Missions_completed
        global start
        global speed
        # 下载
        index = str(segment['index']).zfill(6)
        title = segment['title']
        count = segment['count']
        retries = 16
        for i in range(retries):
            try:
                requests.packages.urllib3.disable_warnings()
                response = requests.get(url=segment['segUrl'], headers=headers, timeout=5,stream=True,verify=False)
                ts = response.content
                if response.status_code == 200:
                    break
            except:
                print(f'\r\t{index}.ts requests failed {i} times.')
                if i == 15:
                    ts = b''

        if segment['method'] == 'AES-128':
            key = base64.b64decode(segment['key'])
            if len(key) != 16:
                print('The key is wrong!')
            iv = base64.b64decode(segment['iv'])

            cryptor = AES.new(key=key, mode=AES.MODE_CBC,iv=iv)

            ts = cryptor.decrypt(ts)
        if system == 'Linux':
            if os.path.exists(f'{title}/Part_0') == False:
                os.makedirs(f'{title}/Part_0')
            with open(f'{title}/Part_0/{index}.ts', 'wb') as f:
                f.write(ts)
        elif system == 'Windows':
            if os.path.exists(fr'{title}\Part_0') == False:
                os.makedirs(fr'{title}\Part_0')
            with open(fr'{title}\Part_0\{index}.ts', 'wb') as f:
                f.write(ts)

        # 进度条
        downsize += ts.__sizeof__()
        Missions_completed += 1
        preallsize = downsize * count / Missions_completed
        end = time.time()
        speed = downsize / (end - start)
        ETA = (preallsize - downsize) / speed
        m, s = divmod(int(ETA), 60)
        ETA = f'{m} m {s} s'
        print(f'\r\tProcess: [{Missions_completed}/{count}]',
              f'[{round(downsize / 1024 / 1024, 2)}Mb/{round(preallsize / 1024 / 1024, 2)}Mb]',
              f'Speed={round(speed / 1024 / 1024, 2)}Mb/s', f'ETA={ETA}', end='')

        if Missions_completed == count:
            # arg = 'copyb' if segment['method'] == 'SAMPLE-AES-CTR' else 'normal'
            arg = 'copyb'
            self.combine(arg)

    def combine(self,arg):
        print('\t视频合并中……',end='')
        # 合并
        if arg == 'normal':
            filelists = [fr"file '{os.path.abspath('')}\{title}\Part_0\{str(i).zfill(6)}.ts'" for i in range(count)]
            with open(fr"{os.path.abspath('')}\{title}\filelist.txt", 'w') as f:
                text = '\n'.join(filelists)
                f.write(text)
            cmd = fr"ffmpeg -f concat -safe 0 -i {os.path.abspath('')}\{title}\filelist.txt -c copy {os.path.abspath('')}\{title}.ts -loglevel panic"
            os.system(cmd)

        elif arg == 'copyb':
            if system == 'Linux':
                filelist = [fr"{os.path.abspath('')}/{title}/Part_0/{str(i).zfill(6)}.ts" for i in range(count)]
                for ts_po in filelist:
                    with open(fr"{os.path.abspath('')}/{title}/{title}.ts", 'ab') as f:
                        with open(ts_po, 'rb') as t:
                            f.write(t.read())
                # 检查合并是否完成
                if os.path.exists(fr"{os.path.abspath('')}/{title}/{title}.ts") == True:
                    print('\t合并完成！', end='')

            elif system == 'Windows':
                filelist = [fr"{os.path.abspath('')}\{title}\Part_0\{str(i).zfill(6)}.ts" for i in range(count)]
                for ts_po in filelist:
                    with open(fr"{os.path.abspath('')}\{title}\{title}.ts", 'ab') as f:
                        with open(ts_po, 'rb') as t:
                            f.write(t.read())
                # 检查合并是否完成
                if os.path.exists(fr"{os.path.abspath('')}\{title}\{title}.ts") == True:
                    print('\t合并完成！', end='')
                    # 视频转码
                    # ffmpeg -y -i II_11_3_1.ts -c:v libx264 -c:a copy -bsf:a aac_adtstoasc output.mp4
                    print('视频转码……\t',end='')
                    cmd = fr'ffmpeg -i "{os.path.abspath("")}\{title}\{title}.ts" -c copy "{os.path.abspath("")}\{title}.mp4" -loglevel panic'
                    os.system(cmd)
                    print('转码成功！')

            if enabledel == True:
                self.del_after_done()
        else:
            print('\t合并失败……\t',end='')


    def del_after_done(self):
        rmtree(rf'{os.path.abspath("")}\{title}', ignore_errors=True)
        if os.path.exists(rf'{os.path.abspath("")}\{title}') == False:
            print('删除分片成功！')

def run(m3u8,name='',b64key='',b64iv='',enableDel=False,m3u8BaseUrl=''):
    m3u8infos(m3u8, name, b64key, b64iv, m3u8BaseUrl, enableDel).putsegments()
    try:
        m3u8infos(m3u8, name, b64key, b64iv, m3u8BaseUrl, enableDel).putsegments()
    except:
        print('Error in reading file.')
    #     sys.exit(0)
    for i in range(16):
        t = Consumer()
        t.start()

if __name__ == '__main__':
    m3u8 = r'https://video-tx.huke88.com/cb3d3408vodtransgzp1256517420/4dfb4d0b5285890807377114074/voddrm.token.eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9~eyJ0eXBlIjoiRHJtVG9rZW4iLCJhcHBJZCI6MTI1NjUxNzQyMCwiZmlsZUlkIjoiNTI4NTg5MDgwNzM3NzExNDA3NCIsImN1cnJlbnRUaW1lU3RhbXAiOjE2MjU0OTA1MDEsImV4cGlyZVRpbWVTdGFtcCI6MjE0NzQ4MzY0NywicmFuZG9tIjo0MTg3ODIwOTg5LCJvdmVybGF5S2V5IjoiMGZjYTc0MzJmZGIzNDQ5YzBhNzIzMjg2NTA0ZDk4ODYiLCJvdmVybGF5SXYiOiJmZDZiOGEyMmNkNWFmOTk3Zjc5MDhkNTkxMGVkMGQwYiIsImNpcGhlcmVkT3ZlcmxheUtleSI6IiIsImNpcGhlcmVkT3ZlcmxheUl2IjoiIiwia2V5SWQiOjAsInN0cmljdE1vZGUiOjB9~2TknVZiPdfYi__AG7n4QyXG7CQzdaUakS33uFb6CRk0.video_12_3.m3u8?rlimit=3&sign=dd8e20c1818948ba0185f18cdbd69371&t=60e32e71&us=1625490497'
    run(m3u8=m3u8, name='', b64key='',m3u8BaseUrl='')


