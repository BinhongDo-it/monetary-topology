@echo off
REM Nightly jobs. One line per job. Paths are absolute on purpose: schtasks
REM sets no working directory, and every script here derives its own paths
REM from __file__, so no `cd` is needed and no `&&` has to survive schtasks.
REM The absolute path is taken from this file's own location rather than
REM written out, so the checked-in copy carries no machine's drive letter.
REM
REM Add a job by adding a line. Nothing here needs the venv: the harvester is
REM standard library only (urllib, gzip, hashlib, json, re).

set PY=python
set EXP=%~dp0..\experiments

REM --venues aquis, ruled 2026-08-23. Two runs on 2026-08-22 settled what the
REM free 15-minute-delayed MiFIR tier contains:
REM   cboe      71 links, all rts13_public_trade_data. Trades, no bid/ask.
REM             2.4 GB per run, and its index carries past dates, so nothing
REM             here is lost by not taking it now.
REM   euronext  post-trade delayed, data links JS-rendered, zero fetchable files.
REM   aquis     real pre-trade quotes, and the only irreplaceable one: two files
REM             overwritten in place, so an uncaptured day is gone for good.
REM Widening again is this one flag, not a rewrite. No URL was removed.

%PY% "%EXP%\eu_mifid_harvest.py" --once --venues aquis

REM --- add further nightly jobs below this line ---
