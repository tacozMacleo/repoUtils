repoUtils
====================================================================
A repo with scripts for handling repos.


repo_converter
--------------------------------------------------------------------
Convert a mercurial repo into a git repo.
All commit descriptions, author & date are retained.

Have an option to add a filter on what to convert.
It could be a single file, or only what inside a folder. 

Example:
`repo_converter -r Project/superBigProgram -o Project/superPart -f coolPart/`

The above example takes a existent repo `superBigProgram` in the Project folder, and commit all the files that er under the `coolPart` folder,into the new repo `superPart`.

Added option to shorten the folder path from the output repo, by the filter.

### TODO:
 * [ ] It do not handle file diffs from the first mercurial commit.
