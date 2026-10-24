param([Parameter(Mandatory=$true)][string]$InputDocx,
      [Parameter(Mandatory=$true)][string]$OutputPdf)
$ErrorActionPreference = 'Stop'
$source = (Resolve-Path -LiteralPath $InputDocx).Path
$destination = [System.IO.Path]::GetFullPath($OutputPdf)
if (Test-Path -LiteralPath $destination) { throw 'Refusing to overwrite an existing PDF.' }
New-Item -ItemType Directory -Force -Path ([System.IO.Path]::GetDirectoryName($destination)) | Out-Null
# Use a distinct read-only QA copy. Never close a document the user already opened.
$copy = Join-Path ([System.IO.Path]::GetDirectoryName($destination)) ('qa-' + [guid]::NewGuid().ToString() + '.docx')
Copy-Item -LiteralPath $source -Destination $copy
$word = $null
$document = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $document = $word.Documents.Open($copy, $false, $true, $false)
    $document.Repaginate()
    $document.ExportAsFixedFormat($destination, 17)
    Write-Output ('Exported PDF pages: ' + $document.ComputeStatistics(2))
} finally {
    if ($null -ne $document) { $document.Close(0); [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($document) }
    if ($null -ne $word) { $word.Quit(); [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) }
}
