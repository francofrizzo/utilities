# Personal Utilities

A collection of personal command-line utilities.

## Layout

- **`bin/`** — standalone single-file scripts, symlinked onto `PATH` (`~/.bin`)
  by [`install.sh`](./install.sh).
- **Top-level dirs** (e.g. [`label/`](./label/)) — larger self-contained tools
  or packages with their own build/distribution.

## Standalone scripts (`bin/`)

```bash
./install.sh   # symlink bin/* into ~/.bin (backs up any existing files)
```

### `cleanup-disk.sh`

Reclaim disk space from the usual self-regrowing offenders (Go/Docker/brew/npm
caches, Playwright, Time Machine local snapshots). Safe by default — only
removes things that regenerate.

```bash
cleanup-disk.sh --dry-run     # show what would happen, change nothing
cleanup-disk.sh --snapshots   # also thin TM local snapshots (needs sudo)
cleanup-disk.sh --aggressive  # also prune Docker volumes + deeper caches
```

### `emoji`

Convert text to related emojis.

```bash
emoji "pizza party tonight"
```

### `transcribe`

Transcribe an audio file with Whisper.

```bash
transcribe meeting.m4a
```

> `emoji` and `transcribe` use the OpenAI API — they need their Python deps and
> an API key in the macOS keychain:
>
> ```bash
> pip install -r bin/requirements.txt      # openai, keyring (a venv is fine)
> python3 -c 'import keyring; keyring.set_password("openai", "api_key", "sk-...")'
> ```

## Tools

### [print-label](./label/)

Thermal printer label maker for Bluetooth cat printers. Print beautiful labels with Helvetica Neue font.

```bash
print-label "PANKO"
print-label "BREAD CRUMBS" --subtext "Japanese Style"
```

**Install:**
```bash
brew install francofrizzo/tap/print-label
```

## License

MIT
