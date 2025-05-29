# Git komutlarını çalıştır
Write-Host "Git işlemleri başlatılıyor..."

# Git init (eğer .git klasörü yoksa)
if (-not (Test-Path .git)) {
    Write-Host "Git deposu oluşturuluyor..."
    git init
}

# Değişiklikleri ekle
Write-Host "Değişiklikler ekleniyor..."
git add .

# Commit
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "Commit yapılıyor..."
git commit -m "Otomatik güncelleme - $timestamp"

# Main branch'e geç
Write-Host "Main branch ayarlanıyor..."
git branch -M main

# Remote kontrolü ve ekleme
$remote = git remote -v
if (-not $remote) {
    Write-Host "Remote ayarlanıyor..."
    git remote add origin https://github.com/cermak2323/cermak.servis.git
}

# Force push
Write-Host "GitHub'a force push yapılıyor..."
git push --force origin main

Write-Host "İşlem tamamlandı!" 