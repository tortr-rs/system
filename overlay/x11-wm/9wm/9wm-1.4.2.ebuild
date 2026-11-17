EAPI=8

inherit toolchain-funcs

DESCRIPTION="A rio-like window manager for X"
HOMEPAGE="https://github.com/9wm/9wm"
SRC_URI="https://github.com/9wm/9wm/archive/refs/tags/${PV}.tar.gz -> ${P}.tar.gz"

LICENSE="MIT"
SLOT="0"
KEYWORDS="amd64"

RDEPEND="x11-libs/libX11 x11-libs/libXext"
DEPEND="${RDEPEND}"

src_compile() {
	emake CC="$(tc-getCC)" CFLAGS="${CFLAGS} -DSHAPE -DCOLOR -D_XOPEN_SOURCE" LDFLAGS="${LDFLAGS}" 9wm
}

src_install() {
	dobin 9wm
	newman 9wm.man 9wm.1
	dodoc README.md CUSTOMIZING.md
}
