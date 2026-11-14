# conf KEY prints the value of KEY in /etc/init.conf; a {list} comes out separated by spaces
conf() {
	_k=$1 _v= _in=
	while read -r _l; do
		_l=${_l%%#*}
		if [ -z "$_in" ]; then
			case $_l in *=*) ;; *) continue;; esac
			set -- ${_l%%=*}
			[ "$1" = "$_k" ] || continue
			_l=${_l#*=}
			_in=1
		fi
		_v="$_v $_l"
		case $_v in *\{*) case $_v in *\}*) break;; esac;; *) break;; esac
	done < "${INIT_CONF:-/etc/init.conf}"
	set -- $_v
	case $1 in \{*) _v=${_v//[\{\},]/ };; esac
	set -- $_v
	echo "$*"
}
