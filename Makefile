PREFIX ?= $(HOME)/.local
DESTDIR ?=

.PHONY: install uninstall test
install:
	install -Dm755 bin/git-hunk "$(DESTDIR)$(PREFIX)/bin/git-hunk"
	install -Dm755 bin/git-hunk-status "$(DESTDIR)$(PREFIX)/bin/git-hunk-status"
	install -Dm755 bin/hunk-pager "$(DESTDIR)$(PREFIX)/bin/hunk-pager"
	install -Dm755 bin/hunk-render "$(DESTDIR)$(PREFIX)/bin/hunk-render"
	install -Dm644 share/hunk/delta.gitconfig "$(DESTDIR)$(PREFIX)/share/hunk/delta.gitconfig"

uninstall:
	rm -f "$(DESTDIR)$(PREFIX)/bin/git-hunk" "$(DESTDIR)$(PREFIX)/bin/hunk-pager"
	rm -f "$(DESTDIR)$(PREFIX)/bin/git-hunk-status"
	rm -f "$(DESTDIR)$(PREFIX)/bin/hunk-render"
	rm -f "$(DESTDIR)$(PREFIX)/share/hunk/delta.gitconfig"

test:
	python3 -m unittest discover -s tests -v
