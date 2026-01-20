## macOS + Lighttpd (Homebrew) quick start

This repo’s CGI (`Solar`) is designed to run under a web server and generate an HTML page which embeds a dynamically-generated GIF, similar to Fourmilab’s production endpoint: `https://www.fourmilab.ch/cgi-bin/Solar`.

### 1) Stage a local runnable tree

From the repo root:

```bash
bash ./scripts/macos_local_lighttpd_install.sh
```

This will create `./local/` with:

- `local/htdocs/` (copy of `webtree/`)
- `local/cgi-bin/Solar.cgi` (CGI executable)
- `local/cgi-executables/` (runtime assets the CGI loads at runtime)
- `local/lighttpd.conf` (ready-to-run Lighttpd config)

### 2) Run Lighttpd

```bash
lighttpd -D -f ./local/lighttpd.conf
```

### 3) Use Solar System Live

Open:

- `http://127.0.0.1:8080/cgi-bin/Solar`

The page should render and the generated image should load (it’s embedded as a `di=` stateless request to `/cgi-bin/Solar`, rewritten to `Solar.cgi`).

