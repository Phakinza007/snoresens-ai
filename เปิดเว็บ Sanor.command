#!/bin/zsh
set -e
unsetopt BG_NICE
trap 'sanor_exit_code=$?; if (( sanor_exit_code != 0 )); then echo "Sanor เปิดไม่สำเร็จ (รหัส $sanor_exit_code)"; read -k 1 "?กดปุ่มใดก็ได้เพื่อปิด..."; fi' EXIT
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  echo "ไม่พบ .venv กรุณารัน: python3.12 -m venv .venv"
  exit 1
fi
if ! .venv/bin/python -c 'import numpy, soundfile, scipy, tensorflow' 2>/dev/null; then
  echo "กำลังติดตั้งแพ็กเกจที่จำเป็น..."
  .venv/bin/python -m pip install -r requirements-inference.txt
fi
mkdir -p results
url='http://127.0.0.1:8765'
if curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then
  echo "Sanor เปิดอยู่แล้ว: $url"
  open "$url"
  exit 0
fi
echo "กำลังเริ่ม Sanor..."
SANOR_NO_BROWSER=1 nohup .venv/bin/python -u web_server.py > results/web_server.log 2>&1 < /dev/null &
server_pid=$!
sleep 3
if ! kill -0 "$server_pid" 2>/dev/null || ! curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then
  echo "เปิดเซิร์ฟเวอร์ไม่สำเร็จ:"
  cat results/web_server.log
  exit 1
fi
echo "Sanor พร้อมใช้งาน: $url"
open "$url"
