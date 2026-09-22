# Hunk

**Less ceremony. Just the change.** A compact Git diff presentation powered by
[Delta](https://github.com/dandavison/delta).

One bold path per file, dim hunk locations and context, red/green changes, and
word-level emphasis. Keeps `+`/`-` markers and meaningful file metadata. No
boxes, full-width rules, line-number gutters, or side-by-side columns. The
preset targets dark terminals and deliberately uses quiet, unhighlighted context.

## Install

Requires Git, Bash, GNU coreutils, less, and Delta (tested with 0.19.2).
On Arch, install `git-delta`. From this repository:

```sh
git clone https://github.com/lukelex/hunk.git
cd hunk
make install                         # ~/.local; put ~/.local/bin on PATH
# Or: sudo make install PREFIX=/usr/local
```

Packaging tools can use `make install PREFIX=/usr DESTDIR="$pkgdir"`.
The two executables and `share/hunk/delta.gitconfig` form a self-contained
installation.

## Use

```sh
git hunk
git hunk --cached
git hunk HEAD~1
git hunk -U8 -- path/to/file
```

All arguments go to `git diff`. Hunk defaults to two context lines. Git handles
paging itself, so redirects produce original patches and `--exit-code` keeps
its normal meaning. Short terminal diffs remain visible; longer ones use less.

To make Hunk the default for regular Git commands:

```sh
git config --global pager.diff hunk-pager
git config --global pager.show hunk-pager
git config --global diff.context 2
```

To preview a patch explicitly: `git diff --color=never | hunk-pager`.
To bypass presentation: `git --no-pager diff`.

The preset lives in `share/hunk/delta.gitconfig`. Explicit pager arguments such
as `hunk-pager --light` override it. The pager falls back to less if Delta is
missing. Context selection belongs to Git, not the formatter.

## Development

Run `make test` with Python 3 and Delta installed. Run ShellCheck on `bin/*`.
After editing, run `make install` again to refresh a copied installation.

To disable, unset `pager.diff`, `pager.show`, and `diff.context` in the Git
configuration where you enabled them, then run `make uninstall`.
