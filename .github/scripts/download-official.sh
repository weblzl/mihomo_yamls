#!/usr/bin/env bash
source "$(dirname "$0")/lib_fetch.sh"

echo "📦 Processing Official Configs..."

TASKS=$(cat <<'EOF'
https://wiki.metacubex.one/example/mrs|THEYAMLS/Official_Examples/Metacubex/rule-set_config.yaml
https://wiki.metacubex.one/example/geox|THEYAMLS/Official_Examples/Metacubex/geox_config.yaml
EOF
)

run_parallel_tasks "$TASKS" 2
