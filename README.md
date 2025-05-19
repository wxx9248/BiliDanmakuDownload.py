# Bilibili Danmaku Downloader

A Python program to download danmaku (realtime comments) from Bilibili videos.

## Features

- Supports various resource types:
    - avid (single video, starts with "av")
    - bvid (single video, starts with "bv")
    - epid (episode)
    - ssid (season)
    - mdid (media)
- Exports danmaku in multiple formats: XML, JSON, CSV, plain text
- Interactive CLI mode for easy use
- Command-line mode for scripting/automation
- Async operations for fast downloads
- Rich progress display
- Cookie authentication for accessing restricted content

## Requirements

- Python 3.13+
- Dependencies listed in `requirements.txt`

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/BiliDanmakuDownload.py.git
cd BiliDanmakuDownload.py
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Setting Up Cookies (Optional)

For accessing restricted content or improving API limits, you can provide your Bilibili cookie:

1. Copy the `cookie.template.txt` file to `cookie.txt`:
   ```bash
   cp cookie.template.txt cookie.txt
   ```

2. Login to Bilibili in your browser, then get your cookie:
    - Open Developer Tools (F12)
    - Go to Network tab
    - Refresh the page
    - Click on any request to bilibili.com
    - Find the "Cookie" header in the request
    - Copy the entire cookie string

3. Paste your cookie into the `cookie.txt` file, replacing all the template text

Note: The `cookie.txt` file is included in `.gitignore` to prevent accidentally committing your personal cookies.

## Usage

### Interactive Mode

To use the interactive mode, simply run:

```bash
python main.py
```

The program will prompt you for:

- Resource ID (avid, bvid, epid, ssid, mdid)
- Output format (XML, JSON, CSV, plain text)
- Output directory
- Maximum number of segments to download
- Cookie file path (optional)

### Command Line Mode

You can also use the command line interface:

```bash
python main.py download av12345
python main.py download BV1xx411c7mD
python main.py download ep67890 --format json
python main.py download ss12345 -o my_danmaku -f csv
python main.py download av12345 --cookie my_cookie.txt
```

#### Options:

- `resource_id`: Resource ID (avid, bvid, epid, ssid, mdid)
- `--output`, `-o`: Output directory (default: "output")
- `--format`, `-f`: Output format (xml, json, csv, txt) (default: "xml")
- `--segments`, `-s`: Maximum number of segments to download per content (default: 10)
- `--cookie`, `-c`: Path to the cookie file (default: "cookie.txt")

## Formats

- **XML**: Compatible with most danmaku players
- **JSON**: For data analysis
- **CSV**: For importing into spreadsheets
- **TXT**: Plain text format with timestamps

## Notes

- Each segment is 6 minutes of content
- Resource IDs must include their prefix (av, bv, ep, ss, md)
- Using a cookie file allows you to access content that requires login

## License

MIT License

## Accreditation

* [bilibili-API-collect](https://github.com/SocialSisterYi/bilibili-API-collect/)
