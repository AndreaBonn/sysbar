# APT repository

Sysbar updates are delivered through a signed APT repository, so `apt upgrade`
keeps it current.

## Publishing (maintainer)

The repository is managed with `reprepro`. Layout:

```
apt-repo/
├── conf/
│   └── distributions
└── (generated) dists/  pool/
```

`conf/distributions`:

```
Origin: Sysbar
Label: Sysbar
Codename: noble
Architectures: amd64 all
Components: main
Description: Sysbar APT repository
SignWith: <GPG_KEY_ID>
```

Build and publish a new release:

```bash
./build.sh deb                                   # produces ../sysbar_<ver>_all.deb
reprepro -b apt-repo includedeb noble ../sysbar_*.deb
```

The repository (the `dists/` and `pool/` trees plus the exported public key)
is then served over HTTPS.

## Installing (user)

```bash
curl -fsSL https://<host>/sysbar.gpg | sudo tee /usr/share/keyrings/sysbar.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/sysbar.gpg] https://<host> noble main" \
  | sudo tee /etc/apt/sources.list.d/sysbar.list
sudo apt update
sudo apt install sysbar
```

Updates afterwards: `sudo apt update && sudo apt upgrade`.
