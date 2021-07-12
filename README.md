# m3u8流视频下载脚本 支持多平台调用

## 介绍

m3u8流视频日益常见，目前好用的下载器也有很多，我把之前自己写的一个小脚本分享出来，供广大网友使用。写此程序的目的在于给视频下载爱好者提供一个下载样例，可直接调用，勿再重复造轮子。

## 使用方法

### 方法一

用python 调用源码

```
import m3u8down2

m3u8 = 'https://hls.videocc.net/379c2a7b33/9/379c2a7b330e4b497b07af76502c9449_1.m3u8'
m3u8down2.run(m3u8=m3u8, name='333', b64key='kNqWiPWUIWV1dIuTP5ACBQ==')
```

[![WPgCHP.jpg](https://z3.ax1x.com/2021/07/12/WPgCHP.jpg)](https://imgtu.com/i/WPgCHP)

### 方法二

命令行调用下载器

[![Wpy5o4.jpg](https://z3.ax1x.com/2021/07/10/Wpy5o4.jpg)](https://imgtu.com/i/Wpy5o4)

详细命令：

### 下载指令

| -m3u8        | 视频地址：网络链接或本地文件链接 | https://hls.videocc.net/379c2a7b33/9/379c2a7b330e4b497b07af76502c9449_1.m3u8 或 C:\Users\happy\Downloads\v.f230 |
| ------------ | -------------------------------- | ------------------------------------------------------------ |
| -name        | 自定义名称                       |                                                              |
| -b64key      | 自定义key                        |                                                              |
| -b64iv       | 自定义iv                         |                                                              |
| -enableDel   | 下载后自动删除                   | 默认为True                                                   |
| -m3u8BaseUrl | 链接前缀                         | 用在拖入本地文件时链接不全                                   |
| -showLogs    | 显示错误日志                     | 默认False                                                    |
| -Threads     | 线程数                           | 默认16线程                                                   |
| -retries     | 尝试重试次数                     | 默认16                                                       |

## 源码

https://github.com/Nchujx/m3u8down/blob/main/m3u8down2.py

### 简单说明

1. 采用多线程方式下载m3u8类视频
2. 支持aes-cbc解密，以及对不能解密的视频二进制合并
3. 可采用命令行方式调用成品或python内直接调用源码进行使用
4. 该下载器内置ffmpeg，自带转码和合并
5. 可在linux下使用
6. 彩色文本输出

### 不足

采用线程方式，可能会导致电脑卡顿

暂且只支持aes-128-cbc解密

暂不支持代理，自定义请求头

## Github

github :https://github.com/Nchujx/m3u8down

release:https://github.com/Nchujx/m3u8down/releases


