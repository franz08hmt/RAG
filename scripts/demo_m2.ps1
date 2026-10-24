param([string]$Question,
      [ValidateSet('bm25','dense','hybrid','dense-rerank','hybrid-rerank')][string]$Method='hybrid-rerank',
      [switch]$NoAnswer)
$ErrorActionPreference='Stop'
$project=Split-Path -Parent $PSScriptRoot
$interpreter='C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe'
if (-not (Test-Path -LiteralPath $interpreter)) { throw 'Python env rag-hcmute is missing.' }
$arguments=@('-m','rag_hcmute.console_app','--method',$Method)
if ($Method -ne 'bm25') {
    $arguments+=@('--dense-model','D:\RAG\models\huggingface\hub\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181')
}
if ($Method.EndsWith('-rerank')) {
    $arguments+=@('--reranker-model','D:\RAG\models\huggingface\hub\models--BAAI--bge-reranker-v2-m3\snapshots\953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e','--reranker-max-length','1024')
}
if (-not $NoAnswer) {
    try { $null=Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 5 }
    catch { throw 'Ollama is not running. Open Ollama locally, then run this script again.' }
    $arguments+='--answer'
}
if ($Question) { $arguments+=@('--query',$Question) }
Push-Location $project
try { & $interpreter @arguments; $result=$LASTEXITCODE }
finally { Pop-Location }
exit $result
