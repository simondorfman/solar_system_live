#!/usr/bin/env bash
set -euo pipefail

# Stages a runnable local Lighttpd tree under ./local/ and builds the CGI.
#
# Layout created:
#   local/
#     htdocs/            (served as docroot)  -> copy of ./webtree
#     cgi-bin/           (CGI scripts)        -> Solar.cgi
#     cgi-executables/   (runtime assets)     -> *.bmp, solar-post.html
#     lighttpd.conf
#
# Why cgi-executables?
#   The Solar CGI resolves runtime assets via locfile() as ../cgi-executables/
#   relative to the executable in cgi-bin (see src/vplanet.c).

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STAGE_DIR="${ROOT_DIR}/local"

echo "==> Building Solar CGI"
(cd "${ROOT_DIR}/src" && make clean >/dev/null && make solar)

echo "==> Creating staging tree at ${STAGE_DIR}"
rm -rf "${STAGE_DIR}"
mkdir -p \
  "${STAGE_DIR}/htdocs" \
  "${STAGE_DIR}/cgi-bin" \
  "${STAGE_DIR}/cgi-executables"

echo "==> Copying web content"
cp -R "${ROOT_DIR}/webtree/." "${STAGE_DIR}/htdocs/"

echo "==> Installing CGI (as Solar.cgi) and runtime assets"
install -m 0755 "${ROOT_DIR}/src/solar" "${STAGE_DIR}/cgi-bin/Solar.cgi"
install -m 0644 "${ROOT_DIR}/src/solar-post.html" "${STAGE_DIR}/cgi-executables/solar-post.html"
install -m 0644 "${ROOT_DIR}/src/solar_images.bmp" "${STAGE_DIR}/cgi-executables/solar_images.bmp"
install -m 0644 "${ROOT_DIR}/src/yourtel-icons.bmp" "${STAGE_DIR}/cgi-executables/yourtel-icons.bmp"
install -m 0644 "${ROOT_DIR}/src/yourtel-icons-b.bmp" "${STAGE_DIR}/cgi-executables/yourtel-icons-b.bmp"
install -m 0644 "${ROOT_DIR}/src/yourtel-icons-w.bmp" "${STAGE_DIR}/cgi-executables/yourtel-icons-w.bmp"
install -m 0644 "${ROOT_DIR}/src/yourtel-icons-r.bmp" "${STAGE_DIR}/cgi-executables/yourtel-icons-r.bmp"

# Use absolute paths so you can start lighttpd from anywhere.
# Use a single-quoted heredoc to avoid shell expanding Lighttpd variables like $HTTP and rewrite $1.
cat > "${STAGE_DIR}/lighttpd.conf" <<'EOF'
server.document-root = "__STAGE_DIR__/htdocs"
server.port = 8080
server.bind = "127.0.0.1"

# Keep logs local to the staged tree for easy debugging.
server.errorlog = "__STAGE_DIR__/lighttpd-error.log"
accesslog.filename = "__STAGE_DIR__/lighttpd-access.log"

server.modules += (
  "mod_access",
  "mod_accesslog",
  "mod_alias",
  "mod_cgi",
)

# Serve CGI from /cgi-bin/.
# NOTE: ordering matters: the specific Solar mapping must come before the
# generic /cgi-bin/ directory mapping.
alias.url = (
  "/cgi-bin/Solar" => "__STAGE_DIR__/cgi-bin/Solar.cgi",
  "/cgi-bin/"      => "__STAGE_DIR__/cgi-bin/",
)

# Run CGI scripts by extension
cgi.assign = ( ".cgi" => "" )
cgi.execute-x-only = "enable"

# Minimal permissive access for local dev
$HTTP["remoteip"] == "127.0.0.1" { }
EOF

# Replace placeholder with the actual stage dir
sed -i '' "s|__STAGE_DIR__|${STAGE_DIR}|g" "${STAGE_DIR}/lighttpd.conf"

cat <<EOF

==> Done.

Next steps:
  1) Run Lighttpd against the staged config:
       lighttpd -D -f "${STAGE_DIR}/lighttpd.conf"

  2) Open:
       http://127.0.0.1:8080/cgi-bin/Solar

Notes:
  - The generated image should load via /cgi-bin/Solar?di=... just like the
    production site (example: https://www.fourmilab.ch/cgi-bin/Solar).
EOF

