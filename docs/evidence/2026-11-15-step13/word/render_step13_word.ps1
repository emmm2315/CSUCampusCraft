param(
    [Parameter(Mandatory=$true)][string]$InputDocx,
    [Parameter(Mandatory=$true)][string]$OutputPdf
)
$ErrorActionPreference='Stop'
$inputAbsolute=(Resolve-Path -LiteralPath $InputDocx).Path
$outputAbsolute=[System.IO.Path]::GetFullPath($OutputPdf)
$inputHash=(Get-FileHash -LiteralPath $inputAbsolute -Algorithm SHA256).Hash.ToLowerInvariant()
$application=$null
$document=$null
$record=[ordered]@{renderer='Microsoft Word COM ExportAsFixedFormat';inputSha256=$inputHash;readOnly=$true;inputSaved=$false}
try {
    $application=New-Object -ComObject Word.Application
    $application.Visible=$false
    $application.DisplayAlerts=0
    $record.wordVersion=$application.Version
    $document=$application.Documents.Open($inputAbsolute,$false,$true,$false)
    $document.Repaginate()
    $record.pageCount=$document.ComputeStatistics(2)
    $document.ExportAsFixedFormat($outputAbsolute,17)
    $record.pdfBytes=(Get-Item -LiteralPath $outputAbsolute).Length
    $record.overall='PASS'
} finally {
    if($document){$document.Close(0);[Runtime.InteropServices.Marshal]::FinalReleaseComObject($document)|Out-Null}
    if($application){$application.Quit(0);[Runtime.InteropServices.Marshal]::FinalReleaseComObject($application)|Out-Null}
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
$record.inputStillUnchanged=((Get-FileHash -LiteralPath $inputAbsolute -Algorithm SHA256).Hash.ToLowerInvariant() -eq $inputHash)
if(-not $record.inputStillUnchanged){throw 'Read-only renderer input hash changed'}
$record | ConvertTo-Json -Depth 4
