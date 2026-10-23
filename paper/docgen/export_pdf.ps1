$ErrorActionPreference = "Stop"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
  $doc = $word.Documents.Open("D:\ZCode-work\.zcode\workspace\default\docgen\playbook.docx", $false, $true)
  $doc.ExportAsFixedFormat("D:\ZCode-work\.zcode\workspace\default\docgen\playbook.pdf", 17)
  $doc.Close(0)
} finally {
  $word.Quit()
}
Write-Output "PDF_DONE"
