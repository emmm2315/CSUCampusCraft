param(
  [Parameter(Mandatory=$true)][string]$InputPath,
  [Parameter(Mandatory=$true)][string]$OutputPdf
)
$ErrorActionPreference = 'Stop'
$InputPath = $InputPath.Replace('/', '\')
$OutputPdf = $OutputPdf.Replace('/', '\')
if (-not (Test-Path -LiteralPath $InputPath -PathType Leaf)) { throw "Input does not exist: $InputPath" }
$wordApp = $null
$wordDoc = $null
$result = [ordered]@{ renderer = 'Microsoft Word COM ExportAsFixedFormat'; input = $InputPath; output = $OutputPdf; readOnly = $true; savedInput = $false }
try {
  $wordApp = New-Object -ComObject Word.Application
  $wordApp.Visible = $false
  $wordApp.DisplayAlerts = 0
  $result.wordVersion = $wordApp.Version
  $wordDoc = $wordApp.Documents.Open($InputPath, $false, $true, $false)
  $wordDoc.Repaginate()
  $result.pageCount = $wordDoc.ComputeStatistics(2)
  $wordDoc.ExportAsFixedFormat($OutputPdf, 17)
  $result.pdfBytes = (Get-Item -LiteralPath $OutputPdf).Length
  $result.result = 'PASS'
} finally {
  if ($wordDoc) { $wordDoc.Close(0); [Runtime.InteropServices.Marshal]::FinalReleaseComObject($wordDoc) | Out-Null }
  if ($wordApp) { $wordApp.Quit(0); [Runtime.InteropServices.Marshal]::FinalReleaseComObject($wordApp) | Out-Null }
  [GC]::Collect()
  [GC]::WaitForPendingFinalizers()
}
$result | ConvertTo-Json -Depth 5
