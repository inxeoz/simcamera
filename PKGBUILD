pkgname=simcamera
pkgver=0.1.0
pkgrel=1
pkgdesc="Simple desktop camera app built with Tkinter and OpenCV"
arch=('any')
url="https://github.com/inxeoz/simcamera"
license=('MIT')
depends=(
  'python'
  'python-opencv'
  'python-pillow'
  'python-numpy'
  'tk'
  'ffmpeg'
  'libnotify'
)
optdepends=(
  'python-sounddevice: microphone recording support'
  'python-scipy: save recorded audio before ffmpeg muxing'
)
source=(
  'camera.py'
  'simcamera'
  'simcamera.desktop'
)
sha256sums=(
  'SKIP'
  'SKIP'
  'SKIP'
)

package() {
  install -Dm755 "$srcdir/simcamera" "$pkgdir/usr/bin/simcamera"
  install -Dm755 "$srcdir/camera.py" "$pkgdir/usr/lib/simcamera/camera.py"
  install -Dm644 "$srcdir/simcamera.desktop" "$pkgdir/usr/share/applications/simcamera.desktop"
}
