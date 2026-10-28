#!/bin/sh
set -e
python -m complaintiq ensure-artifacts   # builds a small synthetic demo index if none is mounted
case "${CIQ_APP:-api}" in
  ui)  exec streamlit run src/complaintiq/ui/streamlit_app.py --server.port "${PORT:-7860}" --server.address 0.0.0.0 ;;
  *)   exec python -m complaintiq serve --host 0.0.0.0 --port "${PORT:-8000}" ;;
esac
