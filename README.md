# 一个Python的m3u8流视频下载脚本

## 介绍

m3u8流视频日益常见，目前好用的下载器也有很多，我把之前自己写的一个小脚本分享出来，供广大网友使用。写此程序的目的在于给视频下载爱好者提供一个下载样例，可直接调用，勿再重复造轮子。

## 使用方法

在python中直接运行程序或进行外部调用

```
import m3u8down2

m3u8 = 'https://hls.videocc.net/379c2a7b33/9/379c2a7b330e4b497b07af76502c9449_1.m3u8'
m3u8down2.run(m3u8=m3u8, name='333', b64key='kNqWiPWUIWV1dIuTP5ACBQ==')
```

### 下载指令

| m3u8        | 输入的m3u8链接或本地文件 | https://hls.videocc.net/379c2a7b33/9/379c2a7b330e4b497b07af76502c9449_1.m3u8 或 C:\Users\happy\Downloads\v.f230 |
| ----------- | ------------------------ | ------------------------------------------------------------ |
| name        | 自定义名称               |                                                              |
| b64key      | 自定义key                |                                                              |
| b64iv       | 自定义iv                 |                                                              |
| enableDel   | 下载后自动删除           | 默认为True                                                   |
| m3u8BaseUrl | 链接前缀                 | 用在拖入本地文件时链接不全                                   |

## 源码

```python
import re,os,time,sys
from shutil import rmtree
import requests
import base64,json
from Crypto.Cipher import AES
from queue import Queue
from threading import Thread
import logging

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
            self.m3u8text = requests.get(url=m3u8, headers=headers).text
            self.m3u8BaseUrl = '/'.join(m3u8.split('?')[0].split('/')[:-1]) + '/'
        # C:\Users\happy\Downloads\v.f230 (1).m3u8
        else:
            if name == '':
                self.title = m3u8.split('\\')[-1].split('.')[-2]
            else:
                self.title = name
            with open(f'{m3u8}','r') as f:
                self.m3u8text = f.read()
            self.m3u8BaseUrl = m3u8BaseUrl




        if os.path.exists(self.title) == False:
            os.makedirs(self.title)
        self.tsurls = re.findall('#EXTINF.+\n(.+?)\n',self.m3u8text)
        self.count = len(self.tsurls)
        title = self.title
        count = self.count
        # 判读是否加密及加密类型
        try:
            self.encrypt = bool(re.findall('URI="(.+?)"', self.m3u8text)[0])
        except:
            self.encrypt = False
        self.key = key
        self.iv = iv
        if self.encrypt == True:
            method = 'AES-128'
            self.key = self.getkey(method)
            self.iv = self.getiv(method)
        else:
            method = ''
            self.key = ''
            self.iv = ''

        segments = []
        for i in range(len(self.tsurls)):
            segment = {
                'title':self.title,
                "index": i,
                "count":self.count,
                "method": method,
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
                'encrypt':self.encrypt,
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
        key = requests.get(url=keyurl,headers=headers).content
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
        try:
            ts = requests.get(url=segment['segUrl'], headers=headers).content
        except:
            print('链接无效，尝试设置BaseUrl!')
            sys.exit(0)
        if segment['method'] == 'AES-128':
            key = base64.b64decode(segment['key'])
            if len(key) != 16:
                print('The key is wrong!')
            iv = base64.b64decode(segment['iv'])
            cryptor = AES.new(key=key, mode=AES.MODE_CBC, iv=iv)
            ts = cryptor.decrypt(ts)
        if os.path.exists(f'{title}/Part_0') == False:
            os.makedirs(f'{title}/Part_0')
        with open(f'{title}/Part_0/{index}.ts', 'wb') as f:
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
            self.combine()

    def combine(self):
        print('\t视频合并中……',end='')
        filelists = [fr"file '{os.path.abspath('')}\{title}\Part_0\{str(i).zfill(6)}.ts'" for i in range(count)]
        with open(fr"{os.path.abspath('')}\{title}\filelist.txt", 'w') as f:
            text = '\n'.join(filelists)
            f.write(text)
        cmd = fr"ffmpeg -f concat -safe 0 -i {os.path.abspath('')}\{title}\filelist.txt -c copy {os.path.abspath('')}\{title}.mp4 -loglevel panic"
        os.system(cmd)
        print('\t合并完成！\t',end='')
        if enabledel == True:
            self.del_after_done()

    def del_after_done(self):
        rmtree(rf'{os.path.abspath("")}\{title}', ignore_errors=True)
        print('删除分片成功！')


def run(m3u8,name='',b64key='',b64iv='',enableDel=True,m3u8BaseUrl=''):
    try:
        m3u8infos(m3u8, name, b64key, b64iv, m3u8BaseUrl, enableDel).putsegments()
    except:
        print('Error in reading file.')
        sys.exit(0)
    for i in range(16):
        t = Consumer()
        t.start()

if __name__ == '__main__':
    m3u8 = 'https://hls.videocc.net/379c2a7b33/9/379c2a7b330e4b497b07af76502c9449_1.m3u8'
    # m3u8 = r"C:\Users\happy\Downloads\v.f230 (1).m3u8"
    try:
        run(m3u8=m3u8, name='', b64key='',m3u8BaseUrl='')
    except Exception as e:
        logging.exception(e)

```

### 简单说明

代码分为两个类，一个解析m3u8链接为标准可识别的链接，另一个为多线程下载类。

### 不足

代码可以精简到一个类中，但是多线程会不太好写

默认16线程，可能会导致电脑卡

只支持AES-128解密

使用需要 ffmpeg 合并

## 文件打包

https://aohua.lanzoui.com/iCOm7quqtyf

