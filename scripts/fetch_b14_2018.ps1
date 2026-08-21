<#
.SYNOPSIS
  Fetch the eight 2018 Tick Pilot Appendix B.I files for B14 leg A.

.DESCRIPTION
  Registered in the design file, section 7 supplement 2 clause A and its expansion A1.

  This exists because experiments/b14_fetch_2018.py cannot reach the host from every
  environment: a proxied egress answers 403 on all URL forms. Windows reaches it
  directly, which is how the ten 2016 files were taken. So the split is:

      this script  -> move the bytes (it is the only side with network reach)
      the Python   -> verify and build (no network needed)

  Discipline (project rules, engineering part, items 5 and 6):
    - Nothing is deleted. This script contains no Remove-Item, no del, no rmdir.
      A file whose size disagrees with the index is renamed with an .expired suffix.
    - Resumable. Bytes land in a .part file and an HTTP Range request continues it.
      A rename happens only after the size matches.
    - Truncation is caught downstream: run the Python --verify afterwards, which
      decompresses every gzip end to end.

.EXAMPLE
  .\scripts\fetch_b14_2018.ps1
  .\scripts\fetch_b14_2018.ps1 -WithOctober
  .\scripts\fetch_b14_2018.ps1 -Direct        # skip the index, download by name
#>
[CmdletBinding()]
param(
    [string]$Base = "http://ftp.nyxdata.com/Tick_Pilot/",
    [switch]$WithOctober,
    [switch]$Direct,
    [switch]$ListOnly
)

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# The design file, section 1, already records the fact this works around: the
# certificate this host serves is not valid for this hostname. Asking for http://
# does not avoid it, because the host redirects to https and the redirect is where
# verification fails. So certificate errors are tolerated FOR THIS HOST ONLY.
# A valid certificate is still accepted on the normal path, and any other host with
# a broken certificate is still refused, which is what keeps this from being a
# blanket "trust everything".
$script:InsecureHosts = @("ftp.nyxdata.com")
[Net.ServicePointManager]::ServerCertificateValidationCallback = {
    param($snd, $cert, $chain, $errs)
    if ($errs -eq [Net.Security.SslPolicyErrors]::None) { return $true }
    $h = ""
    try { $h = $snd.RequestUri.Host } catch { }
    if (-not $h) { try { $h = [string]$snd } catch { } }
    return ($script:InsecureHosts -contains $h)
}

$Root = Split-Path -Parent $PSScriptRoot
$Raw  = Join-Path $Root "data\raw"
if (-not (Test-Path $Raw)) { New-Item -ItemType Directory -Path $Raw | Out-Null }

$Venues = @("NYSE", "NYSEARCA")
$Months = @("201808", "201809", "201811", "201812")
if ($WithOctober) { $Months += "201810" }
$Wanted = foreach ($v in $Venues) { foreach ($m in ($Months | Sort-Object)) {
    "{0}_MKTQUALITYSTATS_{1}.gzip" -f $v, $m } }

$Specs = @(
    @{ Url  = "http://www.finra.org/sites/default/files/Appendix-B-and-C-Reporting-Requirements.pdf"
       Name = "FINRA_Appendix-B-and-C-Reporting-Requirements.pdf" }
)

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$UA = "Mozilla/5.0 (compatible; b14-fetch/1.0)"

function Park([string]$Path, [string]$Why) {
    # Never delete. Rename out of the way and return the new name.
    $new = "$Path.expired_${Stamp}_$Why"
    Move-Item -LiteralPath $Path -Destination $new
    return $new
}

function Get-Index([string]$BaseUrl, [ref]$RawOut) {
    $html = (Invoke-WebRequest -Uri $BaseUrl -UseBasicParsing -UserAgent $UA `
             -TimeoutSec 120).Content
    if ($RawOut -ne $null) { $RawOut.Value = $html }
    $map = @{}
    foreach ($row in ($html -split '(?i)<tr|\r?\n')) {
        foreach ($m in [regex]::Matches($row, 'href="([^"]+)"')) {
            $href = $m.Groups[1].Value
            if ($href -notmatch '\.(gzip|gz|txt|csv|pdf|xlsx)$') { continue }
            $name = ($href -replace '/$','') -split '/' | Select-Object -Last 1
            $tail = $row.Substring($row.IndexOf($href) + $href.Length)
            $tail = [regex]::Replace($tail, '<[^>]+>', ' ')
            $nums = [regex]::Matches($tail, '(?<![\d.,])(\d{4,})(?![\d.,])')
            $size = $null
            if ($nums.Count -gt 0) { $size = [int64]$nums[$nums.Count-1].Groups[1].Value }
            # Join on the basename, the same rule the Python half uses, so an
            # absolute href does not get pasted onto the base.
            $map[$name] = @{ Url = $BaseUrl + $name; Size = $size }
        }
    }
    return $map
}

function Get-File([string]$Url, [string]$Dst, $Expect) {
    # Stream to .part with Range resume, then rename. Never opens a write handle
    # on the destination itself.
    $part = "$Dst.part"
    $have = 0L
    if (Test-Path $part) { $have = (Get-Item $part).Length }
    if ($Expect -ne $null -and $have -gt $Expect) {
        Park $part "part_larger_than_index" | Out-Null
        $have = 0L
    }
    $req = [Net.HttpWebRequest]::Create($Url)
    $req.UserAgent = $UA
    $req.Timeout = 120000
    $req.ReadWriteTimeout = 600000
    if ($have -gt 0) { $req.AddRange($have) }
    $resp = $null
    try { $resp = $req.GetResponse() }
    catch [Net.WebException] {
        if ($have -gt 0 -and $_.Exception.Response -and
            [int]$_.Exception.Response.StatusCode -eq 416) {
            # already complete on the server's view
            $resp = $null
        } else { throw }
    }
    if ($resp -eq $null) { return @{ Ok = $false; Msg = "server refused the range request" } }
    $resumed = ([int]$resp.StatusCode -eq 206)
    if ($have -gt 0 -and -not $resumed) {
        Park $part "server_ignored_range" | Out-Null
        $have = 0L
    }
    $mode = if ($resumed) { [IO.FileMode]::Append } else { [IO.FileMode]::Create }
    $in = $resp.GetResponseStream()
    $out = New-Object IO.FileStream($part, $mode, [IO.FileAccess]::Write)
    try {
        $buf = New-Object byte[] (1MB)
        $n = 0
        while (($n = $in.Read($buf, 0, $buf.Length)) -gt 0) { $out.Write($buf, 0, $n) }
    } finally { $out.Close(); $in.Close(); $resp.Close() }
    $got = (Get-Item $part).Length
    if ($Expect -ne $null -and $got -ne $Expect) {
        return @{ Ok = $false
                  Msg = "got $got bytes, index says $Expect; left as .part, not renamed" }
    }
    Move-Item -LiteralPath $part -Destination $Dst
    $note = if ($have -gt 0) { "$got bytes, resumed" } else { "$got bytes" }
    return @{ Ok = $true; Msg = $note }
}

# ------------------------------------------------------------------ index

$byName = @{}
if ($Direct) {
    Write-Host "-Direct: skipping the index, forming names from the 2016 convention"
    foreach ($n in $Wanted) { $byName[$n] = @{ Url = $Base + $n; Size = $null } }
} else {
    Write-Host "index: $Base"
    try {
        $raw = ""
        $byName = Get-Index $Base ([ref]$raw)
        $mq = ($byName.Keys | Where-Object { $_ -like "*MKTQUALITYSTATS*" }).Count
        Write-Host ("  ok, {0} entries, {1} of them MKTQUALITYSTATS" -f $byName.Count, $mq)
        $dump = Join-Path $Raw "_tickpilot_index_$Stamp.html"
        Set-Content -LiteralPath $dump -Value $raw -Encoding UTF8
        Write-Host "  raw index kept at data\raw\_tickpilot_index_$Stamp.html"
    } catch {
        Write-Host "  index unreachable: $($_.Exception.Message)"
        Write-Host ""
        Write-Host "  The eight filenames follow the 2016 convention already on disk, so"
        Write-Host "  if the files open in a browser, re-run with -Direct:"
        Write-Host "      .\scripts\fetch_b14_2018.ps1 -Direct"
        exit 1
    }
}

# ------------------------------------------------------------------ fetch

Write-Host ""
Write-Host ("wanted, {0} files:" -f $Wanted.Count)
foreach ($name in $Wanted) {
    $dst = Join-Path $Raw $name
    $entry = $byName[$name]
    $note = ""
    if ($entry -eq $null) {
        $note = "not in the index under this name"
    } else {
        $expect = $entry.Size
        $have = $null
        if (Test-Path $dst) { $have = (Get-Item $dst).Length }
        if ($have -ne $null -and $expect -ne $null -and $have -ne $expect) {
            $new = Park $dst "size_disagrees_with_index"
            $note = "on disk $have vs index $expect, renamed, will re-fetch"
            $have = $null
        } elseif ($have -ne $null) {
            $note = "already on disk"
        }
        if (-not $ListOnly -and $have -eq $null) {
            try {
                $r = Get-File $entry.Url $dst $expect
                $note = $(if ($r.Ok) { "fetched: " } else { "**incomplete**: " }) + $r.Msg
            } catch {
                $note = "**failed**: $($_.Exception.Message) (.part kept; re-run to resume)"
            }
        }
    }
    $sz = if ($entry -ne $null -and $entry.Size -ne $null) { $entry.Size } else { "?" }
    Write-Host ("  {0,-42} {1,12}  {2}" -f $name, $sz, $note)
}

if (-not $ListOnly) {
    Write-Host ""
    Write-Host "specification of record (design file section 3 supplement 3):"
    foreach ($s in $Specs) {
        $dst = Join-Path $Raw $s.Name
        if (Test-Path $dst) {
            Write-Host ("  {0,-52} already on disk" -f $s.Name)
        } else {
            try {
                $r = Get-File $s.Url $dst $null
                Write-Host ("  {0,-52} {1}" -f $s.Name, $r.Msg)
            } catch {
                Write-Host ("  {0,-52} **failed**: {1}" -f $s.Name, $_.Exception.Message)
            }
        }
    }
}

$missing = @($Wanted | Where-Object { -not (Test-Path (Join-Path $Raw $_)) })
Write-Host ""
if ($missing.Count -eq 0) {
    Write-Host "complete. next, in order:"
    Write-Host "  python experiments\b14_fetch_2018.py --verify        # gzip end to end"
    Write-Host "  python experiments\b14_tickpilot_panel.py --build"
    Write-Host "  python experiments\b14_gate_exit.py --census         # step-zero census"
} else {
    Write-Host ("{0} still missing: {1}" -f $missing.Count, ($missing -join ", "))
}
