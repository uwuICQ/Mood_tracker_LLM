#Requires -Version 5.1
<#
  Публикует текущий проект в GitHub с учётом ruleset:
  - ветка development защищена: нужен PR из другой ветки;
  - force-push обычно запрещён — скрипт его не использует.

  Запуск (из корня репозитория):
    powershell -ExecutionPolicy Bypass -File .\push_via_pr.ps1
#>
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .git)) {
    throw "Запустите скрипт из корня git-репозитория (рядом с папкой .git)."
}

function Invoke-Git {
    param([Parameter(Mandatory)][string[]]$Args)
    & git @Args
    if ($LASTEXITCODE -ne 0) {
        throw "Команда завершилась с ошибкой: git $($Args -join ' ')"
    }
}

Write-Host "==> Убираем venv и __pycache__ из индекса (если попали случайно)..."
$null = git rm -r --cached venv 2>$null
$null = git rm -r --cached backend/__pycache__ 2>$null
Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch '[\\/]venv[\\/]' } |
    ForEach-Object {
        $rel = $_.FullName.Substring((Get-Location).Path.Length).TrimStart("\", "/") -replace "\\", "/"
        $null = git rm -r --cached --ignore-unmatch $rel 2>$null
    }

Write-Host "==> Стадия и коммит на main (если есть изменения)..."
Invoke-Git @("checkout", "main")
Invoke-Git @("add", "-A")
$status = git status --porcelain
if ($status) {
    git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        Invoke-Git @("commit", "-m", "Emotion analyzer: backend, gitignore; exclude venv and __pycache__")
    }
}

Write-Host "==> fetch origin..."
Invoke-Git @("fetch", "origin")

$featureBranch = "feature/emotion-analyzer-backend"
Write-Host "==> Ветка $featureBranch от origin/development и merge main..."
$ref = git show-ref --verify --quiet "refs/heads/$featureBranch"; if ($LASTEXITCODE -eq 0) {
    Invoke-Git @("branch", "-D", $featureBranch)
}
Invoke-Git @("checkout", "-B", $featureBranch, "origin/development")
Invoke-Git @("merge", "main", "-m", "Merge main (emotion analyzer) for PR into development")

Write-Host "==> push в origin..."
Invoke-Git @("push", "-u", "origin", $featureBranch)

$repo = "https://github.com/uwuICQ/Mood_tracker_LLM"
$compare = "$repo/compare/development...$featureBranch" + "?expand=1"

Write-Host ""
Write-Host "Готово: ветка запушена: $featureBranch"
Write-Host "На ruleset включено «Require a pull request before merging» — смержить можно только через PR."
Write-Host "Если включено «Require deployments to succeed», merge PR возможен только после успешного деплоя по правилам репозитория."
Write-Host ""

if (Get-Command gh -ErrorAction SilentlyContinue) {
    Write-Host "==> Создаю PR через GitHub CLI..."
    gh pr create --repo uwuICQ/Mood_tracker_LLM --base development --head $featureBranch `
        --title "Emotion analyzer backend" `
        --body "Автоматический PR из ``$featureBranch``. Включает backend и ``.gitignore`` (venv, ``__pycache__`` не в репозитории)."
} else {
    Write-Host "GitHub CLI (gh) не найден. Откройте ссылку и нажмите «Create pull request»:"
    Write-Host $compare
    Start-Process $compare
}
