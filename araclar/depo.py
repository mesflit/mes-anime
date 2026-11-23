"""Git işlemleri: video deposunu videolar olmadan klonlama, gönderme, yeni depo açma."""
import shutil
from pathlib import Path

from .ayar import DEPOLAR_TXT, KOK, KULLANICI, calistir, cikti, depo_yolu, hata


def _git(depo: Path, *arg, sessiz=True):
    return calistir(["git", "-C", depo, *arg], sessiz=sessiz)


def var_mi(depo: str) -> bool:
    """GitHub'da depo var mı? (Yoksa git şifre sormasın diye GIT_TERMINAL_PROMPT=0)"""
    import os
    import subprocess
    r = subprocess.run(["git", "ls-remote", f"https://github.com/{KULLANICI}/{depo}.git"],
                       capture_output=True, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    return r.returncode == 0


def klonla(depo: str) -> Path:
    """Depoyu ../<depo> klasörüne videolar (.ts) OLMADAN klonlar. Varsa videoları diskten kaldırır."""
    hedef = depo_yolu(depo)
    if (hedef / ".git").exists():
        _git(hedef, "config", "remote.origin.promisor", "true")
        _git(hedef, "config", "remote.origin.partialclonefilter", "blob:none")
    else:
        calistir(["git", "clone", "--filter=blob:none", "--no-checkout",
                  f"https://github.com/{KULLANICI}/{depo}.git", hedef])
    _git(hedef, "config", "advice.updateSparsePath", "false")
    _git(hedef, "sparse-checkout", "set", "--no-cone", "/*", "!*.ts")
    if cikti(["git", "-C", hedef, "rev-parse", "--verify", "HEAD"]):
        _git(hedef, "checkout")
    else:
        _git(hedef, "symbolic-ref", "HEAD", "refs/heads/main")   # boş depo: ilk dal main olsun
    print(f"📦 {hedef} hazır (videolar indirilmedi)")
    return hedef


def hazirla(depo: str) -> Path:
    """../<depo> yoksa klonlar, varsa olduğu gibi döndürür."""
    hedef = depo_yolu(depo)
    return hedef if (hedef / ".git").exists() else klonla(depo)


def olustur(depo: str):
    """GitHub'da herkese açık boş depo açar (gh gerekir)."""
    if var_mi(depo):
        print(f"ℹ️  github.com/{KULLANICI}/{depo} zaten var.")
        return
    if not shutil.which("gh"):
        hata(f"gh yok. Depoyu elle aç (herkese açık): https://github.com/new  ad: {depo}")
    calistir(["gh", "repo", "create", f"{KULLANICI}/{depo}", "--public"])


def gonder(depo: Path, mesaj: str) -> bool:
    """Değişiklikleri commit + push eder, yüklenen videoları diskten siler."""
    _git(depo, "add", "--sparse", "-A")
    if not cikti(["git", "-C", depo, "status", "--porcelain"]):
        print("ℹ️  Gönderilecek değişiklik yok.")
        return False
    _git(depo, "commit", "-q", "-m", mesaj)
    print(f"⬆️  {depo.name}: gönderiliyor...")
    _git(depo, "push", "-q", "-u", "origin", "HEAD", sessiz=False)
    _git(depo, "sparse-checkout", "reapply")                     # .ts dosyalarını diskten sil
    print(f"✅ {depo.name}: gönderildi ({mesaj})")
    return True


def sitede_mi(depo: str) -> bool:
    """data/depolar.txt'de bu depo var mı?"""
    if not DEPOLAR_TXT.exists():
        return False
    return any(s.split("#")[0].strip().split("@")[0] == f"{KULLANICI}/{depo}"
               for s in DEPOLAR_TXT.read_text(encoding="utf-8").splitlines())


def siteye_ekle(depo: str, gonder_mi: bool = True):
    """data/depolar.txt'ye depoyu ekler ve mes-anime'yi gönderir."""
    if sitede_mi(depo):
        return
    mevcut = DEPOLAR_TXT.read_text(encoding="utf-8") if DEPOLAR_TXT.exists() else ""
    DEPOLAR_TXT.write_text(mevcut.rstrip("\n") + f"\n{KULLANICI}/{depo}\n", encoding="utf-8")
    print(f"➕ data/depolar.txt: {KULLANICI}/{depo}")
    if gonder_mi:
        _git(KOK, "add", DEPOLAR_TXT)
        _git(KOK, "commit", "-q", "-m", f"feat: {depo} siteye eklendi")
        _git(KOK, "push", "-q", "origin", "HEAD", sessiz=False)
        print("✅ mes-anime gönderildi")
