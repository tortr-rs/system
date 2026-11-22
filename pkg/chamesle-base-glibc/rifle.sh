# rifle is the coreutils of Chamesle: its tools come first, GNU's are behind them
case ":$PATH:" in *:/usr/lib/rifle/bin:*) ;; *) PATH=/usr/lib/rifle/bin:$PATH;; esac
