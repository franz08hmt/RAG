param([Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
$project=Split-Path -Parent $PSScriptRoot
$output=[IO.Path]::GetFullPath($OutputDirectory)
if ($output.StartsWith($project,[StringComparison]::OrdinalIgnoreCase)) { throw 'Logs must stay outside the repository.' }
if (Test-Path -LiteralPath $output) { throw 'Choose a new output directory.' }
New-Item -ItemType Directory -Path $output | Out-Null
$questions=@(
 @{ id='01'; text='Thủ tục xin nghỉ học tạm thời được quy định ra sao?' },
 @{ id='02'; text='So sánh thời gian thiết kế và số tín chỉ tối thiểu của cử nhân chính quy và vừa làm vừa học theo bảng 1.' },
 @{ id='03'; text='Điều kiện để đăng ký học chương trình thứ hai là gì?' },
 @{ id='04'; text='Thư viện công cộng ở Cần Thơ mở cửa sáng Chủ nhật lúc mấy giờ?' },
 @{ id='05'; text='Đã học môn A nhưng chưa đạt, điều kiện đăng ký môn B khi A là học trước hoặc tiên quyết là gì?' }
)
$python='C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe'
$model='D:\RAG\models\huggingface\hub\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181'
Push-Location $project
try {
  foreach($q in $questions){
    $log=Join-Path $output ('demo_'+$q.id+'.txt')
    $metrics=Join-Path $output ('demo_'+$q.id+'.json')
    Write-Output "Python executable: $python"
    & $python -m rag_hcmute.console_app --method hybrid --dense-model $model --answer --prompt-variant scope_schema --context-window 8192 --query $q.text --timing-json $metrics 2>&1 | Out-File -FilePath $log -Encoding utf8
    if($LASTEXITCODE -ne 0){Write-Output "demo $($q.id) reported exit code $LASTEXITCODE; inspect status in local JSON and log"}
    else {Write-Output "demo $($q.id) completed"}
  }
} finally {Pop-Location}
