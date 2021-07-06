# m3u8流视频下载脚本 支持多平台调用

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

见附件m3u8down.py

### 简单说明

1. 代码分为两个类，一个解析m3u8链接为标准可识别的链接，另一个为多线程下载类。
2. 文件无法解密时支持二进制合并
3. 支持本地读取key文件
4. 视频默认二进制合并,内置ffmpeg转码
5. 支持linux平台调用



### 不足

代码可以精简到一个类中，但是多线程会不太好写

默认16线程，可能会导致电脑卡

只支持AES-128解密

## Github

github : [Nchujx/m3u8down: 一个m3u8视频流下载脚本 (github.com)](https://github.com/Nchujx/m3u8down/)

