#!/bin/bash
# PostToolUse: проверка синтаксиса Python-файла сразу после правки
f=$(jq -r '.tool_input.file_path // empty')
case "$f" in
  *.py)
    if ! out=$(python3 -m py_compile "$f" 2>&1); then
      echo "Синтаксическая ошибка в $f:" >&2
      echo "$out" >&2
      exit 2
    fi
    ;;
esac
exit 0
