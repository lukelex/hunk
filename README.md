<p align="center">
  <img src="docs/logo.svg" alt="Hunk logo — an H with Git diff minus and plus marks" width="120" height="120">
</p>

# Hunk

**Less ceremony. Just the change.** Compact, readable Git diffs in your terminal,
powered by [Delta](https://github.com/dandavison/delta).

Hunk adds a `git hunk` command and a reusable Git pager. It pairs a small Bash
wrapper with a Delta preset so you can focus on changed lines:

- **Bold filenames and muted directories**, with quieter hunk locations and readable context.
- **Compact per-file `+12 −4` totals** and consistent whitespace between files.
- **Red/green changes and word-level emphasis**, keeping the familiar `+`/`-` markers.
- **Useful file metadata**, including renames, additions, deletions, and mode changes.
- **A compact layout** with two context lines by default, without boxes,
  full-width rules, line-number gutters, or side-by-side columns.

The default and Railscasts themes target dark terminals; `light` targets light backgrounds. Git still handles diff arguments,
exit codes, and paging; redirected output remains an original Git patch.

## Install

### 1. Install dependencies

You need Git, Bash, Python 3.9+, GNU coreutils (including `realpath` and `install`), Make,
less, and Delta (tested with 0.19.2). On Arch Linux:

```sh
sudo pacman -S --needed git bash python coreutils make less git-delta
```

For other systems, install these tools with your package manager and follow
[Delta's installation instructions](https://github.com/dandavison/delta#installation).
The Makefile uses GNU `install`, so ensure GNU coreutils are on your `PATH`.

### 2. Install Hunk

```sh
git clone https://github.com/lukelex/hunk.git
cd hunk
make install
```

This installs Hunk into `~/.local`. Add its executables to your current shell's
`PATH`:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

Add that line to your shell's startup file (such as `~/.bashrc` or `~/.zshrc`)
to keep it available in new terminals. Git discovers `git hunk` through the
installed `git-hunk` executable.

For a system-wide installation instead:

```sh
sudo make install PREFIX=/usr/local
```

Packaging tools can use `make install PREFIX=/usr DESTDIR="$pkgdir"`.
The four executables and `share/hunk/delta.gitconfig` form a self-contained
installation.

## Use

From inside a Git repository:

```sh
git hunk                         # unstaged changes
git hunk --cached                # staged changes
git hunk HEAD~1                  # compare working tree with the previous commit
git hunk -U8 -- path/to/file      # eight context lines, limited to one file
```

Except for the `status` subcommand, all arguments go to `git diff`. Use
`git hunk -- status` to diff a file named `status`. Hunk defaults to two context lines. Git handles
paging itself, so redirects produce original patches and `--exit-code` keeps
its normal meaning. Short terminal diffs remain visible; longer ones use less.

### Color status by change type

```sh
git hunk status                   # branch summary and grouped changes
git hunk status --short           # compact staged/unstaged columns
git hunk status --hints           # Git's detailed layout and guidance
git hunk status -- path/to/file   # limit to a path
```

Modified and renamed files are blue, added files green, and deleted files red.
The default theme uses bright ANSI blue and ANSI green/red; Railscasts uses
`#6D9CBE`, `#87AF5F`, and `#DA4939`. Untracked paths are light gray (ANSI bright
white by default, `#BDC3C7` in Railscasts). Both honor `hunk.theme` and `HUNK_THEME`.
The default layout keeps Git's branch summary and uses counted **Staged**,
**Unstaged**, **Untracked**, and **Conflicts** groups. Aligned `mod`, `new`,
`del`, `ren`, `cpy`, and `typ` labels identify changes without relying on color.
Filenames are bold and directories muted. Use `--hints` or `--long` for Git's
detailed sections and instructional hints. With `--short`, the left status column describes
staged changes; the right describes unstaged changes. Each column gets its own
change-type color. If both have changes, the filename uses the unstaged change's
color. Conflicts are red, copies green,
type changes blue, and untracked/ignored entries neutral.

Merge conflicts retain their precise descriptions in **Conflicts** (`--long`
uses Git's **Unmerged paths** section and resolution hints). Every conflicted entry is red, including “both
added” and delete/modify conflicts. After resolution and `git add` (or `git rm`),
Git moves the entry out of that section and its normal change-type color applies.

Arguments other than `--hints` go to `git status`. Redirects,
`--porcelain` and `-z` bypass Hunk coloring. Ordinary `git status`
continues to use Git's own configuration.

#### Replace `git status` (optional)

Git's built-in `status` command cannot be overridden with a Git alias. Hunk can
set up an interactive Bash or Zsh shell function to route `git status` through
Hunk. Run:

```sh
git hunk setup-status
```

The command prints the function and asks before appending it to `~/.bashrc` or
`$ZDOTDIR/.zshrc` (or `~/.zshrc` if `ZDOTDIR` is unset). It changes only
`git status`; other Git commands pass through unchanged. Remove the marked
function from that startup file, or run `unset -f git` in the current shell, to
restore normal behavior. Without opting in, `git status` is unaffected.

### Make Hunk your default pager (optional)

To use the same presentation for `git diff` and `git show`:

```sh
git config --global pager.diff hunk-pager
git config --global pager.show hunk-pager
git config --global diff.context 2
```

These global settings apply across repositories. Omit `--global` to configure
only the current repository. The `diff.context` setting also gives regular Git
diffs two context lines.

### Preview and customize

To preview a patch explicitly: `git diff --color=never | hunk-pager`.
To bypass presentation: `git --no-pager diff`.

The preset lives in `share/hunk/delta.gitconfig`. Explicit pager arguments such
as `hunk-pager --light` override it. The pager falls back to less if Delta is
missing. Context selection belongs to Git, not the formatter.

## Themes

The default theme uses your terminal's ANSI change colors and a readable gray
for context. The `railscasts` theme
uses the palette from [railscasts.nvim](https://github.com/lukelex/railscasts.nvim):
warm file headers, cyan locations, gray context, green additions, and warm
orange removal lines. The actual removed words use bold red over its darker
red-tinted background; added words get a green-tinted highlight. The layout
stays the same. RGB colors render exactly on true-color terminals; Delta
approximates them on 256-color terminals.

```sh
git config --global hunk.theme railscasts
git config --global hunk.theme light   # for light terminal backgrounds
HUNK_THEME=default git hunk             # temporary override
```

`HUNK_THEME` overrides `hunk.theme`; without either, Hunk uses `default`.
All three palettes ship with Hunk, so no Neovim theme installation is required.
The light palette uses dark red/green text, pale word-level highlights, and
medium-gray context. File totals count visible added/removed lines in the default
unified layout; binary and metadata-only changes retain their descriptive labels.

## Uninstall

If you enabled the optional global settings, remove them individually:

```sh
git config --global --unset pager.diff
git config --global --unset pager.show
git config --global --unset diff.context
```

If you configured a theme, remove it with `git config --global --unset hunk.theme`.
For repository-local settings, run the corresponding commands without `--global`.
If these settings replaced earlier preferences, restore those values instead.

Then, from this checkout, remove the installed files:

```sh
make uninstall
# For a system-wide installation: sudo make uninstall PREFIX=/usr/local
```

Use the same `PREFIX` you used when installing.

## Development

Run `make test` with Python 3 and Delta installed. Run
`shellcheck bin/git-hunk bin/hunk-pager` for the Bash wrappers.
After editing, run `make install` again to refresh a copied installation.
