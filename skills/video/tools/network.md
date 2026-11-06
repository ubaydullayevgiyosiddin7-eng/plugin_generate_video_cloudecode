# Korporativ tarmoq: qaysi xatoga nima yordam beradi

| Xato | Yechim |
|---|---|
| `git clone/push`: schannel, `CRYPT_E_NO_REVOCATION_CHECK` | `git -c http.schannelCheckRevoke=false ...` |
| `curl`: `CRYPT_E_NO_REVOCATION_CHECK` | `curl --ssl-no-revoke`, yoki `CURL_HOME` papkasida `_curlrc` fayli: `ssl-no-revoke` |
| `pip`: `CERTIFICATE_VERIFY_FAILED` | `pip install --use-feature=truststore` (pip 24.2+ da bu standart) |
| Python urllib (`scripts\railway.py`) | `from pip._vendor import truststore; truststore.inject_into_ssl()` va keyin skript |
| Node / `railway` CLI | `$env:NODE_OPTIONS="--use-system-ca"`; `railway` topilmasa: `$env:Path="$env:APPDATA\npm;$env:Path"` |
| `winget`: msstore sertifikati | `winget install ... --source winget` |
