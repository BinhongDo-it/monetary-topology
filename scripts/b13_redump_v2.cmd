@echo off
REM ---------------------------------------------------------------------------
REM  B13 two-class dump, v3: the same states as the v1 cache plus the two class
REM  spreads s_e and s_d as columns 5 and 6, and the two bids as 7 and 8.
REM  The bids are what carry the LEVEL, and Theorem 6(5) is a statement about
REM  s/2M, so without them the spread part of S - S' cannot be formed at all.
REM
REM  The multicast group sets below are not guesses. Each was checked against the
REM  v1 cache by re-running the dump with --limit 500000 and comparing the first
REM  four columns row by row: ch386 65 rows identical, ch382 2388 rows identical.
REM  Any other group set shifts the seq counter and stops matching.
REM
REM  Writes to *_v3.tsv. The v1 files are not touched and are not read by this.
REM
REM  venv first, or python resolves to miniconda and pytest to global 3.13:
REM      .\.venv\Scripts\Activate.ps1
REM ---------------------------------------------------------------------------
setlocal
set PY=python
set DEFS=data\raw\b13\dc3-glbx-a-20230716T110000.pcap.zst
set DATA=data\raw\b13\dc3-glbx-ab-dedup-20230717T133000.pcap.zst

echo === ch386  NYMEX nat gas and other non-crude energy ===
%PY% experiments\b4_two_classes.py --dump ^
  --defs %DEFS% --data %DATA% ^
  --groups 224.0.31.134:14386,224.0.32.134:15386 ^
  --spreads NGU3-NGZ3,NGQ3-NGF4,NGQ3-NGZ3,NGQ3-NGH4,NGU3-NGK4,NGV3-NGK4,NGU3-NGJ4,NGQ3-NGK4,NGH4-NGQ4,NGQ3-NGJ4,NGX3-NGF4,NGU3-NGF4,NGV3-NGF4,TTFQ3-TTFU3,NGZ3-NGK4 ^
  --out data\cache\b13\two_classes_ch386_v3.tsv
if errorlevel 1 goto :fail

echo === ch382  NYMEX crude and refined ===
%PY% experiments\b4_two_classes.py --dump ^
  --defs %DEFS% --data %DATA% ^
  --groups 224.0.31.130:14382,224.0.32.130:15382 ^
  --spreads CLZ3-CLZ4,CLQ3-CLX3,CLU3-CLX3,CLQ3-CLV3,CLV3-CLM4,CLU3-CLV3,RBU3-RBV3,RBU3-RBX3 ^
  --out data\cache\b13\two_classes_ch382_v3.tsv
if errorlevel 1 goto :fail

echo.
echo === discipline 19: v1 must be a prefix of v2's first four columns ===
%PY% scripts\b13_check_v2.py
if errorlevel 1 goto :fail

echo.
echo === stage two, the test the two extra columns exist for ===
%PY% experiments\b13_level.py
goto :eof

:fail
echo.
echo FAILED, stopping here.
exit /b 1
