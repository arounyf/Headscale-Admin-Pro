# Pre-0.27 upstream dumps

Real SQLite databases taken from official headscale releases up to and
including 0.26.x, plus one pre-0.27 dump carrying a failing node/pre-auth-key
constraint. They are parked here rather than deleted because they are the
evidence for a known gap, and because they are the fixtures to move back the
day that gap is closed.

## Why they are not in the parent directory

`TestSQLiteAllTestdataMigrations` walks `testdata/sqlite` and asserts that
every file in it migrates successfully. These do not, so they live in a
subdirectory, which the test skips (`schema.IsDir()`). Moving them back is all
that is needed to re-enable coverage once the code below is fixed.

## Where they fail

Every one of them stops in `202507021200` (the v0.27.0 schema recreation):

- Its `users` copy selects 17 columns from `users_old`, but these databases
  were created before the fork added its seven custom `users` columns, so the
  copy dies with `copying data: no such column: password`.
- Behind that, its `acl` and `log` copies select from `acl_old` and `log_old`.
  These databases have no `acl` or `log` table, so neither is renamed and the
  copies would fail with `no such table: acl_old`.

## What fixing them would take

`202507021200` has already shipped, and this repository's rule is that
migrations are append-only — a new migration runs *after* it, so it cannot
rescue a database that crashes inside it. Supporting these files means editing
the body of `202507021200` so its data copy only reads source columns and
tables that actually exist:

1. record which tables were really renamed in the rename loop and skip the
   copy whose `_old` source was never created;
2. build the `users` column list from the intersection of the target columns
   and `PRAGMA table_info(users_old)`.

Note that `checkVersionUpgradePath` (see `hscontrol/db/versioncheck.go`) also
refuses to move more than one minor version at a time, so a database that
records a version at all cannot go 0.26.x → 0.29.x in a single start. These
dumps predate that table, so they slip past the check and reach the migration —
which is why they fail here rather than being rejected earlier.
