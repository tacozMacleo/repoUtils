repoUtils
====================================================================
A repo with scripts for handling repos.


repo converter
--------------------------------------------------------------------
Convert a mercurial repo into a git repo.
All commit descriptions, author & date are retained.

Have an option to add a filter on what to convert.
It could be a single file, or only what is inside a folder. 

Example:
`repo_converter -r Project/superBigProgram -o Project/superPart -f coolPart/`

The above example takes a existent repo `superBigProgram` in the Project folder, and commit all the files that er under the `coolPart` folder, into the new repo `superPart`.

Added option to shorten the folder path from the output repo, by the filter.

### Known Bugs
 * If option 'branch' is set, it tries to apply changes from all branch to file.
 ---

### TODO:
 * [x] Add Option to set program on hold, on errors, so user can fix it.
 * [x] It do not handle file diffs from the first mercurial commit.
 * [ ] Handle sub-repos.
 * [ ] Add option to convert & import all branches as once.
 * [ ] Option to show/check result with a diff.
 * [ ] Done check: `diff -qr {repo} {out}`
 * [ ] Add handle of multiline Description.
