# pailixiang-downloader

简体中文 | [English](README.en.md)

一条命令,下载 [拍立享 / pailixiang.com](https://live.pailixiang.com) 相册里的**全部原图(全分辨率)**。

拍立享相册页是 Vue 单页应用——HTML 里**没有照片**,照片是滚动时从 JSON 接口懒加载的。所以"右键另存""截图""滚动到底再抓"都会漏掉大部分照片。本工具直接调用接口,一张不落地全拿下来。

- ✅ 纯 Python 3 标准库——**无需 pip 安装、无需浏览器/Selenium**
- ✅ 跨平台:macOS、Windows、Linux
- ✅ 下载的是原始文件(不是压缩/带水印的预览图)
- ✅ 自动翻页处理(相册常有几百张)
- ✅ 可断点续传——重跑会跳过已下载的文件

## 安装

需要 Python 3.7+,无任何依赖。

```bash
git clone https://github.com/muxia23/pailixiang-downloader.git
cd pailixiang-downloader
```

## 使用

```bash
python3 pailixiang_dl.py <相册链接或代码> [-o 输出目录]
```

示例:

```bash
# 完整链接
python3 pailixiang_dl.py https://live.pailixiang.com/album/a12581882107 -o ~/Downloads/相册

# 只给代码,输出到 ./<相册名>
python3 pailixiang_dl.py a12581882107

# 只统计照片数量,不下载
python3 pailixiang_dl.py a12581882107 --list-only
```

Windows 上如果 `python3` 不是启动器名,请改用 `python`。

### 参数

| 参数 | 说明 |
|------|------|
| `-o, --output 目录` | 输出目录(默认:`./<相册名>`) |
| `--page-size N` | 每页拉取的照片数(默认 80) |
| `--list-only` | 只打印照片总数后退出 |

文件按拍摄时间排序,命名为 `序号_原文件名.jpg`。重跑时已存在(非空)的文件会被跳过,所以中断后再跑可无缝续传。

## 工作原理

1. `POST mapi.pailixiang.com/plx/WapAbm/AlbumGetView` → 解析出相册的内部 ID。
2. `POST .../WapAbm/AlbumSearchPhoto`,按 `StartIndex` 翻页直到取尽 → 完整照片清单。
3. 下载每张照片的签名地址 `DownloadImageUrl`(即原始全分辨率文件)。

每个请求都带一个 `ak` 签名,网站在客户端用常量 `appKey` 算出来;`gen_ak()` 复现了该算法,因此无需浏览器、无需登录。

> **关于 `PhotoSearchCount`:** 相册视图里的 `PhotoSearchCount` 是*每页数量*,不是总数。本工具会按 `StartIndex` 翻页并按照片 ID 去重得到真实总数。**不要以为前 ~80 张就是整个相册。**

### 维护

如果网站轮换了 `appKey` 或迁移了接口导致下载失败,用内置的零依赖工具重新提取当前常量(无需浏览器):

```bash
python3 tools/inspect_bundle.py <相册链接>
```

然后更新 `pailixiang_dl.py` 顶部的 `APP_KEY` / `API_BASE`。

## 免责声明

请仅用于下载你有权访问的相册(例如你自己的活动,或他人分享给你的相册)。请尊重摄影师和平台的使用条款与版权。本工具调用的是相册网页本身使用的公开接口。

## 许可证

MIT
