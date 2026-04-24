# simcamera

`simcamera` is a small desktop camera app written in Python with Tkinter and OpenCV.

## Local build on Arch

```bash
makepkg -si
simcamera
```

## Runtime dependencies

- `python`
- `python-opencv`
- `python-pillow`
- `python-numpy`
- `tk`
- `ffmpeg`
- `libnotify`

Optional audio recording support:

- `python-sounddevice`
- `python-scipy`

## Before publishing to AUR

1. Put this project in a git repository.
2. Replace the `url=` value in `PKGBUILD` with your real repository URL.
3. Decide on a real license and update `license=`.
4. Make sure `simcamera` does not already exist in AUR.
5. Generate `.SRCINFO` with:

```bash
makepkg --printsrcinfo > .SRCINFO
```

6. Copy `PKGBUILD`, `.SRCINFO`, `camera.py`, `simcamera`, and `simcamera.desktop` into your AUR package repository.

## Publish to AUR

Create an AUR account and add your SSH public key there, then:

```bash
git init -b master
git remote add aur ssh://aur@aur.archlinux.org/simcamera.git
makepkg --printsrcinfo > .SRCINFO
git add PKGBUILD .SRCINFO camera.py simcamera simcamera.desktop README.md .gitignore
git commit -m "Initial AUR release"
git push aur master
```

If you prefer to start from the empty AUR repo instead:

```bash
git clone ssh://aur@aur.archlinux.org/simcamera.git
cd simcamera
```

Then copy in the package files, commit, and push.
