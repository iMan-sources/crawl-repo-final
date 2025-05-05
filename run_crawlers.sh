#!/bin/bash

# Script chạy định kỳ mỗi 4 tiếng để crawl release và repo

# Thời gian hiện tại để ghi log
timestamp=$(date "+%Y-%m-%d %H:%M:%S")
echo "[$timestamp] Bắt đầu chạy crawler" >> logs/crawler_schedule.log

# Đường dẫn đến virtualenv (nếu có)
VENV_PATH=".venv/bin/activate"

# Kích hoạt venv nếu tồn tại
if [ -f "$VENV_PATH" ]; then
    source "$VENV_PATH"
fi

# Bước 1: Chạy crawler repo
echo "[$timestamp] Đang chạy repo crawler..." >> logs/crawler_schedule.log
python run_crawler.py >> logs/repo_crawler.log 2>&1



# Kiểm tra crawler release có chạy thành công không
if [ $? -ne 0 ]; then
    echo "[$timestamp] X Lỗi khi crawl release!" >> logs/crawler_schedule.log
    exit 1
fi

# Bước 2: Chạy crawler release
echo "[$timestamp] Đang chạy release crawler..." >> logs/crawler_schedule.log
python run_release.py >> logs/release_crawler.log 2>&1


# Kiểm tra crawler repo có chạy thành công không
if [ $? -ne 0 ]; then
    echo "[$timestamp] X Lỗi khi crawl repo!" >> logs/crawler_schedule.log
    exit 1
fi

echo "[$timestamp] V Crawler hoàn tất!" >> logs/crawler_schedule.log
