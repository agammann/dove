param([Parameter(Mandatory = $true)][string]$Directory)
$ErrorActionPreference = 'Stop'
$line = (Get-Content -LiteralPath (Join-Path $Directory 'SHA256SUMS') -Raw).Trim()
if ($line -cnotmatch '^([a-f0-9]{64})  (dove_[0-9]+\.[0-9]+\.[0-9]+_source\.zip)$') {
  throw 'Unexpected checksum manifest.'
}
$expected = $Matches[1]
$archive = Join-Path $Directory $Matches[2]
if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -cne $expected) {
  throw 'Downloaded source archive hash mismatch.'
}
