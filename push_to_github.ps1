# Kullanıcıdan commit mesajı al
$commitMessage = Read-Host "Commit mesajı girin"

# Git yüklü mü kontrol et
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Git yüklü değil. https://git-scm.com adresinden yükleyin." -ForegroundColor Red
    exit
}

# .git klasörü var mı?
if (-not (Test-Path ".git")) {
    Write-Host "Git deposu başlatılıyor..."
    git init
}

# Remote ayarlanmış mı?
$remoteSet = git remote get-url origin 2>$null
if (-not $remoteSet) {
    $repoUrl = Read-Host "GitHub repo HTTPS URL'sini girin (örnek: https://github.com/kullanici/proje.git)"
    git remote add origin $repoUrl
}

# Tüm dosyaları stage et
git add .

# Commit yap
if (-not $commitMessage) {
    $commitMessage = "Zorunlu otomatik commit"
}
git commit -m "$commitMessage"

# Ana branch'e geç
git branch -M main

# Zorla pushla
git push origin main --force

Write-Host "`n✅ Proje ZORLA GitHub'a yüklendi." -ForegroundColor Green
