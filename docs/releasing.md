# Dual-repository release guide

WakeVoice ships as **two GitHub repositories** with the same voice assistant,
split by the shape end users receive:

| Repository | Contents | Best for | Run |
|---|---|---|---|
| `jsxxwhai/wakevoice` | Full source + `main.py` / `scripts/` / docs | Developers & tinkerers | `python main.py --wake`, or double-click `安装并启动.bat` after installing Python |
| `jsxxwhai/wakevoice-portable` | Static README + release assets (EXE zip), **no binaries committed** | End users without Python | Download `WakeVoiceDesktop-portable-vX.zip` from Releases and double-click the EXE |

> Both distributions are built from the same source. The portable EXE is produced by
> `scripts/build_dist.py` and uploaded as a Release asset - it is never committed to git.

---

## How a release works now (fully automatic)

1. Bump the version in `pyproject.toml` / `CHANGELOG.md`, commit, tag, and push:
   ```bash
   git add -A
   git commit -m "release: prepare vX.Y.Z"
   git tag vX.Y.Z
   git push origin main vX.Y.Z
   ```
2. GitHub Actions (`.github/workflows/release.yml`) then runs, in order:
   - `test`: lint + unit tests.
   - `publish`: build `sdist` + `wheel` from the source repo.
   - `build-portable`: build the portable EXE and zip it.
   - `attach`: create/refresh the **source repo release** `vX.Y.Z` on
     `jsxxwhai/wakevoice` with the wheel, sdist and portable zip.
   - `mirror-portable`: create/refresh the **portable repo release** `vX.Y.Z`
     on `jsxxwhai/wakevoice-portable` with the same portable zip asset.
3. No manual zip upload or git commit is needed on the portable side any more.
   Both Releases pages are updated automatically from one tag push.

> Requirement: the `PORTABLE_REPO_TOKEN` secret must exist on
> `jsxxwhai/wakevoice` with `repo` scope, so the workflow can write to
> `jsxxwhai/wakevoice-portable`.

---

## One-time setup

- Create the two public repositories.
- On `jsxxwhai/wakevoice`: Settings -> Secrets and variables -> Actions, add
  `PORTABLE_REPO_TOKEN` (a fine-grained or classic PAT with `repo` scope for
  `jsxxwhai/wakevoice-portable`).
- Keep the portable repo's static `README.md`, `LICENSE`, `assets/` and
  `使用说明.txt` in sync with `release_templates/README_portable.md` whenever
  wording changes (small manual edit; no binaries involved).

## Manual fallback

If you ever need to build and publish by hand (e.g. no network for Actions):

```bash
python scripts/build_dist.py --clean --source --portable --zip
# then upload build_out assets with `gh release create` to both repos.
```

## Verification

- Source repo: after pushing `vX.Y.Z`, the Release page of
  `jsxxwhai/wakevoice` shows `wakevoice-X.Y.Z.tar.gz`, the wheel, and the
  portable zip.
- Portable repo: the Release page of `jsxxwhai/wakevoice-portable` shows the
  same portable zip for tag `vX.Y.Z`.
- Download the portable zip, unzip, double-click `WakeVoiceDesktop.exe`, say
  "你好伙伴", and confirm it replies "我在".
